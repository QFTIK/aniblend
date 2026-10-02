"""
MatCap-style Anime Cel-Shader Engine for Blender 5+.
Uses a sphere controller (Empty) for artistic light direction (no real lights needed).
Includes advanced Inverted Hull outline shader with Hand-Drawn Chaos, Opacity, and Styles.
"""

import bpy

NODE_GROUP_NAME = "Anime_Toon_Shader"
CTRL_PROP = "anime_light_ctrl"       # custom property linking mesh ↔ sphere controller
OUTLINE_MAT_NAME = "M_Anime_Outline"
OUTLINE_MOD_NAME = "Anime_Outline"
OUTLINE_STRAY_MAT_NAME = "M_Anime_Stray_Outline"
OUTLINE_STRAY_MOD_NAME = "Anime_Stray_Outline"


def _get_light_socket_name(idx, prop):
    """
    Returns consistent socket names for light at index (0-based).
    For index 0 (Light 1), keeps legacy socket names where possible.
    """
    i = idx + 1
    if i == 1:
        mapping = {
            'direction': 'Light Direction',
            'color': 'L1 Color',
            'shadow': 'L1 Shadow Color',
            'strength': 'L1 Strength',
            'position': 'Shadow Position',
            'softness': 'Shadow Softness',
            'specular': 'Specular Size',
            'enabled': 'L1 Enabled',
            'opacity': 'L1 Opacity',
            'cover': 'L1 Cover',
        }
        return mapping.get(prop, f"L1 {prop.capitalize()}")
    else:
        mapping = {
            'direction': f'L{i} Direction',
            'color': f'L{i} Color',
            'shadow': f'L{i} Shadow Color',
            'strength': f'L{i} Strength',
            'position': f'L{i} Shadow Position',
            'softness': f'L{i} Shadow Softness',
            'specular': f'L{i} Specular Size',
            'enabled': f'L{i} Enabled',
            'opacity': f'L{i} Opacity',
            'cover': f'L{i} Cover',
        }
        return mapping.get(prop, f"L{i} {prop.capitalize()}")


