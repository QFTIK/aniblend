"""
Operators for AniBlend Cel-Shader & Inverted Hull Outlines.
"""

import bpy
import bmesh
from mathutils import Matrix, Vector
from .shader_builder import (
    create_anime_material, find_anime_toon_node,
    setup_sphere_drivers, CTRL_PROP,
    get_or_create_outline_material, OUTLINE_MOD_NAME,
    set_outline_style, set_outline_chaos, set_outline_opacity, set_outline_scale,
    find_outline_emission_node,
    get_or_create_stray_outline_material,
    OUTLINE_STRAY_MOD_NAME, OUTLINE_STRAY_MAT_NAME,
    set_stray_density, set_stray_opacity, set_stray_jitter, set_stray_color,
    heal_anime_materials,
    sync_material_lights, _get_light_socket_name,
)

LIGHT_PALETTE = [
    (0.2, 1.0, 0.4, 1.0),   # 1: 🟢 Neon Green
    (1.0, 0.9, 0.1, 1.0),   # 2: 🟡 Yellow
    (0.15, 0.8, 1.0, 1.0),  # 3: 🔵 Cyan / Sky Blue
    (1.0, 0.25, 0.8, 1.0),  # 4: 🟣 Magenta
    (1.0, 0.5, 0.1, 1.0),   # 5: 🟠 Orange
    (0.7, 0.3, 1.0, 1.0),   # 6: 🪻 Purple
    (1.0, 0.2, 0.2, 1.0),   # 7: 🔴 Red
    (0.2, 1.0, 0.9, 1.0),   # 8: 🌊 Aquamarine
]


def _resolve_mesh(context):
    """Helper to get the bound mesh from any selected object (mesh, sphere controller, or pointer)."""
    obj = context.active_object
    if not obj:
        return None
    if "anime_bound_mesh" in obj:
        mesh = obj["anime_bound_mesh"]
        if mesh and mesh.name in bpy.data.objects:
            return mesh
    if obj.type in {'MESH', 'CURVE', 'FONT', 'SURFACE'}:
        return obj
    return None


def _on_light_prop_update(self, context):
    mesh = _resolve_mesh(context)
    if mesh:
        sync_material_lights(mesh)
        if context.area:
            context.area.tag_redraw()


def _on_light_color_update(self, context):
    # Keep marker color and light color 1:1 in sync
    self["marker_color"] = tuple(self.light_color)
    if self.ctrl_obj:
        _update_pointer_color(self.ctrl_obj, self.light_color)
    _on_light_prop_update(self, context)


def _on_marker_color_update(self, context):
    # Keep light color and marker color 1:1 in sync
    self["light_color"] = tuple(self.marker_color)
    if self.ctrl_obj:
        _update_pointer_color(self.ctrl_obj, self.marker_color)
    _on_light_prop_update(self, context)


class AnimeLightItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="Light")
    marker_color: bpy.props.FloatVectorProperty(
        name="Marker Color",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.2, 1.0, 0.4, 1.0),
        update=_on_marker_color_update,
    )
    light_color: bpy.props.FloatVectorProperty(
        name="Light Color",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.2, 1.0, 0.4, 1.0),
        update=_on_light_color_update,
    )
    strength: bpy.props.FloatProperty(
        name="Strength",
        default=1.0,
        min=0.0, max=5.0,
        update=_on_light_prop_update,
    )
    shadow_position: bpy.props.FloatProperty(
        name="Shadow Position",
        default=0.4,
        min=-1.0, max=1.0,
        update=_on_light_prop_update,
    )
    shadow_softness: bpy.props.FloatProperty(
        name="Shadow Softness",
        default=0.08,
        min=0.001, max=1.0,
        update=_on_light_prop_update,
    )
    specular_size: bpy.props.FloatProperty(
        name="Highlight Size",
        default=0.10,
        min=0.0, max=0.8,
        update=_on_light_prop_update,
    )
    enabled: bpy.props.BoolProperty(
        name="Enabled",
        default=True,
        update=_on_light_prop_update,
    )
    opacity: bpy.props.FloatProperty(
        name="Opacity",
        description="Layer opacity (0 = transparent, 1 = fully opaque)",
        default=1.0,
        min=0.0, max=1.0,
        subtype='FACTOR',
        update=_on_light_prop_update,
    )
    blend_mode: bpy.props.EnumProperty(
        name="Layer Mode",
        description="How this light interacts with layers beneath it",
        items=[
            ('COVER', "Cover", "Acts like an opaque paint layer covering underlying lighting"),
            ('ADD', "Add", "Adds brightness on top of underlying lighting"),
        ],
        default='COVER',
        update=_on_light_prop_update,
    )
    ctrl_obj: bpy.props.PointerProperty(
        name="Controller",
        type=bpy.types.Object,
    )


