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


def get_or_create_toon_nodegroup():
    """
    Creates or updates the Anime_Toon_Shader node group using pure MatCap approach:
      Normal · LightDir = cel factor  (no scene lights needed)

    Accepts 'Light Direction' vector as an input socket so each material
    can have its own independent light controller without driver crosstalk.
    Never removes the group node tree so existing materials stay intact.
    """
    ng = bpy.data.node_groups.get(NODE_GROUP_NAME)
    if not ng or ng.bl_idname != "ShaderNodeTree":
        ng = bpy.data.node_groups.new(name=NODE_GROUP_NAME, type="ShaderNodeTree")

    iface = ng.interface

    # Clean up legacy manga sockets if present
    for item in list(iface.items_tree):
        if getattr(item, 'item_type', None) == 'SOCKET' and getattr(item, 'in_out', None) == 'INPUT':
            if item.name.startswith("Manga"):
                try:
                    iface.remove(item)
                except Exception:
                    pass

    # Ensure all required sockets exist on the interface
    existing_inputs = {
        item.name: item for item in iface.items_tree
        if getattr(item, 'item_type', None) == 'SOCKET' and getattr(item, 'in_out', None) == 'INPUT'
    }

    if "Base Color" not in existing_inputs:
        s = iface.new_socket(name="Base Color", in_out='INPUT', socket_type='NodeSocketColor')
        s.default_value = (0.92, 0.78, 0.68, 1.0)

    if "Shadow Color" not in existing_inputs:
        s = iface.new_socket(name="Shadow Color", in_out='INPUT', socket_type='NodeSocketColor')
        s.default_value = (0.55, 0.42, 0.52, 1.0)

    if "Shadow Position" not in existing_inputs:
        s = iface.new_socket(name="Shadow Position", in_out='INPUT', socket_type='NodeSocketFloat')
        s.default_value = 0.4
        s.min_value = -1.0
        s.max_value = 1.0

    if "Shadow Softness" not in existing_inputs:
        s = iface.new_socket(name="Shadow Softness", in_out='INPUT', socket_type='NodeSocketFloat')
        s.default_value = 0.08
        s.min_value = 0.001
        s.max_value = 1.0

    if "Specular Size" not in existing_inputs:
        s = iface.new_socket(name="Specular Size", in_out='INPUT', socket_type='NodeSocketFloat')
        s.default_value = 0.10
        s.min_value = 0.0
        s.max_value = 0.8

    if "Light Direction" not in existing_inputs:
        s = iface.new_socket(name="Light Direction", in_out='INPUT', socket_type='NodeSocketVector')
        s.default_value = (0.0, 0.0, 1.0)

    has_output = any(
        getattr(item, 'item_type', None) == 'SOCKET' and getattr(item, 'in_out', None) == 'OUTPUT'
        for item in iface.items_tree
    )
    if not has_output:
        iface.new_socket(name="Shader", in_out='OUTPUT', socket_type='NodeSocketShader')

    # --- Nodes ---
    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    node_in = nodes.new('NodeGroupInput')
    node_in.location = (-1100, 0)
    node_out = nodes.new('NodeGroupOutput')
    node_out.location = (1150, 0)

    # ─── 1. CEL SHADOW (Normal · LightDir) ──────────────────────────────
    geom = nodes.new('ShaderNodeNewGeometry')
    geom.location = (-900, 300)

    # Normalized Light Direction from material input socket
    norm_light = nodes.new('ShaderNodeVectorMath')
    norm_light.name = "NormLight"
    norm_light.operation = 'NORMALIZE'
    norm_light.location = (-900, 100)
    links.new(node_in.outputs['Light Direction'], norm_light.inputs[0])

    # Dot product: surface normal · light direction
    dot_light = nodes.new('ShaderNodeVectorMath')
    dot_light.operation = 'DOT_PRODUCT'
    dot_light.location = (-650, 200)
    links.new(geom.outputs['Normal'], dot_light.inputs[0])
    links.new(norm_light.outputs['Vector'], dot_light.inputs[1])

    # Shadow bounds [pos - soft .. pos + soft]
    sub = nodes.new('ShaderNodeMath')
    sub.operation = 'SUBTRACT'
    sub.location = (-650, -50)
    links.new(node_in.outputs['Shadow Position'], sub.inputs[0])
    links.new(node_in.outputs['Shadow Softness'], sub.inputs[1])

    add = nodes.new('ShaderNodeMath')
    add.operation = 'ADD'
    add.location = (-650, -200)
    links.new(node_in.outputs['Shadow Position'], add.inputs[0])
    links.new(node_in.outputs['Shadow Softness'], add.inputs[1])

    # Smoothstep cel transition
    map_cel = nodes.new('ShaderNodeMapRange')
    map_cel.interpolation_type = 'SMOOTHSTEP'
    map_cel.clamp = True
    map_cel.location = (-400, 200)
    links.new(dot_light.outputs['Value'], map_cel.inputs['Value'])
    links.new(sub.outputs['Value'], map_cel.inputs['From Min'])
    links.new(add.outputs['Value'], map_cel.inputs['From Max'])

    # Mix: Factor=0 → Shadow, Factor=1 → Base
    mix_cel = nodes.new('ShaderNodeMix')
    mix_cel.data_type = 'RGBA'
    mix_cel.clamp_factor = True
    mix_cel.location = (-150, 200)
    links.new(map_cel.outputs['Result'],       mix_cel.inputs[0])
    links.new(node_in.outputs['Shadow Color'], mix_cel.inputs[6])  # A=shadow
    links.new(node_in.outputs['Base Color'],   mix_cel.inputs[7])  # B=base

    # ─── 2. SPECULAR (Reflect · LightDir) ───────────────────────────────
    reflect = nodes.new('ShaderNodeVectorMath')
    reflect.operation = 'REFLECT'
    reflect.location = (-650, -400)
    links.new(geom.outputs['Incoming'], reflect.inputs[0])
    links.new(geom.outputs['Normal'], reflect.inputs[1])

    dot_spec = nodes.new('ShaderNodeVectorMath')
    dot_spec.operation = 'DOT_PRODUCT'
    dot_spec.location = (-400, -400)
    links.new(reflect.outputs['Vector'], dot_spec.inputs[0])
    links.new(norm_light.outputs['Vector'], dot_spec.inputs[1])

    spec_thresh = nodes.new('ShaderNodeMath')
    spec_thresh.operation = 'SUBTRACT'
    spec_thresh.inputs[0].default_value = 1.0
    spec_thresh.location = (-400, -570)
    links.new(node_in.outputs['Specular Size'], spec_thresh.inputs[1])

    spec_step = nodes.new('ShaderNodeMath')
    spec_step.operation = 'GREATER_THAN'
    spec_step.location = (-200, -400)
    links.new(dot_spec.outputs['Value'], spec_step.inputs[0])
    links.new(spec_thresh.outputs['Value'], spec_step.inputs[1])

    # Mask specular so it NEVER appears in shadow
    spec_masked = nodes.new('ShaderNodeMath')
    spec_masked.operation = 'MULTIPLY'
    spec_masked.location = (-50, -400)
    links.new(spec_step.outputs['Value'], spec_masked.inputs[0])
    links.new(map_cel.outputs['Result'],  spec_masked.inputs[1])

    # Softened white highlight
    white = nodes.new('ShaderNodeRGB')
    white.location = (-200, -580)
    white.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)

    spec_soften = nodes.new('ShaderNodeMix')
    spec_soften.data_type = 'RGBA'
    spec_soften.clamp_factor = True
    spec_soften.inputs[0].default_value = 0.55
    spec_soften.location = (-50, -200)
    links.new(node_in.outputs['Base Color'], spec_soften.inputs[6])
    links.new(white.outputs[0],              spec_soften.inputs[7])

    mix_spec = nodes.new('ShaderNodeMix')
    mix_spec.data_type = 'RGBA'
    mix_spec.clamp_factor = True
    mix_spec.location = (120, 150)
    links.new(spec_masked.outputs['Value'],  mix_spec.inputs[0])
    links.new(mix_cel.outputs[2],            mix_spec.inputs[6])  # A=cel result
    links.new(spec_soften.outputs[2],        mix_spec.inputs[7])  # B=specular highlight

    # ─── 3. FINAL EMISSION OUTPUT ───────────────────────────────────────
    emit = nodes.new('ShaderNodeEmission')
    emit.inputs['Strength'].default_value = 1.0
    emit.location = (400, 150)
    links.new(mix_spec.outputs[2], emit.inputs['Color'])
    links.new(emit.outputs['Emission'], node_out.inputs['Shader'])

    return ng


