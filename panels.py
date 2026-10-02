"""
Tabbed UI Panel for AniBlend (Light & Outline tabs).
Clean, intuitive layout with logical grouping.
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
    if "anime_bound_mesh" in obj:
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
    per_mesh = bpy.data.materials.get(f"M_Anime_Outline_{mesh.name}")
    if per_mesh and per_mesh.node_tree:
        return per_mesh
    return bpy.data.materials.get(OUTLINE_MAT_NAME)


def _find_active_stray_mat(mesh):
    per_mesh = bpy.data.materials.get(f"M_Anime_Stray_Outline_{mesh.name}")
    if per_mesh and per_mesh.node_tree:
        return per_mesh
    return bpy.data.materials.get(OUTLINE_STRAY_MAT_NAME)


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────

def _update_thickness(self, context):
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        mod = mesh.modifiers.get(OUTLINE_MOD_NAME)
        if mod:
            mod.thickness = self.anime_outline_thickness
        stray_mod = mesh.modifiers.get(OUTLINE_STRAY_MOD_NAME)
        if stray_mod:
            stray_mod.thickness = max(0.002, self.anime_outline_thickness * 0.65)
            stray_mod.offset = self.anime_stray_offset / self.anime_outline_thickness if self.anime_outline_thickness > 0 else 1.0
        _tag_viewport_redraw(context)


def _update_opacity(self, context):
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        outline_mat = _find_active_outline_mat(mesh)
        if outline_mat:
            set_outline_opacity(outline_mat, self.anime_outline_opacity)
            outline_mat.update_tag()
        _tag_viewport_redraw(context)


def _update_chaos(self, context):
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        outline_mat = _find_active_outline_mat(mesh)
        if outline_mat:
            set_outline_chaos(outline_mat, self.anime_outline_chaos)
            outline_mat.update_tag()
        _tag_viewport_redraw(context)


def _update_style(self, context):
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        outline_mat = _find_active_outline_mat(mesh)
        if outline_mat:
            set_outline_style(outline_mat, self.anime_outline_style)
            set_outline_scale(outline_mat, self.anime_outline_scale)
            outline_mat.update_tag()
        _tag_viewport_redraw(context)


def _update_scale(self, context):
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        outline_mat = _find_active_outline_mat(mesh)
        if outline_mat:
            set_outline_scale(outline_mat, self.anime_outline_scale)
            outline_mat.update_tag()
        _tag_viewport_redraw(context)


def _update_color(self, context):
    mesh = _resolve_target_mesh(self, context)
    if mesh:
        val = self.anime_outline_color
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


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PANEL
# ─────────────────────────────────────────────────────────────────────────────

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

        # Tab selector
        row = layout.row(align=True)
        row.scale_y = 1.15
        row.prop(scene, "anime_active_tab", expand=True)

        if not mesh:
            layout.separator()
            box = layout.box()
            box.label(text="Select a 3D mesh to begin", icon='INFO')
            return

        active_tab = scene.anime_active_tab

        # Apply / status button
        if active_tab == 'LIGHT':
            if not node:
                op_row = layout.row(align=True)
                op_row.scale_y = 1.35
                op_row.operator("anime.apply_shader", text="Apply Anime Shader", icon='SHADING_RENDERED')
            else:
                row_st = layout.row(align=True)
                row_st.scale_y = 1.1
                row_st.operator("anime.apply_shader", text="Re-apply Shader", icon='FILE_REFRESH')

        elif active_tab == 'OUTLINE':
            mod = mesh.modifiers.get(OUTLINE_MOD_NAME)
            if not mod:
                op_row = layout.row(align=True)
                op_row.scale_y = 1.35
                op_row.operator("anime.add_outline", text="Add Outlines", icon='LINE_DATA')
            else:
                row_out = layout.row(align=True)
                row_out.scale_y = 1.1
                if mod.show_viewport:
                    row_out.operator("anime.toggle_outline", text="Outlines: ON", icon='HIDE_OFF')
                else:
                    row_out.operator("anime.toggle_outline", text="Outlines: OFF", icon='HIDE_ON')
                row_out.operator("anime.remove_outline", text="", icon='TRASH')


# ─────────────────────────────────────────────────────────────────────────────
# LIGHT TAB  —  Material Colors  (always visible at top of Light tab)
# ─────────────────────────────────────────────────────────────────────────────

class ANIME_PT_material_colors(bpy.types.Panel):
    bl_label = "Material Colors"
    bl_idname = "ANIME_PT_material_colors"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab != 'LIGHT':
            return False
        mesh, node = _get_mesh_and_node(context)
        return mesh is not None and node is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='COLOR')

    def draw(self, context):
        layout = self.layout
        mesh, node = _get_mesh_and_node(context)
        if not mesh or not node:
            return

        # Base & Shadow color — the most important setting, always visible
        col = layout.column(align=True)
        if 'Base Color' in node.inputs:
            col.prop(node.inputs['Base Color'], "default_value", text="Base Color")
        if 'Shadow Color' in node.inputs:
            col.prop(node.inputs['Shadow Color'], "default_value", text="Shadow Color")

        # Color presets row
        layout.separator(factor=0.5)
        layout.label(text="Quick Presets:", icon='PRESET')
        r1 = layout.row(align=True)
        op1 = r1.operator("anime.apply_preset", text="Classic")
        op1.preset = 'CLASSIC'
        op2 = r1.operator("anime.apply_preset", text="Ghibli")
        op2.preset = 'GHIBLI'
        op3 = r1.operator("anime.apply_preset", text="Sunset")
        op3.preset = 'SUNSET'
        op4 = r1.operator("anime.apply_preset", text="Cyber")
        op4.preset = 'CYBER'


# ─────────────────────────────────────────────────────────────────────────────
# LIGHT TAB  —  Light Sources  (list + active light settings)
# ─────────────────────────────────────────────────────────────────────────────

class ANIME_UL_lights_list(bpy.types.UIList):
    """Compact light list: color · name · [Cover/Add] · 👁 · ✕"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        light = item
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            # Color badge (reflects the selected light color)
            sub_col = row.row(align=True)
            sub_col.scale_x = 0.4
            sub_col.prop(light, "marker_color", text="")

            # Name
            row.prop(light, "name", text="", emboss=False)

            # Layer mode badge for upper layers
            if index > 0:
                row.label(text="Cover" if light.blend_mode == 'COVER' else "Add")

            # Hide/Show
            op_vis = row.operator(
                "anime.light_toggle_visibility",
                text="",
                icon='HIDE_OFF' if light.enabled else 'HIDE_ON',
                emboss=False,
            )
            op_vis.index = index

            # Delete (only if > 1 light)
            del_row = row.row(align=True)
            del_row.enabled = len(data.anime_lights) > 1
            op_del = del_row.operator("anime.light_remove", text="", icon='X', emboss=False)
            op_del.index = index