def _get_or_create_pointer_material(color=(0.2, 1.0, 0.4, 1.0), suffix=""):
    """Emission material for the light source point matching the marker color."""
    mat_name = f"M_AniBlend_LightGizmo_{suffix}" if suffix else "M_AniBlend_LightGizmo"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        emit = nodes.new('ShaderNodeEmission')
        emit.inputs['Color'].default_value = color
        emit.inputs['Strength'].default_value = 2.0
        mat.node_tree.links.new(emit.outputs['Emission'], out.inputs['Surface'])
    else:
        for node in mat.node_tree.nodes:
            if node.type == 'EMISSION' and 'Color' in node.inputs:
                node.inputs['Color'].default_value = color
    mat.diffuse_color = color
    mat.use_backface_culling = True
    return mat


def _update_pointer_color(ctrl, color):
    """Updates the display and emission color of the pointer object and controller attached to ctrl."""
    if not ctrl or ctrl.name not in bpy.data.objects:
        return
    ctrl.color = color
    pointer_name = f"{ctrl.name}_Pointer"
    pointer_obj = bpy.data.objects.get(pointer_name)
    if pointer_obj:
        pointer_obj.color = color
        if pointer_obj.data and pointer_obj.data.materials:
            mat = pointer_obj.data.materials[0]
            if mat:
                mat.diffuse_color = color
                if mat.node_tree:
                    for node in mat.node_tree.nodes:
                        if node.type == 'EMISSION' and 'Color' in node.inputs:
                            node.inputs['Color'].default_value = color


def _ensure_light_pointer(context, ctrl, mesh_obj, marker_color=(0.2, 1.0, 0.4, 1.0), suffix=""):
    """
    Creates or updates the colored light indicator sphere at (0, 0, R) on the controller sphere.
    """
    pointer_name = f"{ctrl.name}_Pointer"
    pointer_obj = bpy.data.objects.get(pointer_name)

    R = max(ctrl.empty_display_size, 0.5)
    r_point = max(0.04, R * 0.065)

    bm = bmesh.new()

    T_point = Matrix.Translation(Vector((0, 0, R)))
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r_point, matrix=T_point)
    for face in bm.faces:
        face.smooth = True

    mesh_data = bpy.data.meshes.get(f"{pointer_name}_Mesh")
    if not mesh_data:
        mesh_data = bpy.data.meshes.new(f"{pointer_name}_Mesh")
    else:
        mesh_data.clear_geometry()

    bm.to_mesh(mesh_data)
    bm.free()

    mat = _get_or_create_pointer_material(color=marker_color, suffix=suffix or ctrl.name)
    if not mesh_data.materials:
        mesh_data.materials.append(mat)
    else:
        mesh_data.materials[0] = mat

    if not pointer_obj:
        pointer_obj = bpy.data.objects.new(pointer_name, mesh_data)
        coll = ctrl.users_collection[0] if ctrl.users_collection else context.scene.collection
        coll.objects.link(pointer_obj)
    else:
        pointer_obj.data = mesh_data

    wire_mod = pointer_obj.modifiers.get("Wireframe")
    if wire_mod:
        pointer_obj.modifiers.remove(wire_mod)

    pointer_obj.parent = ctrl
    pointer_obj.matrix_parent_inverse = Matrix.Identity(4)
    pointer_obj.location = (0, 0, 0)
    pointer_obj.rotation_euler = (0, 0, 0)
    pointer_obj.scale = (1, 1, 1)

    pointer_obj.hide_render = True
    pointer_obj.hide_select = True
    pointer_obj.show_in_front = True
    pointer_obj.color = marker_color

    if hasattr(pointer_obj, "visible_shadow"):
        pointer_obj.visible_shadow = False
    if hasattr(pointer_obj, "visible_diffuse"):
        pointer_obj.visible_diffuse = False
    if hasattr(pointer_obj, "visible_glossy"):
        pointer_obj.visible_glossy = False
    if hasattr(pointer_obj, "visible_transmission"):
        pointer_obj.visible_transmission = False
    if hasattr(pointer_obj, "visible_volume_scatter"):
        pointer_obj.visible_volume_scatter = False

    pointer_obj["anime_bound_mesh"] = mesh_obj
    return pointer_obj


