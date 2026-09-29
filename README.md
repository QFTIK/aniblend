# AniBlend — Anime Cel-Shading & Outlines for Blender

[![Blender 4.2+ | 5.0+](https://img.shields.io/badge/Blender-4.2%20%7C%205.0%2B-orange?logo=blender&logoColor=white)](https://www.blender.org/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Version: 1.0.0](https://img.shields.io/badge/Version-1.0.0-emerald.svg)](https://github.com/QFTIK/aniblend/releases)

Fast, lightweight non-photorealistic rendering (NPR) add-on and extension for Blender 4.2+ and 5.0+. Turn any 3D model into stylized 2D anime art with interactive shadow steering and procedural inverted-hull outlines.

---

## Key Features

- **Interactive 3D Light Controller**: Generates an empty wireframe sphere per mesh. Rotate it (`R`) to steer shadow angles directly in the viewport without touching scene lights.
- **Procedural Inverted-Hull Outlines**: Real-time EEVEE-Next outlines with zero Grease Pencil overhead.
- **Hand-Drawn Chaos**: Adjust line jitter and organic waviness to avoid sterile 3D looks.
- **4 Outline Styles**: `Solid`, `Ink/Pen`, `Dashed`, and `Sketch`.
- **Secondary Stray Strokes**: Adds subtle sketchy pencil strokes around the silhouette.
- **Color Presets**: One-click palettes including `Classic Cel`, `Soft Ghibli`, `Warm Sunset`, and `Cyberpunk`.
- **Per-Mesh Isolation**: Each object maintains independent lighting directions and outline parameters.

---

## Installation

### Blender Extension (Blender 4.2+ / 5.0+)
1. Go to **Edit > Preferences > Get Extensions**.
2. Click top-right menu **⌄ > Install from Disk...**
3. Select `aniblend-1.0.0.zip`.

### Traditional Add-on
1. Go to **Edit > Preferences > Add-ons**.
2. Click top-right menu **⌄ > Install from Disk...**
3. Select `aniblend.zip` and enable the checkbox.

---

## Quick Start

1. Select your mesh in Object Mode.
2. Open sidebar (`N`) > **AniBlend** tab.
3. Click **Apply Anime Shader** — select the generated sphere and press `R` to position shadows.
4. Click **Add Outlines** — adjust thickness, chaos, and style in the panel.

---

## License

GNU General Public License v3.0 (GPL-3.0). See [LICENSE](LICENSE) for details.
