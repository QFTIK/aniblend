<p align="center">
  <img src="assets/logo.png" alt="AniBlend Logo" width="220" />
</p>

<h1 align="center">AniBlend</h1>

<p align="center">
  <strong>Anime Cel-Shading &amp; Inverted Hull Outlines for Blender 4.2+ / 5.x — EEVEE &amp; Cycles</strong><br/>
  Multi-light toon shader &nbsp;·&nbsp; Ink outlines &nbsp;·&nbsp; Sketch strokes &nbsp;·&nbsp; 1-click NPR
</p>

<p align="center">
  <a href="https://github.com/QFTIK/aniblend/releases"><img src="https://img.shields.io/github/v/release/QFTIK/aniblend?label=Release&logo=github&color=ff69b4" alt="Release" /></a>
  <a href="https://github.com/QFTIK/aniblend/releases"><img src="https://img.shields.io/github/downloads/QFTIK/aniblend/total?label=Downloads&logo=github" alt="Downloads" /></a>
  <a href="https://www.blender.org/"><img src="https://img.shields.io/badge/Blender-4.2_|_5.x-orange?logo=blender&logoColor=white" alt="Blender" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0-blue.svg?logo=gnu" alt="License" /></a>
  <a href="https://github.com/QFTIK/aniblend/stargazers"><img src="https://img.shields.io/github/stars/QFTIK/aniblend?style=flat&label=Stars&logo=github" alt="Stars" /></a>
</p>

<p align="center">
  <a href="#installation"><img src="https://img.shields.io/badge/Install-1--Click-blue?style=for-the-badge" alt="Install" /></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/Quick_Start-60_sec-green?style=for-the-badge" alt="Quick start" /></a>
  <a href="#changelog"><img src="https://img.shields.io/badge/Whats_new-v1.1.0-ff69b4?style=for-the-badge" alt="Changelog" /></a>
</p>

---

**AniBlend** turns any 3D mesh into production-ready anime NPR in one click — layered cel-shading, per-light shadow tints, procedural ink outlines and pencil sketch strokes, live in the viewport. No node spaghetti, no manual Solidify setup, no drivers to wire by hand.

> **Search keywords:** blender anime shader, blender cel shading, blender toon shader, blender NPR, anime NPR blender, inverted hull outline blender, blender ink outline, blender sketch lines, vtuber shader, genshin style shader, eevee anime, cycles toon.

---

## Contents