def _create_or_ensure_light_ctrl(context, mesh_obj, light_item, index=0):
    """Creates or updates a sphere controller Empty + Pointer for light_item."""
    ctrl_name = f"{mesh_obj.name}_LightCtrl_{index+1}" if index > 0 else f"{mesh_obj.name}_LightCtrl"
    ctrl = light_item.ctrl_obj
    if not ctrl or ctrl.name not in bpy.data.objects:
        ctrl = bpy.data.objects.get(ctrl_name)
    if not ctrl:
        bpy.ops.object.empty_add(type='SPHERE', location=mesh_obj.location)
        ctrl = context.active_object
        ctrl.name = ctrl_name
        dim = max(mesh_obj.dimensions) if mesh_obj.dimensions else 2.0
        ctrl.empty_display_size = max(dim * 0.8, 1.0)
        ctrl.show_in_front = True
        if index > 0:
            # Offset initial rotation so lights don't face identical directions
            ctrl.rotation_euler = (0.4, 0.0, 1.2 * index)

    ctrl.color = light_item.marker_color
    ctrl["anime_bound_mesh"] = mesh_obj
    ctrl["anime_light_index"] = index
    light_item.ctrl_obj = ctrl
    if index == 0:
        mesh_obj[CTRL_PROP] = ctrl

    _ensure_light_pointer(context, ctrl, mesh_obj, marker_color=light_item.marker_color, suffix=str(index+1))
    return ctrl



# ─────────────────────────────────────────────────────────────────────────────
# SHADER & LIGHT OPERATORS
# ─────────────────────────────────────────────────────────────────────────────

class ANIME_OT_apply_shader(bpy.types.Operator):
    """Create anime MatCap material with a sphere controller for artistic light direction"""
    bl_idname = "anime.apply_shader"
    bl_label = "Apply Anime Shader"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type in {'MESH', 'CURVE', 'FONT', 'SURFACE'}

    def execute(self, context):
        mesh_obj = context.active_object

        # Initialize lights collection on mesh_obj if empty
        if not mesh_obj.anime_lights:
            l1 = mesh_obj.anime_lights.add()
            l1.name = "Key Light"
            l1.marker_color = LIGHT_PALETTE[0]
            l1.light_color = (1.0, 1.0, 1.0, 1.0)
            l1.strength = 1.0
            l1.shadow_position = 0.4
            l1.shadow_softness = 0.08
            l1.specular_size = 0.10
            l1.enabled = True

        ctrl = _create_or_ensure_light_ctrl(context, mesh_obj, mesh_obj.anime_lights[0], index=0)
        mesh_obj.anime_active_light_index = 0

        # Create material
        mat_name = f"M_Anime_{mesh_obj.name}"
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = create_anime_material(name=mat_name, num_lights=max(1, len(mesh_obj.anime_lights)))

        # Assign to mesh (always slot 0 for main material)
        context.view_layer.objects.active = mesh_obj
        if mesh_obj.data.materials:
            mesh_obj.data.materials[0] = mat
        else:
            mesh_obj.data.materials.append(mat)

        # Wire all lights, normal nodes, and drivers
        sync_material_lights(mesh_obj)

        # Auto-heal all materials in scene to ensure full color
        heal_anime_materials()

        # Switch viewport to Material Preview
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        space.shading.show_backface_culling = True
                        break
                break

        # Select controller so user can immediately rotate it with R
        for o in context.view_layer.objects:
            o.select_set(False)
        ctrl.select_set(True)
        context.view_layer.objects.active = ctrl

        self.report({'INFO'}, f"Anime shader applied! Rotate '{ctrl.name}' sphere to move shadows.")
        return {'FINISHED'}


