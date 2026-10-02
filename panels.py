"""
Tabbed UI Panel for AniBlend (Light & Outline tabs).
Features Hand-Drawn Chaos, Opacity, Styles (Solid, Ink/Pen, Dashed, Sketch), Density, and Color.
"""

import bpy
from .shader_builder import (
    find_anime_toon_node, CTRL_PROP,
    OUTLINE_MOD_NAME, OUTLINE_MAT_NAME,
    OUTLINE_STRAY_MOD_NAME, OUTLINE_STRAY_MAT_NAME,
    set_outline_style, set_outline_chaos, set_outline_opacity, set_outline_scale,
    find_outline_emission_node,
    get_or_create_outline_material, get_or_create_stray_outline_material,
    set_stray_color,
)
from .operators import sync_stray_outline




def _get_mesh_and_node(context):
    """Resolve the mesh and anime toon node from active object (mesh or controller)."""
    obj = context.active_object
    if not obj:
        return None, None

    mesh = None
    if obj.type == 'EMPTY' and "anime_bound_mesh" in obj:
        mesh = obj["anime_bound_mesh"]
    elif obj.type in {'MESH', 'CURVE', 'FONT', 'SURFACE'}:
        mesh = obj
    else:
        return None, None

    if mesh and mesh.active_material:
        node = find_anime_toon_node(mesh.active_material)
        return mesh, node
    return mesh, None


def _resolve_target_mesh(self, context):
    """Resolve target mesh whether callback is fired on Object or Scene."""
    if isinstance(self, bpy.types.Object):
        if self.type == 'EMPTY' and "anime_bound_mesh" in self:
            return self["anime_bound_mesh"]
        return self
    mesh, _ = _get_mesh_and_node(context)
    return mesh


def _tag_viewport_redraw(context):
    """Force real-time 3D viewport redraw when outline properties change."""
    if context and hasattr(context, 'screen') and context.screen:
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def _find_active_outline_mat(mesh):
    """Finds the actual outline material in the mesh slots or modifier."""
    if not mesh:
        return None
    mod = mesh.modifiers.get(OUTLINE_MOD_NAME)
    if mod and 0 <= mod.material_offset < len(mesh.data.materials):
        mat = mesh.data.materials[mod.material_offset]
        if mat and mat.node_tree:
            return mat
    for m in mesh.data.materials:
        if m and m.node_tree and find_outline_emission_node(m):
            return m
    return get_or_create_outline_material(mesh)


def _find_active_stray_mat(mesh):
    """Finds the actual stray outline material in the mesh slots or modifier."""
    if not mesh:
        return None
    stray_mod = mesh.modifiers.get(OUTLINE_STRAY_MOD_NAME)
    if stray_mod and 0 <= stray_mod.material_offset < len(mesh.data.materials):
        mat = mesh.data.materials[stray_mod.material_offset]
        if mat and mat.node_tree:
            return mat
    for m in mesh.data.materials:
        if m and m.node_tree and ("stray" in m.name.lower() or m.node_tree.nodes.get("StrayEmission")):
            return m
    return get_or_create_stray_outline_material(mesh)


def _update_thickness(self, context):
    """Safely apply positive thickness to this mesh's Solidify modifier."""
    mesh = _resolve_target_mesh(self, context)
    if mesh and mesh.type == 'MESH':
        val = getattr(mesh, 'anime_outline_thickness', getattr(self, 'anime_outline_thickness', 0.02))
        mod = mesh.modifiers.get(OUTLINE_MOD_NAME)
        if mod:
            mod.thickness = max(0.001, val)
        sync_stray_outline(mesh)
        _tag_viewport_redraw(context)


def _update_chaos(self, context):
    """Update organic hand-drawn jitter & stroke chaos in this mesh's outline material."""
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        val = getattr(mesh, 'anime_outline_chaos', getattr(self, 'anime_outline_chaos', 0.25))
        outline_mat = _find_active_outline_mat(mesh)
        if outline_mat:
            set_outline_chaos(outline_mat, val)
            outline_mat.update_tag()
        _tag_viewport_redraw(context)


def _update_opacity(self, context):
    """Update outline opacity/alpha in this mesh's outline material."""
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        val = getattr(mesh, 'anime_outline_opacity', getattr(self, 'anime_outline_opacity', 1.0))
        outline_mat = _find_active_outline_mat(mesh)
        if outline_mat:
            set_outline_opacity(outline_mat, val)
            outline_mat.update_tag()
        _tag_viewport_redraw(context)


def _update_style(self, context):
    """Switch outline pattern between Solid, Ink/Pen, Dashed, and Sketch for this mesh."""
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        val = getattr(mesh, 'anime_outline_style', getattr(self, 'anime_outline_style', 'SOLID'))
        outline_mat = _find_active_outline_mat(mesh)
        if outline_mat:
            set_outline_style(outline_mat, val)
            outline_mat.update_tag()
        _tag_viewport_redraw(context)


