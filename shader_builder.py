"""
MatCap-style Anime Cel-Shader Engine for Blender 5+.
Uses a sphere controller (Empty) for artistic light direction (no real lights needed).
Includes advanced Inverted Hull outline shader with Hand-Drawn Chaos, Opacity, and Styles.
"""

import bpy

NODE_GROUP_NAME = "Anime_Toon_Shader"
CTRL_PROP = "anime_light_ctrl"       # custom property linking mesh ↔ sphere controller
ASPECT_SOCKET = "Aspect Fix"         # global group input: viewport/render aspect for screen-space patterns
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
            'pattern': 'Shadow Pattern',
            'pscale': 'Pattern Scale',
            'pstrength': 'Pattern Strength',
            'lstrength': 'Light Pattern Strength',
            'lpattern': 'Light Pattern',
            'lpscale': 'Light Pattern Scale',
            'lpblur': 'Light Pattern Blur',
            'pblur': 'Pattern Blur',
            'mask': 'Shadow Mask',
            'lmask': 'Light Mask',
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
            'pattern': f'L{i} Pattern',
            'pscale': f'L{i} Pattern Scale',
            'pstrength': f'L{i} Pattern Strength',
            'lstrength': f'L{i} Light Pattern Strength',
            'lpattern': f'L{i} Light Pattern',
            'lpscale': f'L{i} Light Pattern Scale',
            'lpblur': f'L{i} Light Pattern Blur',
            'pblur': f'L{i} Pattern Blur',
            'mask': f'L{i} Shadow Mask',
            'lmask': f'L{i} Light Mask',
        }
        return mapping.get(prop, f"L{i} {prop.capitalize()}")