class ANIME_OT_light_add(bpy.types.Operator):
    """Add a new anime light source with a color-coded scene marker"""
    bl_idname = "anime.light_add"
    bl_label = "Add Light"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        mesh = _resolve_mesh(context)
        return mesh is not None and len(mesh.data.materials) > 0

    def execute(self, context):
        mesh = _resolve_mesh(context)
        if not mesh:
            return {'CANCELLED'}

        idx = len(mesh.anime_lights)
        color = LIGHT_PALETTE[idx % len(LIGHT_PALETTE)]

        default_names = ["Key Light", "Fill Light", "Rim Light", "Bounce Light", "Top Light"]
        light_name = default_names[idx] if idx < len(default_names) else f"Light {idx + 1}"

        item = mesh.anime_lights.add()
        item.name = light_name
        item.marker_color = color
        item.light_color = color
        item.strength = 1.0
        item.shadow_position = 0.4
        item.shadow_softness = 0.08
        item.specular_size = 0.10
        item.enabled = True
        item.opacity = 1.0
        item.blend_mode = 'COVER'

        ctrl = _create_or_ensure_light_ctrl(context, mesh, item, index=idx)
        mesh.anime_active_light_index = idx

        sync_material_lights(mesh)

        # Select the new controller empty in 3D viewport
        for o in context.view_layer.objects:
            o.select_set(False)
        ctrl.select_set(True)
        context.view_layer.objects.active = ctrl

        self.report({'INFO'}, f"Added {light_name} with colored marker!")
        return {'FINISHED'}


class ANIME_OT_light_move(bpy.types.Operator):
    """Move light layer up or down in the stack"""
    bl_idname = "anime.light_move"
    bl_label = "Move Light Layer"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(
        name="Direction",
        items=[
            ('UP', "Up", "Move up in layer stack"),
            ('DOWN', "Down", "Move down in layer stack"),
        ],
        default='UP',
    )

    @classmethod
    def poll(cls, context):
        mesh = _resolve_mesh(context)
        return mesh is not None and len(mesh.anime_lights) > 1

    def execute(self, context):
        mesh = _resolve_mesh(context)
        if not mesh or not mesh.anime_lights:
            return {'CANCELLED'}

        idx = mesh.anime_active_light_index
        n = len(mesh.anime_lights)

        if self.direction == 'UP':
            if idx <= 0:
                return {'CANCELLED'}
            target_idx = idx - 1
        else:  # 'DOWN'
            if idx >= n - 1:
                return {'CANCELLED'}
            target_idx = idx + 1

        mesh.anime_lights.move(idx, target_idx)
        mesh.anime_active_light_index = target_idx

        # Re-sync materials with new light order
        sync_material_lights(mesh)

        if context.area:
            context.area.tag_redraw()

        self.report({'INFO'}, f"Moved light to layer {target_idx + 1}")
        return {'FINISHED'}


class ANIME_OT_light_remove(bpy.types.Operator):
    """Remove an anime light source"""
    bl_idname = "anime.light_remove"
    bl_label = "Remove Light"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty(
        name="Light Index",
        description="Index of light to remove (-1 for active light)",
        default=-1,
    )

    @classmethod
    def poll(cls, context):
        mesh = _resolve_mesh(context)
        return mesh is not None and len(mesh.anime_lights) > 1

    def execute(self, context):
        mesh = _resolve_mesh(context)
        if not mesh or len(mesh.anime_lights) <= 1:
            self.report({'WARNING'}, "Cannot remove the only light source.")
            return {'CANCELLED'}

        idx = self.index if 0 <= self.index < len(mesh.anime_lights) else mesh.anime_active_light_index
        if not (0 <= idx < len(mesh.anime_lights)):
            idx = len(mesh.anime_lights) - 1

        item = mesh.anime_lights[idx]
        ctrl = item.ctrl_obj
        if ctrl and ctrl.name in bpy.data.objects:
            pointer = bpy.data.objects.get(f"{ctrl.name}_Pointer")
            if pointer:
                bpy.data.objects.remove(pointer, do_unlink=True)
            bpy.data.objects.remove(ctrl, do_unlink=True)

        mesh.anime_lights.remove(idx)
        mesh.anime_active_light_index = max(0, min(idx, len(mesh.anime_lights) - 1))

        sync_material_lights(mesh)

        # Select new active light's controller
        if mesh.anime_lights:
            new_active = mesh.anime_lights[mesh.anime_active_light_index]
            if new_active.ctrl_obj and new_active.ctrl_obj.name in bpy.data.objects:
                for o in context.view_layer.objects:
                    o.select_set(False)
                new_active.ctrl_obj.select_set(True)
                context.view_layer.objects.active = new_active.ctrl_obj

        self.report({'INFO'}, "Light source removed.")
        return {'FINISHED'}