class ANIME_PT_light_sources(bpy.types.Panel):
    bl_label = "Light Sources"
    bl_idname = "ANIME_PT_light_sources"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab != 'LIGHT':
            return False
        mesh, node = _get_mesh_and_node(context)
        return mesh is not None and node is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='LIGHT')

    def draw(self, context):
        layout = self.layout
        mesh, _ = _get_mesh_and_node(context)
        if not mesh:
            return

        if not mesh.anime_lights:
            layout.label(text="Re-apply shader to initialize lights.", icon='INFO')
            return

        # ── Light list with +/- and ▲/▼ layer buttons ──
        row = layout.row()
        row.template_list(
            "ANIME_UL_lights_list", "",
            mesh, "anime_lights",
            mesh, "anime_active_light_index",
            rows=3,
        )

        col_side = row.column(align=True)
        col_side.operator("anime.light_add", text="", icon='ADD')
        del_col = col_side.column(align=True)
        del_col.enabled = len(mesh.anime_lights) > 1
        del_col.operator("anime.light_remove", text="", icon='REMOVE')

        col_side.separator(factor=0.5)
        up_btn = col_side.operator("anime.light_move", text="", icon='TRIA_UP')
        up_btn.direction = 'UP'
        dn_btn = col_side.operator("anime.light_move", text="", icon='TRIA_DOWN')
        dn_btn.direction = 'DOWN'

        # ── Active Light Settings ──
        idx = mesh.anime_active_light_index
        if not (0 <= idx < len(mesh.anime_lights)):
            return

        active_light = mesh.anime_lights[idx]
        ctrl = active_light.ctrl_obj

        layout.separator(factor=0.3)

        # Direction
        if ctrl and ctrl.name in bpy.data.objects:
            col_dir = layout.column(align=True)
            row_dir = col_dir.row(align=True)
            row_dir.label(text="Direction", icon='ORIENTATION_NORMAL')
            sel_op = row_dir.operator("anime.light_select", text="Select", icon='RESTRICT_SELECT_OFF')
            sel_op.index = idx
            col_dir.prop(ctrl, "rotation_euler", text="")

        # Color & Strength
        layout.separator(factor=0.3)
        col_beam = layout.column(align=True)
        col_beam.label(text="Light Color", icon='LIGHT_SUN')
        r_beam = col_beam.row(align=True)
        r_beam.prop(active_light, "light_color", text="")
        r_beam.prop(active_light, "strength", text="Power")

        # Layer & Blending (Cover vs Add, Opacity)
        layout.separator(factor=0.3)
        col_layer = layout.column(align=True)
        col_layer.label(text="Layer & Blending", icon='RENDERLAYERS')
        if idx > 0:
            row_mode = col_layer.row(align=True)
            row_mode.prop(active_light, "blend_mode", expand=True)
        col_layer.prop(active_light, "opacity", text="Layer Opacity", slider=True)

        # Shadow & Specular
        layout.separator(factor=0.3)
        col_sh = layout.column(align=True)
        col_sh.label(text="Shadow & Specular", icon='SHADING_RENDERED')
        col_sh.prop(active_light, "shadow_position", text="Shadow Position", slider=True)
        col_sh.prop(active_light, "shadow_softness", text="Shadow Softness", slider=True)
        col_sh.prop(active_light, "specular_size", text="Highlight Size", slider=True)


