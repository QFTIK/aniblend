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
)


def _resolve_mesh(context):
    """Helper to get the bound mesh from any selected object (mesh or sphere controller)."""
    obj = context.active_object
    if not obj:
        return None
    if obj.type == 'EMPTY' and "anime_bound_mesh" in obj:
        mesh = obj["anime_bound_mesh"]
        if mesh and mesh.name in bpy.data.objects:
            return mesh
    if obj.type in {'MESH', 'CURVE', 'FONT', 'SURFACE'}:
        return obj
    return None


def _get_or_create_pointer_material():
    """Neon lime-green emission material for the light source point and arrow."""
    mat_name = "M_AniBlend_LightGizmo"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        emit = nodes.new('ShaderNodeEmission')
        emit.inputs['Color'].default_value = (0.15, 1.0, 0.25, 1.0)
        emit.inputs['Strength'].default_value = 2.5
        mat.node_tree.links.new(emit.outputs['Emission'], out.inputs['Surface'])
    mat.diffuse_color = (0.15, 1.0, 0.25, 1.0)
    return mat


def _ensure_light_pointer(context, ctrl, mesh_obj):
    """
    Creates or updates the green light indicator sphere and incoming light vector arrow.
    Points from (0, 0, R) on the sphere towards (0, 0, 0) into the center of the model.
    """
    pointer_name = f"{ctrl.name}_Pointer"
    pointer_obj = bpy.data.objects.get(pointer_name)

    R = max(ctrl.empty_display_size, 0.5)
    r_point = max(0.06, R * 0.09)

    bm = bmesh.new()

    # 1. Green Light Point sphere at (0, 0, R)
    T_point = Matrix.Translation(Vector((0, 0, R)))
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r_point, matrix=T_point)

    # 2. Vector line/shaft towards center (0, 0, 0)
    shaft_len = max(0.1, (R - r_point) - (R * 0.35))
    z_mid = (R * 0.35) + shaft_len / 2.0
    T_shaft = Matrix.Translation(Vector((0, 0, z_mid)))
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=12,
        radius1=r_point * 0.22,
        radius2=r_point * 0.22,
        depth=shaft_len,
        matrix=T_shaft,
    )

    # 3. Arrowhead cone pointing towards center
    cone_len = max(0.1, R * 0.28)
    z_cone = (0.05 * R) + cone_len / 2.0
    T_cone = Matrix.Translation(Vector((0, 0, z_cone)))
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=12,
        radius1=0.001,          # tip pointing down -Z into center
        radius2=r_point * 0.65,  # base
        depth=cone_len,
        matrix=T_cone,
    )

    mesh_data = bpy.data.meshes.get(f"{pointer_name}_Mesh")
    if not mesh_data:
        mesh_data = bpy.data.meshes.new(f"{pointer_name}_Mesh")
    else:
        mesh_data.clear_geometry()

    bm.to_mesh(mesh_data)
    bm.free()

    mat = _get_or_create_pointer_material()
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

    # Setup parenting & flags
    pointer_obj.parent = ctrl
    pointer_obj.matrix_parent_inverse = Matrix.Identity(4)
    pointer_obj.location = (0, 0, 0)
    pointer_obj.rotation_euler = (0, 0, 0)
    pointer_obj.scale = (1, 1, 1)

    pointer_obj.hide_render = True
    pointer_obj.hide_select = True
    pointer_obj.show_in_front = True
    pointer_obj["anime_bound_mesh"] = mesh_obj

    return pointer_obj


def _find_or_create_ctrl(context, mesh_obj):
    """Find existing or create new light-direction sphere controller for a mesh."""
    existing = mesh_obj.get(CTRL_PROP)
    if existing and isinstance(existing, bpy.types.Object) and existing.name in bpy.data.objects:
        _ensure_light_pointer(context, existing, mesh_obj)
        return existing

    bpy.ops.object.empty_add(type='SPHERE', location=mesh_obj.location)
    ctrl = context.active_object
    ctrl.name = f"{mesh_obj.name}_LightCtrl"
    dim = max(mesh_obj.dimensions) if mesh_obj.dimensions else 2.0
    ctrl.empty_display_size = max(dim * 0.8, 1.0)
    ctrl.show_in_front = True

    mesh_obj[CTRL_PROP] = ctrl
    ctrl["anime_bound_mesh"] = mesh_obj

    _ensure_light_pointer(context, ctrl, mesh_obj)
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

        # Create or reuse sphere controller
        ctrl = _find_or_create_ctrl(context, mesh_obj)

        # Create material
        mat = create_anime_material(name=f"M_Anime_{mesh_obj.name}")

        # Assign to mesh (always slot 0 for main material)
        context.view_layer.objects.active = mesh_obj
        if mesh_obj.data.materials:
            mesh_obj.data.materials[0] = mat
        else:
            mesh_obj.data.materials.append(mat)

        # Wire drivers: sphere rotation → shader light direction
        setup_sphere_drivers(mat, ctrl)

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

        for key, val in presets[self.preset].items():
            inp = node.inputs.get(key)
            if inp:
                inp.default_value = val

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
    ANIME_OT_apply_shader,
    ANIME_OT_apply_preset,
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
    try:
        heal_anime_materials()
    except Exception:
        pass


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            pass
