<table>
  <tr>
    <td width="140" valign="middle"><img src="assets/logo.png" alt="AniBlend Logo" width="130" /></td>
    <td valign="middle"><h1>AniBlend</h1><p><strong>Anime cel-shading and inverted hull outlines for Blender 4.2+ / 5.x (EEVEE and Cycles).</strong><br />Multi-light toon shader, per-light shadow tints, screen-space screentone, ink outlines and pencil sketch strokes — one click, live in the viewport.</p></td>
  </tr>
</table>

[![Release](https://img.shields.io/github/v/release/QFTIK/aniblend?label=Release&logo=github&color=ff69b4)](https://github.com/QFTIK/aniblend/releases) [![Downloads](https://img.shields.io/github/downloads/QFTIK/aniblend/total?label=Downloads&logo=github)](https://github.com/QFTIK/aniblend/releases) [![Blender](https://img.shields.io/badge/Blender-4.2_|_5.x-orange?logo=blender&logoColor=white)](https://www.blender.org) [![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg?logo=gnu)](LICENSE) [![Stars](https://img.shields.io/github/stars/QFTIK/aniblend?style=flat&label=Stars&logo=github)](https://github.com/QFTIK/aniblend/stargazers)

## Install

1. Download **`aniblend-1.2.0.zip`** from [Releases](https://github.com/QFTIK/aniblend/releases).
2. Blender: `Edit > Preferences > Get Extensions > Install from Disk...`, pick the `.zip`, enable **AniBlend**.
3. Panel appears at `3D Viewport > N > AniBlend`.

## Quick start

1. Select a mesh, open `N > AniBlend`, click **Apply Anime Shader**.
2. Rotate the wireframe sphere controller with `R` — shadows follow live.
3. `+` adds Fill / Rim lights; reorder, set `Cover / Add`, tint shadows.
4. Outline tab: **Add Outlines**, tune width, style, stray pencil strokes.

## Features

| Area | What you get |
|---|---|
| **Multi-light cel** | Up to 8 art-directed layers (Key / Fill / Rim / Bounce), reorder, per-layer opacity, `Cover` vs `Add` blending |
| **Control** | Viewport sphere controller per light (`R` to aim), color-coded glow pointers, parented to the mesh |
| **Color** | Global Base Fill plus independent Light / Shadow tint per layer |
| **Screentone** | Independent Dots / Hatch / Cross / Noise / brush-Image patterns for shadow and lit zones, with Scale, Strength, Blur; screen-space, aspect-fixed, crisp tone edge |
| **Outlines** | Inverted-hull shell: Solid / Ink / Dashed / Sketch, hand tremor, optional stray sketch strokes, per-mesh isolation |
| **Safety** | Poll-safe panels, no crashes on layer delete, controllers auto-heal, old materials rebuild themselves |

## Compatibility

Blender 5.0–5.2 LTS and 4.2 LTS · EEVEE / Material Preview real-time · Cycles ready · Windows / macOS / Linux · stdlib only, no network or extra permissions.

## Changelog

**v1.2.0** — independent shadow + light screentone (patterns, scale, blur, strength, custom images), flat compact panel, English UI, presets removed.
<details>
<summary>Older</summary>

**v1.1.0** — multi-light compositing, per-light shadow tints, collapsible tabs, controller hierarchy, outline leak fixes.
**v1.0.0** — first stable single-light anime shader with inverted-hull outlines.
</details>

## Roadmap

- Shadow tint + ambient occlusion on base fill · Asset Browser material presets · header Popover / Pie Menu UI option

Issues and ideas: [GitHub Issues](https://github.com/QFTIK/aniblend/issues) — attach Blender version, renderer, repro steps.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE). Links: [Releases](https://github.com/QFTIK/aniblend/releases) · [Issues](https://github.com/QFTIK/aniblend/issues)

<!-- SEO: blender anime shader, blender cel shading, blender toon shader, blender NPR, anime NPR blender, inverted hull outline blender, blender ink outline, screentone shader, vtuber shader, eevee anime, cycles toon -->