def _update_scale(self, context):
    """Update stroke density / frequency for this mesh."""
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        val = getattr(mesh, 'anime_outline_scale', getattr(self, 'anime_outline_scale', 20.0))
        outline_mat = _find_active_outline_mat(mesh)
        if outline_mat:
            set_outline_scale(outline_mat, val)
            outline_mat.update_tag()
        _tag_viewport_redraw(context)


def _update_color(self, context):
    """Update ink emission color in this mesh's outline materials."""
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        val = getattr(mesh, 'anime_outline_color', getattr(self, 'anime_outline_color', (0.0, 0.0, 0.0, 1.0)))
        outline_mat = _find_active_outline_mat(mesh)
        if outline_mat:
            emit = find_outline_emission_node(outline_mat)
            if emit:
                emit.inputs['Color'].default_value = val
            outline_mat.update_tag()
        stray_mat = _find_active_stray_mat(mesh)
        if stray_mat:
            set_stray_color(stray_mat, val)
            stray_mat.update_tag()
        _tag_viewport_redraw(context)


def _update_stray(self, context):
    """Update secondary stray stroke parameters and modifier for this mesh."""
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        sync_stray_outline(mesh)
        stray_mat = _find_active_stray_mat(mesh)
        if stray_mat:
            stray_mat.update_tag()
        _tag_viewport_redraw(context)


def _update_tab(self, context):
    """Force UI and viewport redraw when tab filter changes."""
    _tag_viewport_redraw(context)


class ANIME_PT_main_panel(bpy.types.Panel):
    bl_label = "AniBlend"
    bl_idname = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        mesh, node = _get_mesh_and_node(context)

        # Tab filter row: All / Light / Outline
        row = layout.row(align=True)
        row.prop(scene, "anime_active_tab", expand=True)

        if not mesh:
            layout.separator()
            box = layout.box()
            box.label(text="Select a 3D Mesh to begin", icon='INFO')
            return

        active_tab = scene.anime_active_tab

        # Quick Actions Header
        col = layout.column(align=True)
        col.scale_y = 1.25

        if active_tab in {'ALL', 'LIGHT'}:
            if not node:
                col.operator("anime.apply_shader", text="Apply Anime Shader", icon='SHADING_RENDERED')
            else:
                col.operator("anime.apply_shader", text="Reset / Re-apply Shader", icon='FILE_REFRESH')

        if active_tab in {'ALL', 'OUTLINE'}:
            mod = mesh.modifiers.get(OUTLINE_MOD_NAME)
            if not mod:
                col.operator("anime.add_outline", text="Add Outlines", icon='LINE_DATA')
            else:
                row_out = col.row(align=True)
                if mod.show_viewport:
                    row_out.operator("anime.toggle_outline", text="Outlines: Visible", icon='HIDE_OFF')
                else:
                    row_out.operator("anime.toggle_outline", text="Outlines: Hidden", icon='HIDE_ON')
                row_out.operator("anime.remove_outline", text="", icon='TRASH')


class ANIME_PT_light_direction(bpy.types.Panel):
    bl_label = "Light Direction"
    bl_idname = "ANIME_PT_light_direction"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab not in {'ALL', 'LIGHT'}:
            return False
        mesh, node = _get_mesh_and_node(context)
        return mesh is not None and node is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='LIGHT_SUN')

    def draw(self, context):
        layout = self.layout
        mesh, _ = _get_mesh_and_node(context)
        ctrl = mesh.get(CTRL_PROP) if mesh else None
        if ctrl and ctrl.name in bpy.data.objects:
            row = layout.row(align=True)
            row.label(text=f"Controller: {ctrl.name}", icon='EMPTY_DATA')
            layout.prop(ctrl, "rotation_euler", text="Rotation")
            layout.label(text="Rotate helper sphere with R to aim shadows", icon='INFO')
        else:
            layout.label(text="No controller linked. Re-apply shader to generate.", icon='INFO')


class ANIME_PT_light_colors(bpy.types.Panel):
    bl_label = "Shading Colors"
    bl_idname = "ANIME_PT_light_colors"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab not in {'ALL', 'LIGHT'}:
            return False
        mesh, node = _get_mesh_and_node(context)
        return mesh is not None and node is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='COLOR')

    def draw(self, context):
        layout = self.layout
        _, node = _get_mesh_and_node(context)
        if node and 'Base Color' in node.inputs and 'Shadow Color' in node.inputs:
            row = layout.row(align=True)
            row.prop(node.inputs['Base Color'], "default_value", text="Light")
            row.prop(node.inputs['Shadow Color'], "default_value", text="Shadow")