def _build_multilight_toon_nodegroup(ng, num_lights):
    """
    Internal: (re)builds the Anime_Toon_Shader node group interface and node network
    for exactly num_lights lights. Each light has its own Light Color and Shadow Color.
    The overall surface Base Color tints the accumulated lighting.
    """
    iface = ng.interface
    iface.clear()

    # 1. Global Base Color Socket (surface fill of the object)
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

        # 3. Per-Light Screentone Sockets (v1.2: procedural shadow pattern per light)
        pat_name = _get_light_socket_name(idx, 'pattern')
        psc_name = _get_light_socket_name(idx, 'pscale')
        pst_name = _get_light_socket_name(idx, 'pstrength')

        s_pat = iface.new_socket(name=pat_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_pat.default_value = 0.0
        s_pat.min_value = 0.0
        s_pat.max_value = 5.0

        s_psc = iface.new_socket(name=psc_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_psc.default_value = 40.0
        s_psc.min_value = 1.0
        s_psc.max_value = 256.0

        s_pst = iface.new_socket(name=pst_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_pst.default_value = 0.6
        s_pst.min_value = 0.0
        s_pst.max_value = 1.0

        pbl_name = _get_light_socket_name(idx, 'pblur')
        s_pbl = iface.new_socket(name=pbl_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_pbl.default_value = 0.25
        s_pbl.min_value = 0.0
        s_pbl.max_value = 1.0

        lst_name = _get_light_socket_name(idx, 'lstrength')
        s_lst = iface.new_socket(name=lst_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_lst.default_value = 0.0
        s_lst.min_value = 0.0
        s_lst.max_value = 1.0

        lpt_name = _get_light_socket_name(idx, 'lpattern')
        s_lpt = iface.new_socket(name=lpt_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_lpt.default_value = 0.0
        s_lpt.min_value = 0.0
        s_lpt.max_value = 5.0

        lps_name = _get_light_socket_name(idx, 'lpscale')
        s_lps = iface.new_socket(name=lps_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_lps.default_value = 40.0
        s_lps.min_value = 1.0
        s_lps.max_value = 256.0

        lpb_name = _get_light_socket_name(idx, 'lpblur')
        s_lpb = iface.new_socket(name=lpb_name, in_out='INPUT', socket_type='NodeSocketFloat')
        s_lpb.default_value = 0.25
        s_lpb.min_value = 0.0
        s_lpb.max_value = 1.0

    iface.new_socket(name="Shader", in_out='OUTPUT', socket_type='NodeSocketShader')
    iface.new_socket(name="Color", in_out='OUTPUT', socket_type='NodeSocketColor')
    for idx in range(num_lights):
        msk_name = _get_light_socket_name(idx, 'mask')
        iface.new_socket(name=msk_name, in_out='OUTPUT', socket_type='NodeSocketFloat')
        lmk_name = _get_light_socket_name(idx, 'lmask')
        iface.new_socket(name=lmk_name, in_out='OUTPUT', socket_type='NodeSocketFloat')

    # Global aspect correction for screen-space patterns (1.0 = square, 16/9 display = 1.78)
    asp = iface.new_socket(name=ASPECT_SOCKET, in_out='INPUT', socket_type='NodeSocketFloat')
    asp.default_value = 1.0
    asp.min_value = 0.1
    asp.max_value = 4.0

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

    tex_obj = nodes.new('ShaderNodeTexCoord')
    tex_obj.location = (-1300, -200)

    # Shared aspect-corrected screen coords: X * aspect keeps dots round on wide views
    sep_w = nodes.new('ShaderNodeSeparateXYZ')
    sep_w.location = (-1300, -400)
    links.new(tex_obj.outputs['Window'], sep_w.inputs['Vector'])

    asp_x = nodes.new('ShaderNodeMath')
    asp_x.operation = 'MULTIPLY'
    asp_x.location = (-1100, -400)
    links.new(sep_w.outputs['X'], asp_x.inputs[0])
    links.new(node_in.outputs[ASPECT_SOCKET], asp_x.inputs[1])

    comb_w = nodes.new('ShaderNodeCombineXYZ')
    comb_w.location = (-900, -400)
    links.new(asp_x.outputs['Value'], comb_w.inputs['X'])
    links.new(sep_w.outputs['Y'], comb_w.inputs['Y'])
    links.new(sep_w.outputs['Z'], comb_w.inputs['Z'])
    win_corr = comb_w.outputs['Vector']

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

        # ── Shadow screentone pattern (v1.2): procedural texture inside shadow ──
        pat_name = _get_light_socket_name(idx, 'pattern')
        psc_name = _get_light_socket_name(idx, 'pscale')
        pst_name = _get_light_socket_name(idx, 'pstrength')
        pbl_name = _get_light_socket_name(idx, 'pblur')
        msk_name = _get_light_socket_name(idx, 'mask')
        y_pat = y_off - 700

        def _build_fields(scale_sock, blur_sock, xo, yo):
            """Procedural screentone fields (dots/hatch/cross/noise) with own scale/blur."""
            uvs = nodes.new('ShaderNodeVectorMath')
            uvs.operation = 'SCALE'
            uvs.location = (xo - 1050, yo)
            links.new(win_corr, uvs.inputs[0])
            links.new(node_in.outputs[scale_sock], uvs.inputs[3])

            # Edge softness: w = blur * 0.4 (+ epsilon keeps blur 0 defined)
            wmul = nodes.new('ShaderNodeMath')
            wmul.operation = 'MULTIPLY'
            wmul.location = (xo - 1050, yo - 600)
            links.new(node_in.outputs[blur_sock], wmul.inputs[0])
            wmul.inputs[1].default_value = 0.4
            wnd = nodes.new('ShaderNodeMath')
            wnd.operation = 'ADD'
            wnd.location = (xo - 850, yo - 600)
            links.new(wmul.outputs['Value'], wnd.inputs[0])
            wnd.inputs[1].default_value = 0.001
            wout = wnd.outputs['Value']

            def _edge(center, dx, dy):
                lo = nodes.new('ShaderNodeMath')
                lo.operation = 'SUBTRACT'
                lo.location = (xo + dx, yo + dy)
                lo.inputs[0].default_value = center
                links.new(wout, lo.inputs[1])
                hi = nodes.new('ShaderNodeMath')
                hi.operation = 'ADD'
                hi.location = (xo + dx + 200, yo + dy)
                hi.inputs[0].default_value = center
                links.new(wout, hi.inputs[1])
                return lo, hi

            # Dots (halftone): regular grid via fract distance -> uniform manga dots
            sep = nodes.new('ShaderNodeSeparateXYZ')
            sep.location = (xo - 850, yo)
            links.new(uvs.outputs['Vector'], sep.inputs['Vector'])

            fx = nodes.new('ShaderNodeMath')
            fx.operation = 'MODULO'
            fx.inputs[1].default_value = 1.0
            fx.location = (xo - 650, yo + 50)
            links.new(sep.outputs['X'], fx.inputs[0])

            fy = nodes.new('ShaderNodeMath')
            fy.operation = 'MODULO'
            fy.inputs[1].default_value = 1.0
            fy.location = (xo - 650, yo - 50)
            links.new(sep.outputs['Y'], fy.inputs[0])

            dx = nodes.new('ShaderNodeMath')
            dx.operation = 'SUBTRACT'
            dx.inputs[1].default_value = 0.5
            dx.location = (xo - 450, yo + 50)
            links.new(fx.outputs['Value'], dx.inputs[0])

            dy = nodes.new('ShaderNodeMath')
            dy.operation = 'SUBTRACT'
            dy.inputs[1].default_value = 0.5
            dy.location = (xo - 450, yo - 50)
            links.new(fy.outputs['Value'], dy.inputs[0])

            dx2 = nodes.new('ShaderNodeMath')
            dx2.operation = 'MULTIPLY'
            dx2.location = (xo - 250, yo + 50)
            links.new(dx.outputs['Value'], dx2.inputs[0])
            links.new(dx.outputs['Value'], dx2.inputs[1])

            dy2 = nodes.new('ShaderNodeMath')
            dy2.operation = 'MULTIPLY'
            dy2.location = (xo - 250, yo - 50)
            links.new(dy.outputs['Value'], dy2.inputs[0])
            links.new(dy.outputs['Value'], dy2.inputs[1])

            dsum = nodes.new('ShaderNodeMath')
            dsum.operation = 'ADD'
            dsum.location = (xo - 50, yo)
            links.new(dx2.outputs['Value'], dsum.inputs[0])
            links.new(dy2.outputs['Value'], dsum.inputs[1])

            dlen = nodes.new('ShaderNodeMath')
            dlen.operation = 'SQRT'
            dlen.location = (xo + 150, yo)
            links.new(dsum.outputs['Value'], dlen.inputs[0])

            dots_map = nodes.new('ShaderNodeMapRange')
            dots_map.interpolation_type = 'SMOOTHSTEP'
            dots_map.clamp = True
            dots_map.location = (xo + 350, yo)
            links.new(dlen.outputs['Value'], dots_map.inputs['Value'])
            dots_lo, dots_hi = _edge(0.35, -850, -750)
            links.new(dots_lo.outputs['Value'], dots_map.inputs['From Min'])
            links.new(dots_hi.outputs['Value'], dots_map.inputs['From Max'])

            dots = nodes.new('ShaderNodeMath')
            dots.operation = 'SUBTRACT'
            dots.inputs[0].default_value = 1.0
            dots.location = (xo + 550, yo)
            links.new(dots_map.outputs['Result'], dots.inputs[1])

            # Hatch: Wave bands X -> lines
            wave_x = nodes.new('ShaderNodeTexWave')
            wave_x.wave_type = 'BANDS'
            wave_x.bands_direction = 'X'
            wave_x.inputs['Scale'].default_value = 1.0
            wave_x.location = (xo - 850, yo - 150)
            links.new(uvs.outputs['Vector'], wave_x.inputs['Vector'])

            hatch = nodes.new('ShaderNodeMapRange')
            hatch.interpolation_type = 'SMOOTHSTEP'
            hatch.clamp = True
            hatch.location = (xo - 650, yo - 150)
            links.new(wave_x.outputs['Fac'], hatch.inputs['Value'])
            hatch_lo, hatch_hi = _edge(0.5, -850, -900)
            links.new(hatch_lo.outputs['Value'], hatch.inputs['From Min'])
            links.new(hatch_hi.outputs['Value'], hatch.inputs['From Max'])

            # Cross-hatch: Wave bands Y AND hatch
            wave_y = nodes.new('ShaderNodeTexWave')
            wave_y.wave_type = 'BANDS'
            wave_y.bands_direction = 'Y'
            wave_y.inputs['Scale'].default_value = 1.0
            wave_y.location = (xo - 850, yo - 300)
            links.new(uvs.outputs['Vector'], wave_y.inputs['Vector'])

            hatch_y = nodes.new('ShaderNodeMapRange')
            hatch_y.interpolation_type = 'SMOOTHSTEP'
            hatch_y.clamp = True
            hatch_y.location = (xo - 650, yo - 300)
            links.new(wave_y.outputs['Fac'], hatch_y.inputs['Value'])
            hatch_y_lo, hatch_y_hi = _edge(0.5, -850, -1050)
            links.new(hatch_y_lo.outputs['Value'], hatch_y.inputs['From Min'])
            links.new(hatch_y_hi.outputs['Value'], hatch_y.inputs['From Max'])

            cross = nodes.new('ShaderNodeMath')
            cross.operation = 'MULTIPLY'
            cross.location = (xo - 450, yo - 225)
            links.new(hatch.outputs['Result'], cross.inputs[0])
            links.new(hatch_y.outputs['Result'], cross.inputs[1])

            # Grain: Noise -> soft threshold
            grain = nodes.new('ShaderNodeTexNoise')
            grain.inputs['Scale'].default_value = 1.0
            grain.inputs['Detail'].default_value = 2.0
            grain.location = (xo - 850, yo - 450)
            links.new(uvs.outputs['Vector'], grain.inputs['Vector'])

            grain_map = nodes.new('ShaderNodeMapRange')
            grain_map.interpolation_type = 'SMOOTHSTEP'
            grain_map.clamp = True
            grain_map.location = (xo - 650, yo - 450)
            links.new(grain.outputs['Fac'], grain_map.inputs['Value'])
            grain_lo, grain_hi = _edge(0.5, -850, -1200)
            links.new(grain_lo.outputs['Value'], grain_map.inputs['From Min'])
            links.new(grain_hi.outputs['Value'], grain_map.inputs['From Max'])

            return (dots.outputs['Value'], hatch.outputs['Result'],
                    cross.outputs['Value'], grain_map.outputs['Result'])

        lpscale_name = _get_light_socket_name(idx, 'lpscale')
        lpblur_name = _get_light_socket_name(idx, 'lpblur')
        f_s = _build_fields(psc_name, pbl_name, 0, y_pat)
        f_l = _build_fields(lpscale_name, lpblur_name, 0, y_pat - 1400)

        # Pattern select: id 0=None 1=Dots 2=Hatch 3=Cross 4=Noise (5=Image handled at material level)
        # Shadow and light have independent selectors sharing the same procedural fields
        lpt_name = _get_light_socket_name(idx, 'lpattern')

        def _pat_gate(pid, src, x, y, sock=None):
            gate = nodes.new('ShaderNodeMath')
            gate.operation = 'COMPARE'
            gate.location = (x, y)
            links.new(node_in.outputs[sock or pat_name], gate.inputs[0])
            gate.inputs[1].default_value = float(pid)
            gate.inputs[2].default_value = 0.2
            gated = nodes.new('ShaderNodeMath')
            gated.operation = 'MULTIPLY'
            gated.location = (x + 200, y)
            links.new(src, gated.inputs[0])
            links.new(gate.outputs['Value'], gated.inputs[1])
            return gated.outputs['Value']

        m_sel = _pat_gate(1, f_s[0], -250, y_pat)
        for _pid, _src in ((2, f_s[1]),
                           (3, f_s[2]),
                           (4, f_s[3])):
            # chain: mix(prev, candidate, gate_pid)
            _sel = nodes.new('ShaderNodeMix')
            _sel.data_type = 'FLOAT'
            _sel.location = (-50, y_pat - 550)
            _gate = nodes.new('ShaderNodeMath')
            _gate.operation = 'COMPARE'
            _gate.location = (-250, y_pat - 150 * _pid)
            links.new(node_in.outputs[pat_name], _gate.inputs[0])
            _gate.inputs[1].default_value = float(_pid)
            _gate.inputs[2].default_value = 0.2
            links.new(_gate.outputs['Value'], _sel.inputs[0])
            links.new(m_sel, _sel.inputs[2])
            links.new(_src, _sel.inputs[3])
            m_sel = _sel.outputs[0]

        # Independent light selector over the same procedural fields
        m_lsel = _pat_gate(1, f_l[0], -250, y_pat - 1350, lpt_name)
        for _pid, _src in ((2, f_l[1]),
                           (3, f_l[2]),
                           (4, f_l[3])):
            _lsel = nodes.new('ShaderNodeMix')
            _lsel.data_type = 'FLOAT'
            _lsel.location = (-50, y_pat - 1900)
            _lgate = nodes.new('ShaderNodeMath')
            _lgate.operation = 'COMPARE'
            _lgate.location = (-250, y_pat - 1350 - 150 * _pid)
            links.new(node_in.outputs[lpt_name], _lgate.inputs[0])
            _lgate.inputs[1].default_value = float(_pid)
            _lgate.inputs[2].default_value = 0.2
            links.new(_lgate.outputs['Value'], _lsel.inputs[0])
            links.new(m_lsel, _lsel.inputs[2])
            links.new(_src, _lsel.inputs[3])
            m_lsel = _lsel.outputs[0]

        # Apply pattern only inside deep shadow with a crisp tone edge (no smearing on curves)
        deep = nodes.new('ShaderNodeMath')
        deep.operation = 'LESS_THAN'
        deep.inputs[1].default_value = 0.5
        deep.location = (150, y_pat - 550)
        links.new(c_en.outputs['Value'], deep.inputs[0])

        k1 = nodes.new('ShaderNodeMath')
        k1.operation = 'MULTIPLY'
        k1.location = (350, y_pat - 550)
        links.new(m_sel, k1.inputs[0])
        links.new(node_in.outputs[pst_name], k1.inputs[1])

        k2 = nodes.new('ShaderNodeMath')
        k2.operation = 'MULTIPLY'
        k2.location = (550, y_pat - 550)
        links.new(k1.outputs['Value'], k2.inputs[0])
        links.new(deep.outputs['Value'], k2.inputs[1])

        tone_pat = nodes.new('ShaderNodeMix')
        tone_pat.data_type = 'RGBA'
        tone_pat.blend_type = 'MIX'
        tone_pat.location = (750, y_off)
        links.new(k2.outputs['Value'], tone_pat.inputs[0])
        links.new(mix_tone.outputs[2], tone_pat.inputs[6])
        links.new(scale_lit.outputs['Vector'], tone_pat.inputs[7])

        # ── Same pattern on light: pull lit tone toward shadow inside lit zone ──
        lst_name = _get_light_socket_name(idx, 'lstrength')
        lmk_name = _get_light_socket_name(idx, 'lmask')
        deep_lit = nodes.new('ShaderNodeMath')
        deep_lit.operation = 'GREATER_THAN'
        deep_lit.inputs[1].default_value = 0.5
        deep_lit.location = (950, y_off)
        links.new(c_en.outputs['Value'], deep_lit.inputs[0])

        kl1 = nodes.new('ShaderNodeMath')
        kl1.operation = 'MULTIPLY'
        kl1.location = (1150, y_off)
        links.new(m_lsel, kl1.inputs[0])
        links.new(node_in.outputs[lst_name], kl1.inputs[1])

        kl2 = nodes.new('ShaderNodeMath')
        kl2.operation = 'MULTIPLY'
        kl2.location = (1350, y_off)
        links.new(kl1.outputs['Value'], kl2.inputs[0])
        links.new(deep_lit.outputs['Value'], kl2.inputs[1])

        tone_lit = nodes.new('ShaderNodeMix')
        tone_lit.data_type = 'RGBA'
        tone_lit.blend_type = 'MIX'
        tone_lit.location = (1550, y_off)
        links.new(kl2.outputs['Value'], tone_lit.inputs[0])
        links.new(tone_pat.outputs[2], tone_lit.inputs[6])
        links.new(node_in.outputs[shd_name], tone_lit.inputs[7])
        tone_colors.append(tone_lit.outputs[2])

        # Shadow mask output for material-level image patterns: (1 - raw_cel) * enabled * opacity
        opc_name = _get_light_socket_name(idx, 'opacity')
        m_not = nodes.new('ShaderNodeMath')
        m_not.operation = 'SUBTRACT'
        m_not.inputs[0].default_value = 1.0
        m_not.location = (950, y_pat - 550)
        links.new(map_c.outputs['Result'], m_not.inputs[1])

        m_en = nodes.new('ShaderNodeMath')
        m_en.operation = 'MULTIPLY'
        m_en.location = (1150, y_pat - 550)
        links.new(m_not.outputs['Value'], m_en.inputs[0])
        links.new(node_in.outputs[en_name], m_en.inputs[1])

        m_op = nodes.new('ShaderNodeMath')
        m_op.operation = 'MULTIPLY'
        m_op.location = (1350, y_pat - 550)
        links.new(m_en.outputs['Value'], m_op.inputs[0])
        links.new(node_in.outputs[opc_name], m_op.inputs[1])
        links.new(m_op.outputs['Value'], node_out.inputs[msk_name])

        # Light mask output for material-level image patterns: raw_cel * enabled * opacity
        lm_en = nodes.new('ShaderNodeMath')
        lm_en.operation = 'MULTIPLY'
        lm_en.location = (950, y_off - 200)
        links.new(map_c.outputs['Result'], lm_en.inputs[0])
        links.new(node_in.outputs[en_name], lm_en.inputs[1])

        lm_op = nodes.new('ShaderNodeMath')
        lm_op.operation = 'MULTIPLY'
        lm_op.location = (1150, y_off - 200)
        links.new(lm_en.outputs['Value'], lm_op.inputs[0])
        links.new(node_in.outputs[opc_name], lm_op.inputs[1])
        links.new(lm_op.outputs['Value'], node_out.inputs[lmk_name])

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

    # Final Surface: Multiply accumulated lighting tone with Base Color
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
    # Flat color output for material-level image screentone overlays (v1.2)
    links.new(final_color.outputs[2], node_out.inputs['Color'])

    # Stamp the node group with its light count and schema version (v9 = independent light scale/blur)
    ng["_anime_num_lights"] = num_lights
    ng["_anime_schema_ver"] = 9


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
    elif _count_ng_lights(ng) != num_lights or ng.get("_anime_schema_ver", 0) != 9:
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




_PATTERN_IDS = {
    'NONE': 0.0,
    'DOTS': 1.0,
    'HATCH': 2.0,
    'CROSS': 3.0,
    'NOISE': 4.0,
    'IMAGE': 5.0,
}

_PAT_PREFIX = "AnimePat_"


def _sync_pattern_image_overlay(mat, toon_node, mesh_obj):
    """Material-level screentone for lights using a custom brush image (pattern == IMAGE).

    The shared node group cannot hold per-mesh images, so image sampling lives in the
    material tree, driven by the group's per-light Shadow Mask outputs. Idempotent:
    rebuilds the overlay chain on every sync and removes it when unused.
    """
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    def _rm(node):
        try:
            nodes.remove(node)
        except Exception:
            pass

    def _restore_shader_path():
        out_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if out_node is not None and 'Shader' in toon_node.outputs:
            try:
                links.new(toon_node.outputs['Shader'], out_node.inputs['Surface'])
            except Exception:
                pass

    def _img_ok(img):
        return img is not None and img.name in bpy.data.images

    img_lights = []
    if mesh_obj is not None and hasattr(mesh_obj, "anime_lights"):
        for idx, li in enumerate(mesh_obj.anime_lights):
            shadow_img = getattr(li, 'pattern_image', None)
            light_img = getattr(li, 'light_image', None)
            do_lift = getattr(li, 'pattern', 'NONE') == 'IMAGE' and _img_ok(shadow_img)
            do_pull = getattr(li, 'light_pattern', 'NONE') == 'IMAGE' and (
                _img_ok(light_img) or _img_ok(shadow_img))
            if do_lift or do_pull:
                img_lights.append((idx, li, do_lift, do_pull))

    stale = [n for n in nodes if n.name.startswith(_PAT_PREFIX)]
    if not img_lights or 'Color' not in toon_node.outputs:
        for n in stale:
            _rm(n)
        _restore_shader_path()
        return

    keep = set()

    def _get(name, ntype, x, y):
        n = nodes.get(name)
        if n is None:
            n = nodes.new(ntype)
            n.name = name
            n.location = (x, y)
        keep.add(name)
        return n

    uv = _get(_PAT_PREFIX + "UV", 'ShaderNodeTexCoord', 200, -600)
    # Screen-space sampling with aspect fix: brush texture stays round and fixed to camera
    sepw = _get(_PAT_PREFIX + "SepW", 'ShaderNodeSeparateXYZ', 200, -750)
    try:
        links.new(uv.outputs['Window'], sepw.inputs['Vector'])
    except Exception:
        pass
    mulx = _get(_PAT_PREFIX + "MulX", 'ShaderNodeMath', 400, -750)
    mulx.operation = 'MULTIPLY'
    try:
        _oscene = bpy.context.scene
    except Exception:
        _oscene = None
    try:
        mulx.inputs[1].default_value = _current_pattern_aspect()
    except Exception:
        pass
    _drive_float_input(mulx, 1, _oscene)
    try:
        links.new(sepw.outputs['X'], mulx.inputs[0])
    except Exception:
        pass
    combw = _get(_PAT_PREFIX + "CombW", 'ShaderNodeCombineXYZ', 600, -750)
    try:
        links.new(mulx.outputs['Value'], combw.inputs['X'])
        links.new(sepw.outputs['Y'], combw.inputs['Y'])
        links.new(sepw.outputs['Z'], combw.inputs['Z'])
    except Exception:
        pass
    uv_out = combw.outputs['Vector']

    cur = toon_node.outputs['Color']
    for idx, li, do_lift, do_pull in img_lights:
        msk_name = _get_light_socket_name(idx, 'mask')
        lmk_name = _get_light_socket_name(idx, 'lmask')
        if msk_name not in toon_node.outputs or lmk_name not in toon_node.outputs:
            continue
        tag = f"{idx + 1}"

        if do_lift:
            tex = _get(_PAT_PREFIX + f"Tex_{tag}", 'ShaderNodeTexImage', 400 + idx * 60, -600)
            tex.image = li.pattern_image
            try:
                links.new(uv_out, tex.inputs['Vector'])
            except Exception:
                pass

            bw = _get(_PAT_PREFIX + f"BW_{tag}", 'ShaderNodeRGBToBW', 400 + idx * 60, -750)
            try:
                links.new(tex.outputs['Color'], bw.inputs['Color'])
            except Exception:
                pass

            k1 = _get(_PAT_PREFIX + f"K1_{tag}", 'ShaderNodeMath', 600 + idx * 60, -600)
            k1.operation = 'MULTIPLY'
            k1.inputs[1].default_value = getattr(li, 'pattern_strength', 0.6)
            try:
                links.new(toon_node.outputs[msk_name], k1.inputs[0])
            except Exception:
                pass

            k2 = _get(_PAT_PREFIX + f"K2_{tag}", 'ShaderNodeMath', 800 + idx * 60, -600)
            k2.operation = 'MULTIPLY'
            try:
                links.new(k1.outputs['Value'], k2.inputs[0])
                links.new(bw.outputs['Val'], k2.inputs[1])
            except Exception:
                pass

            mx = _get(_PAT_PREFIX + f"Mix_{tag}", 'ShaderNodeMix', 1000 + idx * 60, -600)
            mx.data_type = 'RGBA'
            mx.blend_type = 'MIX'
            try:
                mx.inputs[7].default_value = tuple(li.light_color)
            except Exception:
                pass
            try:
                links.new(k2.outputs['Value'], mx.inputs[0])
                links.new(cur, mx.inputs[6])
            except Exception:
                pass
            cur = mx.outputs[2]

        # Independent brush image on light (falls back to the shadow image)
        if do_pull:
            pull_img = li.light_image if _img_ok(li.light_image) else li.pattern_image
            texl = _get(_PAT_PREFIX + f"TexL_{tag}", 'ShaderNodeTexImage', 400 + idx * 60, -900)
            texl.image = pull_img
            try:
                links.new(uv_out, texl.inputs['Vector'])
            except Exception:
                pass

            bwl = _get(_PAT_PREFIX + f"BWL_{tag}", 'ShaderNodeRGBToBW', 600 + idx * 60, -900)
            try:
                links.new(texl.outputs['Color'], bwl.inputs['Color'])
            except Exception:
                pass

            k3 = _get(_PAT_PREFIX + f"L1_{tag}", 'ShaderNodeMath', 800 + idx * 60, -900)
            k3.operation = 'MULTIPLY'
            k3.inputs[1].default_value = getattr(li, 'pattern_light_strength', 0.0)
            try:
                links.new(toon_node.outputs[lmk_name], k3.inputs[0])
            except Exception:
                pass

            k4 = _get(_PAT_PREFIX + f"L2_{tag}", 'ShaderNodeMath', 1000 + idx * 60, -900)
            k4.operation = 'MULTIPLY'
            try:
                links.new(k3.outputs['Value'], k4.inputs[0])
                links.new(bwl.outputs['Val'], k4.inputs[1])
            except Exception:
                pass

            mxl = _get(_PAT_PREFIX + f"MixL_{tag}", 'ShaderNodeMix', 1200 + idx * 60, -900)
            mxl.data_type = 'RGBA'
            mxl.blend_type = 'MIX'
            try:
                mxl.inputs[7].default_value = tuple(li.shadow_color)
            except Exception:
                pass
            try:
                links.new(k4.outputs['Value'], mxl.inputs[0])
                links.new(cur, mxl.inputs[6])
            except Exception:
                pass
            cur = mxl.outputs[2]

    emis = _get(_PAT_PREFIX + "Emission", 'ShaderNodeEmission', 1300, -600)
    try:
        links.new(cur, emis.inputs['Color'])
    except Exception:
        pass
    out_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if out_node is not None:
        try:
            links.new(emis.outputs['Emission'], out_node.inputs['Surface'])
        except Exception:
            pass

    for n in stale:
        if n.name not in keep:
            _rm(n)


def _current_pattern_aspect():
    """Render aspect (w/h with pixel aspect). Viewport is live-corrected via driver."""
    try:
        rd = bpy.context.scene.render
        px = (rd.pixel_aspect_x / rd.pixel_aspect_y) if rd.pixel_aspect_y else 1.0
        if rd.resolution_y:
            return max(0.1, min(4.0, (rd.resolution_x / rd.resolution_y) * px))
    except Exception:
        pass
    return 1.0


def _drive_float_input(node, key, scene):
    """Point a float socket/input at Scene.anime_pattern_aspect (idempotent-ish)."""
    try:
        inp = node.inputs[key]
    except Exception:
        return
    try:
        inp.driver_remove('default_value')
    except Exception:
        pass
    if scene is None:
        return
    try:
        fcurve = inp.driver_add('default_value')
        drv = fcurve.driver
        drv.type = 'SCRIPTED'
        var = drv.variables.new()
        var.name = 'v'
        var.type = 'SINGLE_PROP'
        tgt = var.targets[0]
        tgt.id_type = 'SCENE'
        tgt.id = scene
        tgt.data_path = 'anime_pattern_aspect'
        drv.expression = 'v'
    except Exception:
        pass


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

                # Screentone pattern sockets (v1.2)
                pat_socket = _get_light_socket_name(idx, 'pattern')
                psc_socket = _get_light_socket_name(idx, 'pscale')
                pst_socket = _get_light_socket_name(idx, 'pstrength')
                if pat_socket in toon_node.inputs:
                    toon_node.inputs[pat_socket].default_value = _PATTERN_IDS.get(
                        getattr(light_item, 'pattern', 'NONE'), 0.0)
                if psc_socket in toon_node.inputs:
                    toon_node.inputs[psc_socket].default_value = getattr(light_item, 'pattern_scale', 40.0)
                if pst_socket in toon_node.inputs:
                    toon_node.inputs[pst_socket].default_value = getattr(light_item, 'pattern_strength', 0.6)
                lst_socket = _get_light_socket_name(idx, 'lstrength')
                if lst_socket in toon_node.inputs:
                    toon_node.inputs[lst_socket].default_value = getattr(light_item, 'pattern_light_strength', 0.0)
                lpt_socket = _get_light_socket_name(idx, 'lpattern')
                if lpt_socket in toon_node.inputs:
                    toon_node.inputs[lpt_socket].default_value = _PATTERN_IDS.get(
                        getattr(light_item, 'light_pattern', 'NONE'), 0.0)
                lps_socket = _get_light_socket_name(idx, 'lpscale')
                if lps_socket in toon_node.inputs:
                    toon_node.inputs[lps_socket].default_value = getattr(light_item, 'light_pattern_scale', 40.0)
                lpb_socket = _get_light_socket_name(idx, 'lpblur')
                if lpb_socket in toon_node.inputs:
                    toon_node.inputs[lpb_socket].default_value = getattr(light_item, 'light_pattern_blur', 0.25)
                pbl_socket = _get_light_socket_name(idx, 'pblur')
                if pbl_socket in toon_node.inputs:
                    toon_node.inputs[pbl_socket].default_value = getattr(light_item, 'pattern_blur', 0.25)
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

        # Aspect correction: render aspect as fallback, viewport aspect via live driver
        try:
            _scene = bpy.context.scene
        except Exception:
            _scene = None
        if ASPECT_SOCKET in toon_node.inputs:
            try:
                toon_node.inputs[ASPECT_SOCKET].default_value = _current_pattern_aspect()
            except Exception:
                pass
            _drive_float_input(toon_node, ASPECT_SOCKET, _scene)

        # Reconcile material-level image screentone overlay (v1.2)
        _sync_pattern_image_overlay(mat, toon_node, mesh_obj)


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