- [Why AniBlend](#why-aniblend)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Compatibility](#compatibility)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [License](#license)

---

## Why AniBlend

| Classic Blender NPR | With AniBlend |
|---|---|
| 20+ nodes wired by hand per material | 1 click: `Apply Anime Shader` |
| 1 sun lamp = 1 flat shadow tone | Up to 8 art-directed light layers |
| Solidify + flipped normals configured manually | `Add Outlines` with 4 ink styles |
| Drivers break on rename / delete | Controllers auto-heal and stay parented to mesh |

---

## Features

### Shading

| Capability | Details |
|---|---|
| **Multi-Light Layers** | Key / Fill / Rim / Bounce stack, reorder with `Up / Down`, per-layer `Opacity` |
| **Blend Modes** | `Cover` — opaque paint layer, `Add` — luminous tint on top |
| **Light Controller** | Wireframe sphere Empty in viewport, `R` to rotate, color-coded glow pointer follows it |
| **Base Fill** | Global surface color (`Base Fill`) separated from light and shadow |
| **Per-Light Shadow Tint** | Independent `Light Color` + `Shadow Color` per layer, e.g. warm sun with violet shadow |
| **Shadow Control** | `Shadow Position`, `Shadow Softness`, `Highlight Size`, `Light Power` per layer |
| **Presets** | `Classic Cel` · `Ghibli Watercolor` · `Golden Sunset` · `Cyberpunk Neon` |

### Outlines

| Capability | Details |
|---|---|
| **Inverted Hull** | Solidify shell, outward offset, backface-culled, per-mesh material `M_Anime_Outline_*` |
| **Styles** | `Solid` — clean line · `Ink / Pen` — pressure breaks · `Dashed` — speed lines · `Sketch` — pencil grain |
| **Hand Tremor** | `Chaos` + `Stroke Density` for organic jitter |
| **Stray Strokes** | Optional second shell for hasty off-model pencil strokes (`Offset / Density / Opacity / Jitter`) |
| **Isolation** | Modifier + material prefixes per mesh, no texture leak onto inner surfaces |

### Workflow

| Capability | Details |
|---|---|
| **Tabbed UI** | `N-Panel > AniBlend`: `Shading` tab and `Outline` tab, collapsible subpanels |
| **Smart Resolve** | Click a controller or pointer — the bound mesh and active light layer auto-sync |
| **Crash-Safe** | Zero-light flat fallback, deferred depsgraph cleanup, poll-safe panels, focus kept on mesh |
| **Stdlib Only** | Pure `bpy` + `mathutils`, no `numpy` / network / filesystem permissions needed |

---

## Installation

1. Download **`aniblend-1.1.0.zip`** from the [Releases](https://github.com/QFTIK/aniblend/releases) page.
2. Blender 4.2+ / 5.x: `Edit > Preferences > Get Extensions > Install from Disk...` and pick the `.zip`.
3. Enable **AniBlend**. Panel appears at `3D Viewport > N > AniBlend`.

> Headless check: `blender --background --python-expr "import bpy; bpy.ops.mesh.primitive_monkey_add(); bpy.ops.anime.apply_shader(); print('AniBlend OK')"`

---

## Quick Start

1. Select a mesh, open `N > AniBlend`, click **Apply Anime Shader**.
2. Rotate the wireframe sphere controller with `R` — shadows follow live in `Material Preview`.
3. `Light Sources > +` adds Fill / Rim. Reorder, set `Cover / Add`, tune shadow tint.
4. `Outline` tab > **Add Outlines** — set `Thickness`, `Color`, `Style`, enable `Stray Strokes` for pencil feel.

---

## Compatibility

| Host | Status |
|---|---|
| Blender 5.0 – 5.2 LTS | Fully supported, `blender_manifest.toml` extension |
| Blender 4.2 LTS | Compatible (`blender_version_min = 4.2.0`) |
| EEVEE / Material Preview | Real-time cel + outlines |
| Cycles | Toon nodes render correctly |
| OS | Windows / macOS / Linux, Python 3.11+ built-in |

---

## Changelog

### v1.1.0 — Final multi-light release

**Shading engine**

- Multi-light compositing: from single MatCap to layered engine
- Layer reorder, per-layer opacity, `Cover` vs `Add` modes
- Per-light `Light Color` + `Shadow Color`, pointer color sync
- Dedicated `Base Fill`, surviving add / remove / toggle
- Controller hierarchy: Empties + pointers parented to mesh with inverse matrix

**Outlines**

- 4 styles: `Solid / Ink / Dashed / Sketch` + stray sketch shell
- `Thickness / Opacity / Chaos / Density` live controls
- Per-mesh isolation, leak-free inner surfaces

**Stability**

- `poll()` side-effect free — no `Writing to ID classes` errors
- Sequential layer deletion without crash, active mesh focus preserved
- Deferred `depsgraph` cleanup via `bpy.app.timers`, no in-handler deletes
- Missing controllers auto-recreate on select

Full history: [Releases](https://github.com/QFTIK/aniblend/releases) · Previous stable: `v1.0.0` · Beta: `v1.1.0-beta`

---

## Roadmap

- [ ] Shadow tint + ambient occlusion control on base fill
- [ ] Material presets for Blender Asset Browser
- [ ] UI pattern finalization: N-Panel vs header Popover vs Pie Menu

Requests and bug reports: [Issues](https://github.com/QFTIK/aniblend/issues) — attach Blender version, renderer (EEVEE/Cycles) and steps to reproduce.

---

## License

Open source under **GPL-3.0-or-later**. See [LICENSE](LICENSE).

Project links: [Releases](https://github.com/QFTIK/aniblend/releases) · [Issues](https://github.com/QFTIK/aniblend/issues) · Blender Extensions: `https://extensions.blender.org`