class ANIME_OT_light_toggle_visibility(bpy.types.Operator):
    """Toggle visibility and mute of this light source in viewport and shader"""
    bl_idname = "anime.light_toggle_visibility"
    bl_label = "Toggle Light Visibility"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty(name="Light Index", default=-1)

    def execute(self, context):
        mesh = _resolve_mesh(context)
        if not mesh or not mesh.anime_lights:
            return {'CANCELLED'}
        idx = self.index if 0 <= self.index < len(mesh.anime_lights) else mesh.anime_active_light_index
        if not (0 <= idx < len(mesh.anime_lights)):
            return {'CANCELLED'}

        light = mesh.anime_lights[idx]
        light.enabled = not light.enabled
        ctrl = light.ctrl_obj
        if ctrl and ctrl.name in bpy.data.objects:
            ctrl.hide_viewport = not light.enabled
            ptr = bpy.data.objects.get(f"{ctrl.name}_Pointer")
            if ptr:
                ptr.hide_viewport = not light.enabled
        sync_material_lights(mesh)
        if context.area:
            context.area.tag_redraw()
        return {'FINISHED'}


class ANIME_OT_light_popup_settings(bpy.types.Operator):
    """Open dedicated settings dialog window for this light source"""
    bl_idname = "anime.light_popup_settings"
    bl_label = "Light Settings"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty(name="Light Index", default=-1)

    def invoke(self, context, event):
        mesh = _resolve_mesh(context)
        if not mesh or not mesh.anime_lights:
            return {'CANCELLED'}
        if 0 <= self.index < len(mesh.anime_lights):
            mesh.anime_active_light_index = self.index
        return context.window_manager.invoke_props_dialog(self, width=320)

    def check(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        mesh = _resolve_mesh(context)
        if not mesh or not mesh.anime_lights:
            layout.label(text="No active mesh or light.", icon='INFO')
            return

        idx = self.index if 0 <= self.index < len(mesh.anime_lights) else mesh.anime_active_light_index
        if not (0 <= idx < len(mesh.anime_lights)):
            return

        light = mesh.anime_lights[idx]
        ctrl = light.ctrl_obj

        # Header: Marker + Name
        top = layout.row(align=True)
        sub = top.row(align=True)
        sub.scale_x = 0.5
        sub.prop(light, "marker_color", text="")
        top.prop(light, "name", text="")

        layout.separator()

        # Direction (Euler)
        if ctrl and ctrl.name in bpy.data.objects:
            layout.label(text="Light Direction (Controller Euler):", icon='EMPTY_DATA')
            layout.prop(ctrl, "rotation_euler", text="")

            ptr = bpy.data.objects.get(f"{ctrl.name}_Pointer")
            if ptr:
                layout.prop(ptr, "hide_viewport", text="Show Scene Pointer Sphere", icon='HIDE_OFF' if not ptr.hide_viewport else 'HIDE_ON')

        layout.separator()

        # Light Beam
        layout.label(text="Light Properties:", icon='LIGHT_SUN')
        r_beam = layout.row(align=True)
        r_beam.prop(light, "light_color", text="Color")
        r_beam.prop(light, "strength", text="Strength")

        layout.separator()

        # Shadow & Specular
        layout.label(text="Shadow & Shading:", icon='MOD_FLUIDSIM')
        layout.prop(light, "shadow_position", text="Shadow Position", slider=True)
        layout.prop(light, "shadow_softness", text="Shadow Softness", slider=True)
        layout.prop(light, "specular_size", text="Specular Highlight", slider=True)

    def execute(self, context):
        mesh = _resolve_mesh(context)
        if mesh:
            sync_material_lights(mesh)
        return {'FINISHED'}


class ANIME_OT_light_select(bpy.types.Operator):
    """Select the active light's controller empty in 3D viewport"""
    bl_idname = "anime.light_select"
    bl_label = "Select Light Controller"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty(name="Light Index", default=-1)

    def execute(self, context):
        mesh = _resolve_mesh(context)
        if not mesh or not mesh.anime_lights:
            return {'CANCELLED'}
        idx = self.index if 0 <= self.index < len(mesh.anime_lights) else mesh.anime_active_light_index
        if 0 <= idx < len(mesh.anime_lights):
            mesh.anime_active_light_index = idx
            ctrl = mesh.anime_lights[idx].ctrl_obj
            if ctrl and ctrl.name in bpy.data.objects:
                for o in context.view_layer.objects:
                    o.select_set(False)
                ctrl.select_set(True)
                context.view_layer.objects.active = ctrl
                self.report({'INFO'}, f"Selected controller '{ctrl.name}'")
                return {'FINISHED'}
        return {'CANCELLED'}


class ANIME_OT_apply_preset(bpy.types.Operator):
    """Apply a styled color preset to the active Anime Shader"""
    bl_idname = "anime.apply_preset"
    bl_label = "Apply Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.EnumProperty(
        name="Preset",
        items=[
            ('CLASSIC', "Classic Cel", "Sharp 2-tone anime"),
            ('GHIBLI', "Soft Ghibli", "Warm watercolor-style"),
            ('SUNSET', "Warm Sunset", "Golden light, violet shadow"),
            ('CYBER', "Cyberpunk", "Neon with dark shadows"),
        ],
        default='CLASSIC'
    )

    @classmethod
    def poll(cls, context):
        mesh = _resolve_mesh(context)
        return mesh is not None and mesh.active_material and find_anime_toon_node(mesh.active_material) is not None

    def execute(self, context):
        mesh = _resolve_mesh(context)
        node = find_anime_toon_node(mesh.active_material) if mesh else None
        if not node:
            self.report({'WARNING'}, "No Anime Shader found.")
            return {'CANCELLED'}

        presets = {
            'CLASSIC': {
                'Base Color':       (0.92, 0.78, 0.68, 1.0),
                'Shadow Color':     (0.55, 0.42, 0.52, 1.0),
                'Shadow Position':  0.4,
                'Shadow Softness':  0.08,
                'Specular Size':    0.10,
            },
            'GHIBLI': {
                'Base Color':       (0.96, 0.84, 0.72, 1.0),
                'Shadow Color':     (0.72, 0.54, 0.50, 1.0),
                'Shadow Position':  0.3,
                'Shadow Softness':  0.25,
                'Specular Size':    0.0,
            },
            'SUNSET': {
                'Base Color':       (1.0, 0.74, 0.55, 1.0),
                'Shadow Color':     (0.36, 0.20, 0.44, 1.0),
                'Shadow Position':  0.35,
                'Shadow Softness':  0.06,
                'Specular Size':    0.15,
            },
            'CYBER': {
                'Base Color':       (0.18, 0.76, 0.96, 1.0),
                'Shadow Color':     (0.06, 0.04, 0.20, 1.0),
                'Shadow Position':  0.35,
                'Shadow Softness':  0.04,
                'Specular Size':    0.20,
            },
        }

        chosen = presets[self.preset]
        if 'Base Color' in node.inputs:
            node.inputs['Base Color'].default_value = chosen['Base Color']
        if 'Shadow Color' in node.inputs:
            node.inputs['Shadow Color'].default_value = chosen['Shadow Color']

        # Update active light tuning
        if mesh and mesh.anime_lights:
            idx = mesh.anime_active_light_index
            if 0 <= idx < len(mesh.anime_lights):
                l = mesh.anime_lights[idx]
                l.shadow_position = chosen['Shadow Position']
                l.shadow_softness = chosen['Shadow Softness']
                l.specular_size = chosen['Specular Size']
            sync_material_lights(mesh)

        self.report({'INFO'}, f"Preset '{self.preset}' applied!")
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
# INVERTED HULL OUTLINE OPERATORS
# ─────────────────────────────────────────────────────────────────────────────