class ANIME_PT_light_tuning(bpy.types.Panel):
    bl_label = "Shading Tuning"
    bl_idname = "ANIME_PT_light_tuning"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab not in {'ALL', 'LIGHT'}:
            return False
        mesh, node = _get_mesh_and_node(context)
        return mesh is not None and node is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='MOD_SMOOTH')

    def draw(self, context):
        layout = self.layout
        _, node = _get_mesh_and_node(context)
        if node:
            col = layout.column(align=True)
            if 'Shadow Position' in node.inputs:
                col.prop(node.inputs['Shadow Position'], "default_value", text="Shadow Position", slider=True)
            if 'Shadow Softness' in node.inputs:
                col.prop(node.inputs['Shadow Softness'], "default_value", text="Shadow Softness", slider=True)
            if 'Specular Size' in node.inputs:
                col.prop(node.inputs['Specular Size'], "default_value", text="Highlight Size", slider=True)


class ANIME_PT_light_presets(bpy.types.Panel):
    bl_label = "Color Presets"
    bl_idname = "ANIME_PT_light_presets"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab not in {'ALL', 'LIGHT'}:
            return False
        mesh, node = _get_mesh_and_node(context)
        return mesh is not None and node is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='PRESET')

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        r1 = col.row(align=True)
        op1 = r1.operator("anime.apply_preset", text="Classic Cel")
        op1.preset = 'CLASSIC'
        op2 = r1.operator("anime.apply_preset", text="Soft Ghibli")
        op2.preset = 'GHIBLI'
        r2 = col.row(align=True)
        op3 = r2.operator("anime.apply_preset", text="Warm Sunset")
        op3.preset = 'SUNSET'
        op4 = r2.operator("anime.apply_preset", text="Cyberpunk")
        op4.preset = 'CYBER'


class ANIME_PT_outline_settings(bpy.types.Panel):
    bl_label = "Line Settings"
    bl_idname = "ANIME_PT_outline_settings"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab not in {'ALL', 'OUTLINE'}:
            return False
        mesh, _ = _get_mesh_and_node(context)
        return mesh is not None and mesh.modifiers.get(OUTLINE_MOD_NAME) is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='STROKE')

    def draw(self, context):
        layout = self.layout
        mesh, _ = _get_mesh_and_node(context)
        if mesh:
            col = layout.column(align=True)
            col.prop(mesh, "anime_outline_thickness", text="Thickness", slider=True)
            col.prop(mesh, "anime_outline_opacity",   text="Opacity", slider=True)
            col.prop(mesh, "anime_outline_color",     text="Color")


class ANIME_PT_outline_style(bpy.types.Panel):
    bl_label = "Stroke Style & Chaos"
    bl_idname = "ANIME_PT_outline_style"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab not in {'ALL', 'OUTLINE'}:
            return False
        mesh, _ = _get_mesh_and_node(context)
        return mesh is not None and mesh.modifiers.get(OUTLINE_MOD_NAME) is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='BRUSH_DATA')

    def draw(self, context):
        layout = self.layout
        mesh, _ = _get_mesh_and_node(context)
        if mesh:
            row = layout.row(align=True)
            row.prop(mesh, "anime_outline_style", expand=True)

            col = layout.column(align=True)
            col.prop(mesh, "anime_outline_chaos", text="Hand Tremor", slider=True)
            if mesh.anime_outline_style in {'DASHED', 'SKETCH', 'INK'}:
                col.prop(mesh, "anime_outline_scale", text="Stroke Density", slider=True)


class ANIME_PT_outline_stray(bpy.types.Panel):
    bl_label = "Stray Sketch Strokes"
    bl_idname = "ANIME_PT_outline_stray"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab not in {'ALL', 'OUTLINE'}:
            return False
        mesh, _ = _get_mesh_and_node(context)
        return mesh is not None and mesh.modifiers.get(OUTLINE_MOD_NAME) is not None

    def draw_header(self, context):
        mesh = _resolve_target_mesh(self, context)
        if mesh:
            self.layout.prop(mesh, "anime_stray_enable", text="")
        else:
            self.layout.label(text="", icon='GREASEPENCIL')

    def draw(self, context):
        layout = self.layout
        mesh, _ = _get_mesh_and_node(context)
        if mesh:
            layout.active = mesh.anime_stray_enable
            col = layout.column(align=True)
            col.prop(mesh, "anime_stray_offset",  text="Offset", slider=True)
            col.prop(mesh, "anime_stray_density", text="Density", slider=True)
            col.prop(mesh, "anime_stray_opacity", text="Opacity", slider=True)
            col.prop(mesh, "anime_stray_jitter",  text="Jitter", slider=True)