# ─────────────────────────────────────────────────────────────────────────────
# OUTLINE TAB  —  Line Appearance
# ─────────────────────────────────────────────────────────────────────────────

class ANIME_PT_outline_settings(bpy.types.Panel):
    bl_label = "Line Appearance"
    bl_idname = "ANIME_PT_outline_settings"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab != 'OUTLINE':
            return False
        mesh, _ = _get_mesh_and_node(context)
        return mesh is not None and mesh.modifiers.get(OUTLINE_MOD_NAME) is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='STROKE')

    def draw(self, context):
        layout = self.layout
        mesh, _ = _get_mesh_and_node(context)
        if not mesh:
            return

        col = layout.column(align=True)
        col.prop(mesh, "anime_outline_thickness", text="Thickness", slider=True)
        col.prop(mesh, "anime_outline_opacity",   text="Opacity", slider=True)
        col.prop(mesh, "anime_outline_color",     text="Color")


# ─────────────────────────────────────────────────────────────────────────────
# OUTLINE TAB  —  Stroke Style
# ─────────────────────────────────────────────────────────────────────────────

class ANIME_PT_outline_style(bpy.types.Panel):
    bl_label = "Stroke Style"
    bl_idname = "ANIME_PT_outline_style"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab != 'OUTLINE':
            return False
        mesh, _ = _get_mesh_and_node(context)
        return mesh is not None and mesh.modifiers.get(OUTLINE_MOD_NAME) is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='BRUSH_DATA')

    def draw(self, context):
        layout = self.layout
        mesh, _ = _get_mesh_and_node(context)
        if not mesh:
            return

        row = layout.row(align=True)
        row.prop(mesh, "anime_outline_style", expand=True)

        col = layout.column(align=True)
        col.prop(mesh, "anime_outline_chaos", text="Hand Tremor", slider=True)
        if mesh.anime_outline_style in {'DASHED', 'SKETCH', 'INK'}:
            col.prop(mesh, "anime_outline_scale", text="Stroke Density", slider=True)


# ─────────────────────────────────────────────────────────────────────────────
# OUTLINE TAB  —  Stray Strokes
# ─────────────────────────────────────────────────────────────────────────────

class ANIME_PT_outline_stray(bpy.types.Panel):
    bl_label = "Stray Strokes"
    bl_idname = "ANIME_PT_outline_stray"
    bl_parent_id = "ANIME_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AniBlend"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.scene.anime_active_tab != 'OUTLINE':
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


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRATION
# ─────────────────────────────────────────────────────────────────────────────

classes = (
    ANIME_UL_lights_list,
    ANIME_PT_main_panel,
    ANIME_PT_material_colors,
    ANIME_PT_light_sources,
    ANIME_PT_outline_settings,
    ANIME_PT_outline_style,
    ANIME_PT_outline_stray,
)


def register():
    bpy.types.Scene.anime_active_tab = bpy.props.EnumProperty(
        name="Tab",
        items=[
            ('LIGHT', "Shading", "Material colors, lights, and cel shading"),
            ('OUTLINE', "Outline", "Anime ink outlines and sketch strokes"),
        ],
        default='LIGHT',
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