class ANIME_OT_add_outline(bpy.types.Operator):
    """Add anime black ink outlines (Inverted Hull Solidify method) to the active mesh"""
    bl_idname = "anime.add_outline"
    bl_label = "Add Anime Outlines"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        mesh = _resolve_mesh(context)
        return mesh is not None and mesh.type == 'MESH'

    def execute(self, context):
        mesh = _resolve_mesh(context)
        scene = context.scene
        if not mesh:
            return {'CANCELLED'}

        # 1. Get or create outline material specific to this mesh
        outline_mat = get_or_create_outline_material(mesh)

        # Apply current mesh outline settings to the material
        style = getattr(mesh, 'anime_outline_style', getattr(scene, 'anime_outline_style', 'SOLID'))
        chaos = getattr(mesh, 'anime_outline_chaos', getattr(scene, 'anime_outline_chaos', 0.25))
        opacity = getattr(mesh, 'anime_outline_opacity', getattr(scene, 'anime_outline_opacity', 1.0))
        scale = getattr(mesh, 'anime_outline_scale', getattr(scene, 'anime_outline_scale', 20.0))
        color = getattr(mesh, 'anime_outline_color', getattr(scene, 'anime_outline_color', (0.0, 0.0, 0.0, 1.0)))

        set_outline_style(outline_mat, style)
        set_outline_chaos(outline_mat, chaos)
        set_outline_opacity(outline_mat, opacity)
        set_outline_scale(outline_mat, scale)
        emit = find_outline_emission_node(outline_mat)
        if emit:
            emit.inputs['Color'].default_value = color

        # 2. Add material slot to mesh if not already present
        mat_idx = -1
        for i, m in enumerate(mesh.data.materials):
            if m and m.name == outline_mat.name:
                mat_idx = i
                break

        if mat_idx == -1:
            mesh.data.materials.append(outline_mat)
            mat_idx = len(mesh.data.materials) - 1

        # 3. Create or reuse Solidify modifier
        mod = mesh.modifiers.get(OUTLINE_MOD_NAME)
        if not mod:
            mod = mesh.modifiers.new(name=OUTLINE_MOD_NAME, type='SOLIDIFY')

        thick = getattr(mesh, 'anime_outline_thickness', getattr(scene, 'anime_outline_thickness', 0.02))
        mod.thickness = max(0.001, thick)
        mod.offset = 1.0                # Push shell outward
        mod.use_flip_normals = True     # Invert normals for backface culling
        mod.use_rim = False             # Do not create solid walls on open edges
        mod.material_offset = mat_idx   # Assign outline material slot
        mod.material_offset_rim = mat_idx
        mod.show_viewport = True
        mod.show_render = True

        # 4. Sync secondary Stray Outline (hand-drawn sketch extra strokes)
        sync_stray_outline(mesh)

        # Switch viewport to Material Preview so backface culling is active immediately
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        space.shading.show_backface_culling = True
                        break
                break

        self.report({'INFO'}, f"Anime Outlines added to '{mesh.name}'!")
        return {'FINISHED'}