def _find_light_dir_node(mat):
    """Find the LightDirection Normal node for this material."""
    if not mat or not mat.node_tree:
        return None
    # 1. Per-material node in mat.node_tree (per-object independence)
    node = mat.node_tree.nodes.get("LightDirection")
    if node:
        return node
    # 2. Legacy fallback: inside group node
    toon = find_anime_toon_node(mat)
    if toon and toon.node_tree:
        return toon.node_tree.nodes.get("LightDirection")
    return None


def setup_sphere_drivers(mat, ctrl_empty):
    """
    Wire 3 drivers on this material's LightDirection Normal node so it tracks
    the Empty sphere's world-space Z-axis (matrix_world column 2).
    Rotating the sphere instantly moves shadows across the model.
    Each material maintains its own drivers independently.
    """
    light_node = _find_light_dir_node(mat)
    if not light_node:
        return

    normal_out = light_node.outputs['Normal']

    # Remove old drivers on this specific node
    for i in range(3):
        try:
            normal_out.driver_remove('default_value', i)
        except Exception:
            pass

    # Add fresh drivers: read matrix_world[2][0], [2][1], [2][2]
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


def create_anime_material(name="M_Anime_Toon"):
    """
    Creates a material with the Anime_Toon_Shader node group
    and a per-material LightDirection Normal node for independent light tracking.
    """
    mat = bpy.data.materials.new(name=name)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out_node = nodes.new('ShaderNodeOutputMaterial')
    out_node.location = (400, 0)

    group_node = nodes.new('ShaderNodeGroup')
    group_node.node_tree = get_or_create_toon_nodegroup()
    group_node.location = (0, 0)

    # Local LightDirection Normal node specific to this material
    light_node = nodes.new('ShaderNodeNormal')
    light_node.name = "LightDirection"
    light_node.label = "Light Direction (Sphere)"
    light_node.location = (-260, -50)
    light_node.outputs['Normal'].default_value = (0.0, 0.0, 1.0)

    # Connect to group node's Light Direction input
    if "Light Direction" in group_node.inputs:
        links.new(light_node.outputs['Normal'], group_node.inputs['Light Direction'])

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
    Restores full color, shader connections, and drivers.
    """
    if ng is None:
        ng = get_or_create_toon_nodegroup()

    for m in bpy.data.materials:
        if not m or not m.node_tree:
            continue

        # Skip and repair any outline or gizmo materials (never add toon node group to them!)
        name_low = m.name.lower()
        if "gizmo" in name_low or "pointer" in name_low:
            continue
        is_outline = (
            "outline" in name_low
            or "stray" in name_low
            or any(n.name in {"OutlineEmission", "StrayEmission"} for n in m.node_tree.nodes)
        )
        if is_outline:
            # Auto-repair outline material if toon group was accidentally attached
            out_node = None
            mix_shader = None
            rogue_nodes = []
            for n in m.node_tree.nodes:
                if n.type == 'OUTPUT_MATERIAL':
                    out_node = n
                elif n.type == 'MIX_SHADER':
                    mix_shader = n
                elif n.type == 'GROUP' and n.node_tree and n.node_tree.name.startswith(NODE_GROUP_NAME):
                    rogue_nodes.append(n)
                elif n.name == "LightDirection":
                    rogue_nodes.append(n)

            if out_node and mix_shader:
                cur_link = out_node.inputs['Surface'].links
                if cur_link and cur_link[0].from_node != mix_shader:
                    m.node_tree.links.new(mix_shader.outputs['Shader'], out_node.inputs['Surface'])
            for rn in rogue_nodes:
                m.node_tree.nodes.remove(rn)
            continue

        # Check if this is an anime toon material
        is_anime = m.name.startswith("M_Anime_") and not is_outline
        group_node = None
        for n in m.node_tree.nodes:
            if n.type == 'GROUP' and (n.node_tree is None or n.node_tree.name.startswith(NODE_GROUP_NAME)):
                group_node = n
                is_anime = True
                break

        if not is_anime:
            continue

        # 1. Ensure group node has ng assigned
        if not group_node:
            group_node = m.node_tree.nodes.new('ShaderNodeGroup')
            group_node.name = "Group"
            group_node.location = (0, 0)
        group_node.node_tree = ng

        # 2. Ensure Material Output exists and is connected
        out_node = None
        for n in m.node_tree.nodes:
            if n.type == 'OUTPUT_MATERIAL':
                out_node = n
                break
        if not out_node:
            out_node = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
            out_node.location = (400, 0)

        # Link group -> output if not linked
        has_out_link = any(
            l.to_node == out_node and l.from_node == group_node
            for l in m.node_tree.links
        )
        if not has_out_link:
            m.node_tree.links.new(group_node.outputs['Shader'], out_node.inputs['Surface'])

        # 3. Ensure LightDirection Normal node exists
        ld = m.node_tree.nodes.get("LightDirection")
        if not ld:
            ld = m.node_tree.nodes.new('ShaderNodeNormal')
            ld.name = "LightDirection"
            ld.label = "Light Direction (Sphere)"
            ld.location = (-260, -50)
            ld.outputs['Normal'].default_value = (0.0, 0.0, 1.0)

        # Link LightDirection -> group_node input
        if "Light Direction" in group_node.inputs:
            has_ld_link = any(
                l.to_socket == group_node.inputs['Light Direction']
                for l in m.node_tree.links
            )
            if not has_ld_link:
                m.node_tree.links.new(ld.outputs['Normal'], group_node.inputs['Light Direction'])

        # 4. Restore Light drivers if bound to a controller
        for obj in bpy.data.objects:
            if obj.type in {'MESH', 'CURVE', 'FONT', 'SURFACE'} and m.name in obj.data.materials:
                ctrl = obj.get(CTRL_PROP)
                if ctrl and isinstance(ctrl, bpy.types.Object) and ctrl.name in bpy.data.objects:
                    setup_sphere_drivers(m, ctrl)
                break


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
    transp.location = (1000, 200)

    emit = nodes.new('ShaderNodeEmission')
    emit.name = "OutlineEmission"
    emit.label = "Outline Color"
    emit.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)
    emit.inputs['Strength'].default_value = 1.0
    emit.location = (1000, -150)

    mix_s = nodes.new('ShaderNodeMixShader')
    mix_s.location = (1200, 100)
    links.new(final_alpha.outputs['Value'], mix_s.inputs['Fac'])
    links.new(transp.outputs['BSDF'], mix_s.inputs[1])
    links.new(emit.outputs['Emission'], mix_s.inputs[2])

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (1400, 100)
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
    out.location = (500, 0)
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