def _build_multilight_toon_nodegroup(ng, num_lights):
    """
    Internal: (re)builds the Anime_Toon_Shader node group interface and node network
    for exactly num_lights lights. Each light has its own Light Color and Shadow Color.
    The overall surface Base Color (Заливка) tints the accumulated lighting.
    """
    iface = ng.interface
    iface.clear()

    # 1. Global Base Color Socket (Заливка - surface fill of the object)
    iface.new_socket(name="Base Color", in_out='INPUT', socket_type='NodeSocketColor').default_value = (0.92, 0.78, 0.68, 1.0)
    # Legacy fallback socket
    iface.new_socket(name="Shadow Color", in_out='INPUT', socket_type='NodeSocketColor').default_value = (0.55, 0.42, 0.52, 1.0)

    # 2. Per-Light Sockets (each light has Light Color + its own Shadow Color)
    for idx in range(num_lights):
        dir_name = _get_light_socket_name(idx, 'direction')
        col_name = _get_light_socket_name(idx, 'color')
        shd_name = _get_light_socket_name(idx, 'shadow')
        str_name = _get_light_socket_name(idx, 'strength')
        pos_name = _get_light_socket_name(idx, 'position')
        sft_name = _get_light_socket_name(idx, 'softness')
        spc_name = _get_light_socket_name(idx, 'specular')
        en_name = _get_light_socket_name(idx, 'enabled')
        opc_name = _get_light_socket_name(idx, 'opacity')
        cov_name = _get_light_socket_name(idx, 'cover')

        iface.new_socket(name=dir_name, in_out='INPUT', socket_type='NodeSocketVector').default_value = (0.0, 0.0, 1.0)
        iface.new_socket(name=col_name, in_out='INPUT', socket_type='NodeSocketColor').default_value = (1.0, 1.0, 1.0, 1.0)
        s_shd = iface.new_socket(name=shd_name, in_out='INPUT', socket_type='NodeSocketColor')
        s_shd.default_value = (0.65, 0.58, 0.68, 1.0) if idx == 0 else (0.45, 0.48, 0.58, 1.0)

        s_str = iface.new_socket(name=str_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_str.default_value = 1.0
        s_str.min_value = 0.0
        s_str.max_value = 5.0

        s_pos = iface.new_socket(name=pos_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_pos.default_value = 0.4
        s_pos.min_value = -1.0
        s_pos.max_value = 1.0

        s_sft = iface.new_socket(name=sft_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_sft.default_value = 0.08
        s_sft.min_value = 0.001
        s_sft.max_value = 1.0

        s_spc = iface.new_socket(name=spc_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_spc.default_value = 0.10
        s_spc.min_value = 0.0
        s_spc.max_value = 0.8

        s_en = iface.new_socket(name=en_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_en.default_value = 1.0
        s_en.min_value = 0.0
        s_en.max_value = 1.0

        s_opc = iface.new_socket(name=opc_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_opc.default_value = 1.0
        s_opc.min_value = 0.0
        s_opc.max_value = 1.0

        s_cov = iface.new_socket(name=cov_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_cov.default_value = 1.0 if idx > 0 else 0.0
        s_cov.min_value = 0.0
        s_cov.max_value = 1.0

    iface.new_socket(name="Shader", in_out='OUTPUT', socket_type='NodeSocketShader')

    # Build Internal Node Network
    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    node_in = nodes.new('NodeGroupInput')
    node_in.location = (-1300, 0)
    node_out = nodes.new('NodeGroupOutput')
    node_out.location = (2200, 0)

    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-1300, 400)

    reflect = nodes.new('ShaderNodeVectorMath')
    reflect.operation = 'REFLECT'
    reflect.location = (-1100, -400)
    links.new(geom.outputs['Incoming'], reflect.inputs[0])
    links.new(geom.outputs['Normal'], reflect.inputs[1])

    cel_factors = []
    tone_colors = []
    spec_colors = []

    for idx in range(num_lights):
        y_off = 400 - idx * 600

        dir_name = _get_light_socket_name(idx, 'direction')
        col_name = _get_light_socket_name(idx, 'color')
        shd_name = _get_light_socket_name(idx, 'shadow')
        str_name = _get_light_socket_name(idx, 'strength')
        pos_name = _get_light_socket_name(idx, 'position')
        sft_name = _get_light_socket_name(idx, 'softness')
        spc_name = _get_light_socket_name(idx, 'specular')
        en_name = _get_light_socket_name(idx, 'enabled')

        norm_l = nodes.new('ShaderNodeVectorMath')
        norm_l.operation = 'NORMALIZE'
        norm_l.location = (-1050, y_off)
        links.new(node_in.outputs[dir_name], norm_l.inputs[0])

        dot_l = nodes.new('ShaderNodeVectorMath')
        dot_l.operation = 'DOT_PRODUCT'
        dot_l.location = (-850, y_off)
        links.new(geom.outputs['Normal'], dot_l.inputs[0])
        links.new(norm_l.outputs['Vector'], dot_l.inputs[1])

        sub = nodes.new('ShaderNodeMath')
        sub.operation = 'SUBTRACT'
        sub.location = (-850, y_off - 150)
        links.new(node_in.outputs[pos_name], sub.inputs[0])
        links.new(node_in.outputs[sft_name], sub.inputs[1])

        add = nodes.new('ShaderNodeMath')
        add.operation = 'ADD'
        add.location = (-850, y_off - 300)
        links.new(node_in.outputs[pos_name], add.inputs[0])
        links.new(node_in.outputs[sft_name], add.inputs[1])

        map_c = nodes.new('ShaderNodeMapRange')
        map_c.interpolation_type = 'SMOOTHSTEP'
        map_c.clamp = True
        map_c.location = (-650, y_off)
        links.new(dot_l.outputs['Value'], map_c.inputs['Value'])
        links.new(sub.outputs['Value'], map_c.inputs['From Min'])
        links.new(add.outputs['Value'], map_c.inputs['From Max'])

        c_en = nodes.new('ShaderNodeMath')
        c_en.operation = 'MULTIPLY'
        c_en.location = (-450, y_off)
        links.new(map_c.outputs['Result'], c_en.inputs[0])
        links.new(node_in.outputs[en_name], c_en.inputs[1])
        cel_factors.append(c_en.outputs['Value'])

        # Scaled lit color: Light Color * Strength
        scale_lit = nodes.new('ShaderNodeVectorMath')
        scale_lit.operation = 'SCALE'
        scale_lit.location = (-250, y_off - 150)
        links.new(node_in.outputs[col_name], scale_lit.inputs[0])
        links.new(node_in.outputs[str_name], scale_lit.inputs[3])

        # Per-light two-tone: mix(Shadow Color, Lit Color, cel_factor)
        mix_tone = nodes.new('ShaderNodeMix')
        mix_tone.data_type = 'RGBA'
        mix_tone.blend_type = 'MIX'
        mix_tone.location = (-50, y_off)
        links.new(c_en.outputs['Value'], mix_tone.inputs[0])
        links.new(node_in.outputs[shd_name], mix_tone.inputs[6])
        links.new(scale_lit.outputs['Vector'], mix_tone.inputs[7])
        tone_colors.append(mix_tone.outputs[2])

        # Specular Highlight
        dot_s = nodes.new('ShaderNodeVectorMath')
        dot_s.operation = 'DOT_PRODUCT'
        dot_s.location = (-850, y_off - 450)
        links.new(reflect.outputs['Vector'], dot_s.inputs[0])
        links.new(norm_l.outputs['Vector'], dot_s.inputs[1])

        thresh = nodes.new('ShaderNodeMath')
        thresh.operation = 'SUBTRACT'
        thresh.inputs[0].default_value = 1.0
        thresh.location = (-650, y_off - 450)
        links.new(node_in.outputs[spc_name], thresh.inputs[1])

        is_spec = nodes.new('ShaderNodeMath')
        is_spec.operation = 'GREATER_THAN'
        is_spec.location = (-450, y_off - 450)
        links.new(dot_s.outputs['Value'], is_spec.inputs[0])
        links.new(thresh.outputs['Value'], is_spec.inputs[1])

        s_mask = nodes.new('ShaderNodeMath')
        s_mask.operation = 'MULTIPLY'
        s_mask.location = (-250, y_off - 450)
        links.new(is_spec.outputs['Value'], s_mask.inputs[0])
        links.new(c_en.outputs['Value'], s_mask.inputs[1])

        s_str = nodes.new('ShaderNodeMath')
        s_str.operation = 'MULTIPLY'
        s_str.location = (-50, y_off - 450)
        links.new(s_mask.outputs['Value'], s_str.inputs[0])
        links.new(node_in.outputs[str_name], s_str.inputs[1])

        mix_s = nodes.new('ShaderNodeMix')
        mix_s.data_type = 'RGBA'
        mix_s.inputs[6].default_value = (0, 0, 0, 0)
        mix_s.location = (150, y_off - 450)
        links.new(s_str.outputs['Value'], mix_s.inputs[0])
        links.new(node_in.outputs[col_name], mix_s.inputs[7])
        spec_colors.append(mix_s.outputs[2])

    # Accumulate tone colors across light layers (Cover vs Add, modulated by Opacity)
    curr_tone = tone_colors[0]
    curr_spec = spec_colors[0]

    for k in range(1, num_lights):
        x_base = 200 + (k - 1) * 380
        opc_name = _get_light_socket_name(k, 'opacity')
        cov_name = _get_light_socket_name(k, 'cover')

        # Effective mask where light k illuminates = cel_factors[k] * opacity
        eff_mask = nodes.new('ShaderNodeMath')
        eff_mask.operation = 'MULTIPLY'
        eff_mask.location = (x_base, 200)
        links.new(cel_factors[k], eff_mask.inputs[0])
        links.new(node_in.outputs[opc_name], eff_mask.inputs[1])

        # ── 1. COVER MODE: where light k shines, it covers underlying tone ──
        cov_step = nodes.new('ShaderNodeMix')
        cov_step.data_type = 'RGBA'
        cov_step.blend_type = 'MIX'
        cov_step.location = (x_base + 130, 200)
        links.new(eff_mask.outputs['Value'], cov_step.inputs[0])
        links.new(curr_tone, cov_step.inputs[6])
        links.new(tone_colors[k], cov_step.inputs[7])

        # ── 2. ADD MODE: light k adds illumination on top of underlying tone ──
        add_step = nodes.new('ShaderNodeMix')
        add_step.data_type = 'RGBA'
        add_step.blend_type = 'ADD'
        add_step.location = (x_base + 130, 0)
        links.new(eff_mask.outputs['Value'], add_step.inputs[0])
        links.new(curr_tone, add_step.inputs[6])
        links.new(tone_colors[k], add_step.inputs[7])

        # ── 3. BLEND: mix between Add and Cover based on layer cover setting ──
        blend_tone = nodes.new('ShaderNodeMix')
        blend_tone.data_type = 'RGBA'
        blend_tone.blend_type = 'MIX'
        blend_tone.location = (x_base + 260, 100)
        links.new(node_in.outputs[cov_name], blend_tone.inputs[0])
        links.new(add_step.outputs[2], blend_tone.inputs[6])
        links.new(cov_step.outputs[2], blend_tone.inputs[7])
        curr_tone = blend_tone.outputs[2]

        # ── 4. SPECULAR ACCUMULATION ──
        scaled_spec = nodes.new('ShaderNodeMix')
        scaled_spec.data_type = 'RGBA'
        scaled_spec.blend_type = 'MIX'
        scaled_spec.inputs[6].default_value = (0, 0, 0, 0)
        scaled_spec.location = (x_base, -240)
        links.new(node_in.outputs[opc_name], scaled_spec.inputs[0])
        links.new(spec_colors[k], scaled_spec.inputs[7])

        add_sp = nodes.new('ShaderNodeMix')
        add_sp.data_type = 'RGBA'
        add_sp.blend_type = 'ADD'
        add_sp.inputs[0].default_value = 1.0
        add_sp.location = (x_base + 130, -240)
        links.new(curr_spec, add_sp.inputs[6])
        links.new(scaled_spec.outputs[2], add_sp.inputs[7])
        curr_spec = add_sp.outputs[2]

    # Final Surface: Multiply accumulated lighting tone with Base Color (Заливка)
    base_mult = nodes.new('ShaderNodeMix')
    base_mult.data_type = 'RGBA'
    base_mult.blend_type = 'MULTIPLY'
    base_mult.inputs[0].default_value = 1.0
    base_mult.location = (250 + num_lights * 380, 0)
    links.new(node_in.outputs['Base Color'], base_mult.inputs[6])
    links.new(curr_tone, base_mult.inputs[7])

    # Add Specular highlights
    final_color = nodes.new('ShaderNodeMix')
    final_color.data_type = 'RGBA'
    final_color.blend_type = 'ADD'
    final_color.inputs[0].default_value = 1.0
    final_color.location = (450 + num_lights * 380, 0)
    links.new(base_mult.outputs[2], final_color.inputs[6])
    links.new(curr_spec, final_color.inputs[7])

    emit = nodes.new('ShaderNodeEmission')
    emit.inputs['Strength'].default_value = 1.0
    emit.location = (650 + num_lights * 380, 0)
    links.new(final_color.outputs[2], emit.inputs['Color'])
    links.new(emit.outputs['Emission'], node_out.inputs['Shader'])

    # Stamp the node group with its light count and schema version (v3 = per-light shadow)
    ng["_anime_num_lights"] = num_lights
    ng["_anime_schema_ver"] = 3


def _count_ng_lights(ng):
    """Returns the light count a node group was built for, or 0 if unknown."""
    if ng and "_anime_num_lights" in ng:
        return ng["_anime_num_lights"]
    return 0


def get_or_create_multilight_toon_nodegroup(num_lights=1):
    """
    Returns the Anime_Toon_Shader node group for N lights.
    Only rebuilds the node network if the group doesn't exist yet or
    was built for a different number of lights or an older schema version.
    """
    num_lights = max(1, int(num_lights))
    name = NODE_GROUP_NAME if num_lights == 1 else f"{NODE_GROUP_NAME}_{num_lights}L"
    ng = bpy.data.node_groups.get(name)

    needs_build = False
    if not ng or ng.bl_idname != "ShaderNodeTree":
        ng = bpy.data.node_groups.new(name=name, type="ShaderNodeTree")
        needs_build = True
    elif _count_ng_lights(ng) != num_lights or ng.get("_anime_schema_ver", 0) != 3:
        needs_build = True

    if needs_build:
        _build_multilight_toon_nodegroup(ng, num_lights)

    return ng


def setup_single_light_drivers(normal_node, ctrl_empty):
    """
    Wire 3 drivers on normal_node so it tracks ctrl_empty's world-space Z-axis (matrix_world column 2).
    """
    if not normal_node or not ctrl_empty:
        return
    normal_out = normal_node.outputs['Normal']
    for i in range(3):
        try:
            normal_out.driver_remove('default_value', i)
        except Exception:
            pass
    for axis_idx in range(3):
        fcurve = normal_out.driver_add('default_value', axis_idx)
        drv = fcurve.driver
        drv.type = 'SCRIPTED'
        var = drv.variables.new()
        var.name = 'v'
        var.type = 'SINGLE_PROP'
        tgt = var.targets[0]
        tgt.id_type = 'OBJECT'
        tgt.id = ctrl_empty
        tgt.data_path = f'matrix_world[2][{axis_idx}]'
        drv.expression = 'v'




def sync_material_lights(mesh_obj):
    """
    Synchronizes all anime materials on mesh_obj with its collection of anime_lights.
    Updates the nodegroup size, Normal nodes, drivers, and property values.
    Preserves user-set Base Color and Shadow Color across node group swaps.
    """
    if not mesh_obj or not hasattr(mesh_obj, "anime_lights") or not mesh_obj.data:
        return

    num_lights = max(1, len(mesh_obj.anime_lights))
    ng = get_or_create_multilight_toon_nodegroup(num_lights)

    for mat in mesh_obj.data.materials:
        if not mat or not mat.node_tree:
            continue
        name_low = mat.name.lower()
        if "outline" in name_low or "stray" in name_low or "gizmo" in name_low or "pointer" in name_low:
            continue

        toon_node = find_anime_toon_node(mat)
        if not toon_node:
            toon_node = mat.node_tree.nodes.new('ShaderNodeGroup')
            toon_node.location = (0, 0)

        # Save user-set Base/Shadow colors BEFORE swapping node_tree
        saved_base = None
        saved_shadow = None
        if toon_node.node_tree and toon_node.inputs:
            if 'Base Color' in toon_node.inputs:
                saved_base = tuple(toon_node.inputs['Base Color'].default_value)
            if 'Shadow Color' in toon_node.inputs:
                saved_shadow = tuple(toon_node.inputs['Shadow Color'].default_value)

        # Only reassign node_tree if it actually changed (avoids resetting socket values)
        if toon_node.node_tree is not ng:
            toon_node.node_tree = ng

        # Restore saved Base Color (socket gets reset to interface defaults on tree swap)
        if saved_base is not None and 'Base Color' in toon_node.inputs:
            toon_node.inputs['Base Color'].default_value = saved_base
        elif 'Base Color' in toon_node.inputs:
            bc = toon_node.inputs['Base Color'].default_value
            if bc[0] == 0.0 and bc[1] == 0.0 and bc[2] == 0.0:
                toon_node.inputs['Base Color'].default_value = (0.92, 0.78, 0.68, 1.0)

        # Wire Output Surface
        out_node = None
        for n in mat.node_tree.nodes:
            if n.type == 'OUTPUT_MATERIAL':
                out_node = n
                break
        if not out_node:
            out_node = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
            out_node.location = (450 + num_lights * 160, 0)
        mat.node_tree.links.new(toon_node.outputs['Shader'], out_node.inputs['Surface'])

        # Process each light
        for idx in range(num_lights):
            i = idx + 1
            light_item = mesh_obj.anime_lights[idx] if idx < len(mesh_obj.anime_lights) else None

            node_name = "LightDirection" if i == 1 else f"LightDirection_{i}"
            normal_node = mat.node_tree.nodes.get(node_name)
            if not normal_node:
                normal_node = mat.node_tree.nodes.new('ShaderNodeNormal')
                normal_node.name = node_name
                normal_node.label = f"Light {i} Direction"
                normal_node.location = (-260, -50 - (i - 1) * 180)

            dir_socket_name = _get_light_socket_name(idx, 'direction')
            if dir_socket_name in toon_node.inputs:
                mat.node_tree.links.new(normal_node.outputs['Normal'], toon_node.inputs[dir_socket_name])

            if light_item and light_item.ctrl_obj:
                ctrl = light_item.ctrl_obj
                if ctrl.name in bpy.data.objects and ctrl.parent != mesh_obj:
                    ctrl.parent = mesh_obj
                    ctrl.matrix_parent_inverse = mesh_obj.matrix_world.inverted()
                setup_single_light_drivers(normal_node, ctrl)

            if light_item:
                col_socket = _get_light_socket_name(idx, 'color')
                shd_socket = _get_light_socket_name(idx, 'shadow')
                str_socket = _get_light_socket_name(idx, 'strength')
                pos_socket = _get_light_socket_name(idx, 'position')
                sft_socket = _get_light_socket_name(idx, 'softness')
                spc_socket = _get_light_socket_name(idx, 'specular')
                en_socket = _get_light_socket_name(idx, 'enabled')
                opc_socket = _get_light_socket_name(idx, 'opacity')
                cov_socket = _get_light_socket_name(idx, 'cover')

                if col_socket in toon_node.inputs:
                    toon_node.inputs[col_socket].default_value = light_item.light_color
                if shd_socket in toon_node.inputs and hasattr(light_item, "shadow_color"):
                    toon_node.inputs[shd_socket].default_value = light_item.shadow_color
                if str_socket in toon_node.inputs:
                    toon_node.inputs[str_socket].default_value = light_item.strength
                if pos_socket in toon_node.inputs:
                    toon_node.inputs[pos_socket].default_value = light_item.shadow_position
                if sft_socket in toon_node.inputs:
                    toon_node.inputs[sft_socket].default_value = light_item.shadow_softness
                if spc_socket in toon_node.inputs:
                    toon_node.inputs[spc_socket].default_value = light_item.specular_size
                if en_socket in toon_node.inputs:
                    toon_node.inputs[en_socket].default_value = 1.0 if light_item.enabled else 0.0
                if opc_socket in toon_node.inputs and hasattr(light_item, "opacity"):
                    toon_node.inputs[opc_socket].default_value = light_item.opacity
                if cov_socket in toon_node.inputs and hasattr(light_item, "blend_mode"):
                    toon_node.inputs[cov_socket].default_value = 1.0 if light_item.blend_mode == 'COVER' else 0.0
            else:
                # No light source item (0 lights active, unlit flat shading)
                en_socket = _get_light_socket_name(idx, 'enabled')
                str_socket = _get_light_socket_name(idx, 'strength')
                if en_socket in toon_node.inputs:
                    toon_node.inputs[en_socket].default_value = 0.0
                if str_socket in toon_node.inputs:
                    toon_node.inputs[str_socket].default_value = 0.0

        # Clean up obsolete LightDirection nodes if lights count decreased
        for n in list(mat.node_tree.nodes):
            if n.name.startswith("LightDirection_"):
                try:
                    num = int(n.name.split("_")[1])
                    if num > num_lights:
                        mat.node_tree.nodes.remove(n)
                except Exception:
                    pass


def create_anime_material(name="M_Anime_Toon", num_lights=1):
    """
    Creates an anime material with the multi-light Anime_Toon_Shader node group.
    """
    mat = bpy.data.materials.new(name=name)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out_node = nodes.new('ShaderNodeOutputMaterial')
    out_node.location = (400, 0)

    group_node = nodes.new('ShaderNodeGroup')
    group_node.node_tree = get_or_create_multilight_toon_nodegroup(num_lights)
    group_node.location = (0, 0)

    if 'Base Color' in group_node.inputs:
        group_node.inputs['Base Color'].default_value = (0.92, 0.78, 0.68, 1.0)
    if 'Shadow Color' in group_node.inputs:
        group_node.inputs['Shadow Color'].default_value = (0.55, 0.42, 0.52, 1.0)

    # Local LightDirection Normal node for Light 1
    light_node = nodes.new('ShaderNodeNormal')
    light_node.name = "LightDirection"
    light_node.label = "Light 1 Direction"
    light_node.location = (-260, -50)
    light_node.outputs['Normal'].default_value = (0.0, 0.0, 1.0)

    dir_socket = _get_light_socket_name(0, 'direction')
    if dir_socket in group_node.inputs:
        links.new(light_node.outputs['Normal'], group_node.inputs[dir_socket])

    links.new(group_node.outputs['Shader'], out_node.inputs['Surface'])
    return mat


def find_anime_toon_node(mat):
    """Finds the Anime_Toon_Shader group node inside a material."""
    if not mat or not mat.node_tree:
        return None
    for n in mat.node_tree.nodes:
        if n.type == 'GROUP' and n.node_tree and n.node_tree.name.startswith(NODE_GROUP_NAME):
            return n
    return None


def heal_anime_materials(ng=None):
    """
    Scans all materials in the file. Any anime material that lost its node tree
    or is missing the per-material LightDirection node is automatically repaired.
    Restores full color, shader connections, drivers, and controller parenting.
    """
    for obj in bpy.data.objects:
        if obj.name.endswith("_Pointer") and hasattr(obj, "visible_camera"):
            obj.visible_camera = True
        if obj.type in {'MESH', 'CURVE', 'FONT', 'SURFACE'} and hasattr(obj, "anime_lights") and obj.anime_lights:
            sync_material_lights(obj)


# ─────────────────────────────────────────────────────────────────────────────
# ADVANCED INVERTED HULL OUTLINE MATERIAL (HAND-DRAWN CHAOS & STYLES)
# ─────────────────────────────────────────────────────────────────────────────

def get_or_create_outline_material(mesh=None):
    """
    Creates or returns the advanced anime outline material.
    If mesh is provided, returns/creates a per-mesh outline material so changes
    do not affect other objects.
    """
    mat_name = f"M_Anime_Outline_{mesh.name}" if mesh else OUTLINE_MAT_NAME
    mat = bpy.data.materials.get(mat_name)
    if mat and mat.node_tree:
        return mat

    mat = bpy.data.materials.new(name=mat_name)
    mat.use_backface_culling = True
    if hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'DITHERED'
    if hasattr(mat, 'blend_method'):
        mat.blend_method = 'HASHED'

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # 1. Texture Coordinates for procedural strokes
    texcoord = nodes.new('ShaderNodeTexCoord')
    texcoord.location = (-1100, 0)

    # 2. Chaos Noise for hand-drawn jitter & varied line weight
    noise_chaos = nodes.new('ShaderNodeTexNoise')
    noise_chaos.name = "ChaosNoise"
    noise_chaos.inputs['Scale'].default_value = 16.0
    noise_chaos.inputs['Detail'].default_value = 6.0
    noise_chaos.inputs['Roughness'].default_value = 0.75
    noise_chaos.inputs['Distortion'].default_value = 2.0
    noise_chaos.location = (-900, -300)
    links.new(texcoord.outputs['Object'], noise_chaos.inputs['Vector'])

    # Chaos Strength value node (0.0 = clean, 1.0 = heavy organic hand tremor)
    chaos_val = nodes.new('ShaderNodeValue')
    chaos_val.name = "OutlineChaos"
    chaos_val.outputs[0].default_value = 0.3
    chaos_val.location = (-900, -500)

    # Vector Jitter: add noise vector to Object vector for wavy hand-drawn lines
    jitter_scale = nodes.new('ShaderNodeVectorMath')
    jitter_scale.operation = 'SCALE'
    jitter_scale.location = (-700, -300)
    links.new(noise_chaos.outputs['Color'], jitter_scale.inputs[0])
    links.new(chaos_val.outputs[0], jitter_scale.inputs['Scale'])

    jittered_vec = nodes.new('ShaderNodeVectorMath')
    jittered_vec.operation = 'ADD'
    jittered_vec.location = (-500, -100)
    links.new(texcoord.outputs['Object'], jittered_vec.inputs[0])
    links.new(jitter_scale.outputs['Vector'], jittered_vec.inputs[1])

    # 3. Wave pattern for DASHED strokes (uses jittered vector)
    wave = nodes.new('ShaderNodeTexWave')
    wave.name = "OutlineWave"
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'DIAGONAL'
    wave.inputs['Scale'].default_value = 20.0
    wave.inputs['Distortion'].default_value = 1.5
    wave.location = (-280, 200)
    links.new(jittered_vec.outputs['Vector'], wave.inputs['Vector'])

    step_dash = nodes.new('ShaderNodeMath')
    step_dash.operation = 'GREATER_THAN'
    step_dash.inputs[1].default_value = 0.5
    step_dash.location = (-100, 200)
    links.new(wave.outputs['Color'], step_dash.inputs[0])

    # 4. Noise pattern for SKETCH / PENCIL strokes
    noise_sketch = nodes.new('ShaderNodeTexNoise')
    noise_sketch.name = "OutlineNoise"
    noise_sketch.inputs['Scale'].default_value = 40.0
    noise_sketch.inputs['Detail'].default_value = 4.0
    noise_sketch.location = (-280, 0)
    links.new(jittered_vec.outputs['Vector'], noise_sketch.inputs['Vector'])

    step_sketch = nodes.new('ShaderNodeMath')
    step_sketch.operation = 'GREATER_THAN'
    step_sketch.inputs[1].default_value = 0.45
    step_sketch.location = (-100, 0)
    links.new(noise_sketch.outputs['Fac'], step_sketch.inputs[0])

    # 5. Hand-Inked G-Pen style: varied line pressure with natural organic breaks
    map_ink = nodes.new('ShaderNodeMapRange')
    map_ink.name = "MapHandInk"
    map_ink.interpolation_type = 'SMOOTHSTEP'
    map_ink.clamp = True
    map_ink.inputs['From Min'].default_value = 0.25
    map_ink.inputs['From Max'].default_value = 0.70
    map_ink.location = (-100, -300)
    links.new(noise_chaos.outputs['Fac'], map_ink.inputs['Value'])

    # 6. Style selectors (Mix nodes)
    # Mix 1: Solid (1.0) vs Dashed
    mix1 = nodes.new('ShaderNodeMix')
    mix1.name = "StyleMix1"
    mix1.data_type = 'FLOAT'
    mix1.inputs[0].default_value = 0.0  # Default: Solid
    mix1.inputs[2].default_value = 1.0  # A = Solid (always visible)
    mix1.location = (100, 150)
    links.new(step_dash.outputs['Value'], mix1.inputs[3])

    # Mix 2: Mix1 vs Sketch
    mix2 = nodes.new('ShaderNodeMix')
    mix2.name = "StyleMix2"
    mix2.data_type = 'FLOAT'
    mix2.inputs[0].default_value = 0.0
    mix2.location = (280, 100)
    links.new(mix1.outputs[0], mix2.inputs[2])
    links.new(step_sketch.outputs['Value'], mix2.inputs[3])

    # Mix 3: Mix2 vs Hand-Inked G-Pen
    mix3 = nodes.new('ShaderNodeMix')
    mix3.name = "StyleMix3"
    mix3.data_type = 'FLOAT'
    mix3.inputs[0].default_value = 0.0
    mix3.location = (460, 50)
    links.new(mix2.outputs[0], mix3.inputs[2])
    links.new(map_ink.outputs['Result'], mix3.inputs[3])

    # 7. Apply Hand-Drawn Chaos Modulation (line breaks & pressure)
    chaos_mod = nodes.new('ShaderNodeMath')
    chaos_mod.operation = 'MULTIPLY'
    chaos_mod.location = (460, -200)
    links.new(noise_chaos.outputs['Fac'], chaos_mod.inputs[0])
    links.new(chaos_val.outputs[0], chaos_mod.inputs[1])

    chaos_atten = nodes.new('ShaderNodeMath')
    chaos_atten.operation = 'MULTIPLY'
    chaos_atten.inputs[1].default_value = 0.40
    chaos_atten.location = (640, -200)
    links.new(chaos_mod.outputs['Value'], chaos_atten.inputs[0])

    chaos_sub = nodes.new('ShaderNodeMath')
    chaos_sub.operation = 'SUBTRACT'
    chaos_sub.location = (640, 50)
    links.new(mix3.outputs[0], chaos_sub.inputs[0])
    links.new(chaos_atten.outputs['Value'], chaos_sub.inputs[1])

    clamp_chaos = nodes.new('ShaderNodeMath')
    clamp_chaos.operation = 'MAXIMUM'
    clamp_chaos.inputs[1].default_value = 0.0
    clamp_chaos.location = (820, 50)
    links.new(chaos_sub.outputs['Value'], clamp_chaos.inputs[0])

    # 8. Opacity node (0.0 = fully transparent, 1.0 = solid)
    opac_val = nodes.new('ShaderNodeValue')
    opac_val.name = "OutlineOpacity"
    opac_val.outputs[0].default_value = 1.0
    opac_val.location = (820, -150)

    # Final Alpha = Pattern_Mask * Opacity
    final_alpha = nodes.new('ShaderNodeMath')
    final_alpha.name = "FinalAlpha"
    final_alpha.operation = 'MULTIPLY'
    final_alpha.location = (1000, 0)
    links.new(clamp_chaos.outputs['Value'], final_alpha.inputs[0])
    links.new(opac_val.outputs[0], final_alpha.inputs[1])

    # 9. Shaders: Transparent BSDF & Emission
    transp = nodes.new('ShaderNodeBsdfTransparent')
    transp.location = (1180, 200)

    emit = nodes.new('ShaderNodeEmission')
    emit.name = "OutlineEmission"
    emit.label = "Outline Color"
    emit.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)
    emit.inputs['Strength'].default_value = 1.0
    emit.location = (1180, -150)

    mix_s = nodes.new('ShaderNodeMixShader')
    mix_s.location = (1380, 100)
    links.new(final_alpha.outputs['Value'], mix_s.inputs['Fac'])
    links.new(transp.outputs['BSDF'], mix_s.inputs[1])
    links.new(emit.outputs['Emission'], mix_s.inputs[2])

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (1580, 100)
    links.new(mix_s.outputs['Shader'], out.inputs['Surface'])

    return mat


def set_outline_style(mat, style_key):
    """
    Switches outline pattern mode:
      'SOLID'  -> Continuous clean line
      'INK'    -> Hand-drawn organic ink with varied pen pressure
      'DASHED' -> Stylized dashed ink stroke
      'SKETCH' -> Textured pencil / hand-drawn sketch
    """
    if not mat or not mat.node_tree:
        return
    nodes = mat.node_tree.nodes
    mix1 = nodes.get("StyleMix1")
    mix2 = nodes.get("StyleMix2")
    mix3 = nodes.get("StyleMix3")
    if not mix1 or not mix2 or not mix3:
        return

    if style_key == 'SOLID':
        mix1.inputs[0].default_value = 0.0
        mix2.inputs[0].default_value = 0.0
        mix3.inputs[0].default_value = 0.0
    elif style_key == 'DASHED':
        mix1.inputs[0].default_value = 1.0
        mix2.inputs[0].default_value = 0.0
        mix3.inputs[0].default_value = 0.0
    elif style_key == 'SKETCH':
        mix1.inputs[0].default_value = 0.0
        mix2.inputs[0].default_value = 1.0
        mix3.inputs[0].default_value = 0.0
    elif style_key == 'INK':
        mix1.inputs[0].default_value = 0.0
        mix2.inputs[0].default_value = 0.0
        mix3.inputs[0].default_value = 1.0


def set_outline_chaos(mat, chaos):
    """Sets hand-drawn jitter & stroke chaos strength (0.0 to 1.0)."""
    if not mat or not mat.node_tree:
        return
    node = mat.node_tree.nodes.get("OutlineChaos")
    if node:
        node.outputs[0].default_value = max(0.0, min(1.0, chaos))


def set_outline_opacity(mat, opacity):
    """Sets outline opacity (0.0 to 1.0)."""
    if not mat or not mat.node_tree:
        return
    node = mat.node_tree.nodes.get("OutlineOpacity")
    if node:
        node.outputs[0].default_value = max(0.0, min(1.0, opacity))


def set_outline_scale(mat, scale):
    """Sets stroke density / frequency for Dashed and Sketch styles."""
    if not mat or not mat.node_tree:
        return
    nodes = mat.node_tree.nodes
    wave = nodes.get("OutlineWave")
    noise = nodes.get("OutlineNoise")
    chaos = nodes.get("ChaosNoise")
    if wave:
        wave.inputs['Scale'].default_value = max(1.0, scale)
    if noise:
        noise.inputs['Scale'].default_value = max(1.0, scale * 2.0)
    if chaos:
        chaos.inputs['Scale'].default_value = max(1.0, scale * 0.8)


def find_outline_emission_node(outline_mat):
    """Finds the OutlineEmission node to read or change the ink color."""
    if not outline_mat or not outline_mat.node_tree:
        return None
    return outline_mat.node_tree.nodes.get("OutlineEmission")


# ─────────────────────────────────────────────────────────────────────────────
# SECONDARY STRAY OUTLINE MATERIAL (HASTY HAND-DRAWN SKETCH / EXTRA STROKES)
# ─────────────────────────────────────────────────────────────────────────────

def get_or_create_stray_outline_material(mesh=None):
    """
    Creates or returns the secondary sketch stray strokes outline material.
    If mesh is provided, returns/creates a per-mesh stray material.
    """
    mat_name = f"M_Anime_Stray_{mesh.name}" if mesh else OUTLINE_STRAY_MAT_NAME
    mat = bpy.data.materials.get(mat_name)
    if mat and mat.node_tree:
        return mat

    mat = bpy.data.materials.new(name=mat_name)
    mat.use_backface_culling = True
    if hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'DITHERED'
    if hasattr(mat, 'blend_method'):
        mat.blend_method = 'HASHED'

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # 1. Tex Coord
    tex = nodes.new('ShaderNodeTexCoord')
    tex.location = (-1000, 0)

    # 2. Macro noise for stroke placement & breaks
    noise_macro = nodes.new('ShaderNodeTexNoise')
    noise_macro.name = "StrayMacroNoise"
    noise_macro.inputs['Scale'].default_value = 7.0
    noise_macro.inputs['Detail'].default_value = 5.0
    noise_macro.inputs['Distortion'].default_value = 4.0
    noise_macro.location = (-750, 150)
    links.new(tex.outputs['Object'], noise_macro.inputs['Vector'])

    # Stray Density / Frequency threshold node
    val_density = nodes.new('ShaderNodeValue')
    val_density.name = "StrayDensity"
    val_density.outputs[0].default_value = 0.58
    val_density.location = (-750, -100)

    # Threshold: Greater Than (determines stroke patches)
    step = nodes.new('ShaderNodeMath')
    step.operation = 'GREATER_THAN'
    step.location = (-500, 150)
    links.new(noise_macro.outputs['Fac'], step.inputs[0])
    links.new(val_density.outputs[0], step.inputs[1])

    # 3. Fine grain noise (gives sketchy pencil / textured ink look to the stray strokes)
    noise_grain = nodes.new('ShaderNodeTexNoise')
    noise_grain.name = "StrayGrainNoise"
    noise_grain.inputs['Scale'].default_value = 35.0
    noise_grain.inputs['Detail'].default_value = 3.0
    noise_grain.location = (-750, -250)
    links.new(tex.outputs['Object'], noise_grain.inputs['Vector'])

    step_grain = nodes.new('ShaderNodeMath')
    step_grain.operation = 'GREATER_THAN'
    step_grain.inputs[1].default_value = 0.30
    step_grain.location = (-500, -250)
    links.new(noise_grain.outputs['Fac'], step_grain.inputs[0])

    # Multiply macro mask with fine grain
    mix_stroke = nodes.new('ShaderNodeMath')
    mix_stroke.operation = 'MULTIPLY'
    mix_stroke.location = (-300, 50)
    links.new(step.outputs['Value'], mix_stroke.inputs[0])
    links.new(step_grain.outputs['Value'], mix_stroke.inputs[1])

    # 4. Stray Opacity
    val_opacity = nodes.new('ShaderNodeValue')
    val_opacity.name = "StrayOpacity"
    val_opacity.outputs[0].default_value = 0.75
    val_opacity.location = (-300, -150)

    final_alpha = nodes.new('ShaderNodeMath')
    final_alpha.name = "StrayFinalAlpha"
    final_alpha.operation = 'MULTIPLY'
    final_alpha.location = (-100, 0)
    links.new(mix_stroke.outputs['Value'], final_alpha.inputs[0])
    links.new(val_opacity.outputs[0], final_alpha.inputs[1])

    # 5. Shaders
    transp = nodes.new('ShaderNodeBsdfTransparent')
    transp.location = (100, 150)

    emit = nodes.new('ShaderNodeEmission')
    emit.name = "StrayEmission"
    emit.label = "Stray Stroke Color"
    emit.inputs['Color'].default_value = (0.05, 0.05, 0.05, 1.0)
    emit.inputs['Strength'].default_value = 1.0
    emit.location = (100, -150)

    mix_s = nodes.new('ShaderNodeMixShader')
    mix_s.location = (300, 0)
    links.new(final_alpha.outputs['Value'], mix_s.inputs['Fac'])
    links.new(transp.outputs['BSDF'], mix_s.inputs[1])
    links.new(emit.outputs['Emission'], mix_s.inputs[2])

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (650, 0)
    links.new(mix_s.outputs['Shader'], out.inputs['Surface'])

    return mat


def set_stray_density(mat, density):
    """Sets density/frequency of stray strokes (0.0 = rare, 1.0 = dense sketch lines)."""
    if not mat or not mat.node_tree:
        return
    node = mat.node_tree.nodes.get("StrayDensity")
    if node:
        # map 0.0..1.0 to threshold 0.82..0.38 (inverted because Greater Than)
        val = 0.82 - (max(0.0, min(1.0, density)) * 0.44)
        node.outputs[0].default_value = val


def set_stray_opacity(mat, opacity):
    """Sets opacity of the stray sketch strokes (0.0 to 1.0)."""
    if not mat or not mat.node_tree:
        return
    node = mat.node_tree.nodes.get("StrayOpacity")
    if node:
        node.outputs[0].default_value = max(0.0, min(1.0, opacity))


def set_stray_jitter(mat, jitter):
    """Sets organic waviness / distortion of stray strokes."""
    if not mat or not mat.node_tree:
        return
    noise = mat.node_tree.nodes.get("StrayMacroNoise")
    if noise:
        noise.inputs['Distortion'].default_value = max(0.0, jitter * 8.0)


def set_stray_color(mat, color):
    """Sets color of the stray sketch strokes."""
    if not mat or not mat.node_tree:
        return
    emit = mat.node_tree.nodes.get("StrayEmission")
    if emit:
        emit.inputs['Color'].default_value = color