def sync_stray_outline(mesh, scene=None):
    """
    Syncs the secondary Stray Strokes solidify modifier and material for this mesh.
    Creates broken, hasty hand-drawn extra strokes around the silhouette.
    """
    if not mesh or mesh.type != 'MESH':
        return

    stray_mod = mesh.modifiers.get(OUTLINE_STRAY_MOD_NAME)
    enabled = getattr(mesh, 'anime_stray_enable', True) if hasattr(mesh, 'anime_stray_enable') else (getattr(scene, 'anime_stray_enable', True) if scene else True)

    if not enabled:
        if stray_mod:
            stray_mod.show_viewport = False
            stray_mod.show_render = False
        return

    # Check existing material slots first to avoid creating duplicate stray materials
    stray_mat = None
    stray_idx = -1
    if stray_mod and 0 <= stray_mod.material_offset < len(mesh.data.materials):
        candidate = mesh.data.materials[stray_mod.material_offset]
        if candidate and candidate.node_tree and ("stray" in candidate.name.lower() or candidate.node_tree.nodes.get("StrayEmission")):
            stray_mat = candidate
            stray_idx = stray_mod.material_offset

    if not stray_mat:
        for i, m in enumerate(mesh.data.materials):
            if m and m.node_tree and ("stray" in m.name.lower() or m.node_tree.nodes.get("StrayEmission")):
                stray_mat = m
                stray_idx = i
                break

    if not stray_mat:
        stray_mat = get_or_create_stray_outline_material(mesh)
        mesh.data.materials.append(stray_mat)
        stray_idx = len(mesh.data.materials) - 1

    src = mesh if hasattr(mesh, 'anime_stray_density') else scene
    if src:
        if hasattr(src, 'anime_stray_density'):
            set_stray_density(stray_mat, src.anime_stray_density)
        if hasattr(src, 'anime_stray_opacity'):
            set_stray_opacity(stray_mat, src.anime_stray_opacity)
        if hasattr(src, 'anime_stray_jitter'):
            set_stray_jitter(stray_mat, src.anime_stray_jitter)
        if hasattr(src, 'anime_outline_color'):
            set_stray_color(stray_mat, src.anime_outline_color)

    # Ensure modifier on mesh
    if not stray_mod:
        stray_mod = mesh.modifiers.new(name=OUTLINE_STRAY_MOD_NAME, type='SOLIDIFY')

    base_thick = getattr(mesh, 'anime_outline_thickness', 0.02)
    offset = getattr(mesh, 'anime_stray_offset', 0.012)
    stray_mod.thickness = max(0.001, base_thick + offset)
    stray_mod.offset = 1.0
    stray_mod.use_flip_normals = True
    stray_mod.use_rim = False
    stray_mod.material_offset = stray_idx
    stray_mod.material_offset_rim = stray_idx
    stray_mod.show_viewport = True
    stray_mod.show_render = True