classes = (
    ANIME_PT_main_panel,
    ANIME_PT_light_direction,
    ANIME_PT_light_colors,
    ANIME_PT_light_tuning,
    ANIME_PT_light_presets,
    ANIME_PT_outline_settings,
    ANIME_PT_outline_style,
    ANIME_PT_outline_stray,
)


def register():
    bpy.types.Scene.anime_active_tab = bpy.props.EnumProperty(
        name="Filter",
        items=[
            ('ALL', "All", "Show all anime shading and outline controls"),
            ('LIGHT', "Light", "Lighting direction, colors, and cel shading"),
            ('OUTLINE', "Outline", "Anime ink outlines and sketch stray strokes"),
        ],
        default='ALL',
        update=_update_tab,
    )

    for target in (bpy.types.Object, bpy.types.Scene):
        target.anime_outline_thickness = bpy.props.FloatProperty(
            name="Thickness",
            description="Outline line thickness (strictly positive)",
            min=0.001,
            max=0.1,
            soft_max=0.06,
            default=0.02,
            update=_update_thickness,
        )

        target.anime_outline_opacity = bpy.props.FloatProperty(
            name="Opacity",
            description="Outline line opacity (0 = transparent, 1 = solid ink)",
            min=0.0,
            max=1.0,
            default=1.0,
            subtype='FACTOR',
            update=_update_opacity,
        )

        target.anime_outline_chaos = bpy.props.FloatProperty(
            name="Hand Chaos",
            description="Organic hand-drawn jitter & stroke variation (0 = clean, 1 = heavy sketch)",
            min=0.0,
            max=1.0,
            default=0.25,
            subtype='FACTOR',
            update=_update_chaos,
        )

        target.anime_outline_style = bpy.props.EnumProperty(
            name="Style",
            description="Outline line pattern style",
            items=[
                ('SOLID', "Solid", "Continuous clean ink line"),
                ('INK', "Ink / Pen", "Dynamic hand-drawn pressure with natural breaks"),
                ('DASHED', "Dashed", "Stylized dashed stroke pattern"),
                ('SKETCH', "Sketch", "Textured pencil sketch"),
            ],
            default='SOLID',
            update=_update_style,
        )

        target.anime_outline_scale = bpy.props.FloatProperty(
            name="Stroke Density",
            description="Frequency / density of dashed strokes, ink variation or pencil grain",
            min=2.0,
            max=80.0,
            default=20.0,
            update=_update_scale,
        )

        target.anime_outline_color = bpy.props.FloatVectorProperty(
            name="Color",
            description="Outline ink color",
            subtype='COLOR',
            size=4,
            min=0.0,
            max=1.0,
            default=(0.0, 0.0, 0.0, 1.0),
            update=_update_color,
        )

        target.anime_stray_enable = bpy.props.BoolProperty(
            name="Stray Strokes",
            description="Enable hasty hand-drawn secondary stray strokes near the outline",
            default=True,
            update=_update_stray,
        )

        target.anime_stray_offset = bpy.props.FloatProperty(
            name="Offset",
            description="Distance between main outline and stray sketch strokes",
            min=0.002,
            max=0.06,
            default=0.012,
            update=_update_stray,
        )

        target.anime_stray_density = bpy.props.FloatProperty(
            name="Density",
            description="Frequency / amount of broken stray strokes along the silhouette",
            min=0.0,
            max=1.0,
            default=0.6,
            subtype='FACTOR',
            update=_update_stray,
        )

        target.anime_stray_opacity = bpy.props.FloatProperty(
            name="Opacity",
            description="Opacity of stray sketch strokes (pencil vs bold ink)",
            min=0.0,
            max=1.0,
            default=0.75,
            subtype='FACTOR',
            update=_update_stray,
        )

        target.anime_stray_jitter = bpy.props.FloatProperty(
            name="Jitter",
            description="Organic waviness and distortion of stray sketch strokes",
            min=0.0,
            max=1.0,
            default=0.5,
            subtype='FACTOR',
            update=_update_stray,
        )

    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            pass

    prop_names = [
        "anime_outline_thickness",
        "anime_outline_opacity",
        "anime_outline_chaos",
        "anime_outline_style",
        "anime_outline_scale",
        "anime_outline_color",
        "anime_stray_enable",
        "anime_stray_offset",
        "anime_stray_density",
        "anime_stray_opacity",
        "anime_stray_jitter",
    ]
    for target in (bpy.types.Object, bpy.types.Scene):
        for prop in prop_names:
            if hasattr(target, prop):
                delattr(target, prop)

    if hasattr(bpy.types.Scene, "anime_active_tab"):
        delattr(bpy.types.Scene, "anime_active_tab")