class ANIME_OT_toggle_outline(bpy.types.Operator):
    """Toggle visibility of anime outlines in the viewport"""
    bl_idname = "anime.toggle_outline"
    bl_label = "Toggle Outlines"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        mesh = _resolve_mesh(context)
        return mesh is not None and OUTLINE_MOD_NAME in mesh.modifiers

    def execute(self, context):
        mesh = _resolve_mesh(context)
        if not mesh:
            return {'CANCELLED'}
        mod = mesh.modifiers.get(OUTLINE_MOD_NAME)
        stray_mod = mesh.modifiers.get(OUTLINE_STRAY_MOD_NAME)
        if mod:
            new_state = not mod.show_viewport
            mod.show_viewport = new_state
            if stray_mod:
                stray_mod.show_viewport = new_state
            state = "ON" if new_state else "OFF"
            self.report({'INFO'}, f"Outlines {state}")
            return {'FINISHED'}
        return {'CANCELLED'}


class ANIME_OT_remove_outline(bpy.types.Operator):
    """Remove anime outlines modifier from the active mesh"""
    bl_idname = "anime.remove_outline"
    bl_label = "Remove Outlines"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        mesh = _resolve_mesh(context)
        return mesh is not None and OUTLINE_MOD_NAME in mesh.modifiers

    def execute(self, context):
        mesh = _resolve_mesh(context)
        if not mesh:
            return {'CANCELLED'}
        mod = mesh.modifiers.get(OUTLINE_MOD_NAME)
        if mod:
            mesh.modifiers.remove(mod)
        stray_mod = mesh.modifiers.get(OUTLINE_STRAY_MOD_NAME)
        if stray_mod:
            mesh.modifiers.remove(stray_mod)
        self.report({'INFO'}, f"Outlines removed from '{mesh.name}'")
        return {'FINISHED'}


classes = (
    AnimeLightItem,
    ANIME_OT_apply_shader,
    ANIME_OT_apply_preset,
    ANIME_OT_light_add,
    ANIME_OT_light_move,
    ANIME_OT_light_remove,
    ANIME_OT_light_toggle_visibility,
    ANIME_OT_light_popup_settings,
    ANIME_OT_light_select,
    ANIME_OT_add_outline,
    ANIME_OT_toggle_outline,
    ANIME_OT_remove_outline,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass
    bpy.types.Object.anime_lights = bpy.props.CollectionProperty(type=AnimeLightItem)
    bpy.types.Object.anime_active_light_index = bpy.props.IntProperty(name="Active Light Index", default=0)
    try:
        heal_anime_materials()
    except Exception:
        pass


def unregister():
    if hasattr(bpy.types.Object, "anime_active_light_index"):
        del bpy.types.Object.anime_active_light_index
    if hasattr(bpy.types.Object, "anime_lights"):
        del bpy.types.Object.anime_lights
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            pass
