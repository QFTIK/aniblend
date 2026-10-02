# AniBlend

A simple Blender add-on to give 3D models an anime cel-shaded look with customizable outlines.

Tested on Blender 4.2+ and 5.0+.

---

## What it does

- **Shadow control with a sphere**: Clicking "Apply Anime Shader" adds a small helper sphere. Select it and press `R` to rotate shadows where you want them, without changing your actual scene lights.
- **Outlines**: Inverted-hull outlines that work right in the viewport.
- **Hand-drawn style**: You can add a bit of jitter/chaos to the lines so they don't look too rigid or digital.
- **A few presets**: Quick color styles (Classic anime, Ghibli-inspired, Sunset, Cyberpunk).
- **Per-object**: Each object can have its own shadow direction and outline settings.

---

## How to install

1. Download `aniblend-1.1.0.zip` (or `aniblend.zip`) from the [Releases](https://github.com/QFTIK/aniblend/releases) page.
2. In Blender, go to **Edit > Preferences > Add-ons** (or **Get Extensions**).
3. Click the top-right menu icon and choose **Install from Disk...**
4. Pick the downloaded `.zip` file and enable it.

---

## How to use

1. Select your model.
2. Press `N` to open the sidebar and find the **AniBlend** tab.
3. Click **Apply Anime Shader**.
4. Select the wireframe sphere near your model and press `R` to aim the shadow.
5. (Optional) Click **Add Outlines** to add line art and adjust thickness or chaos.

---

## License

GPL-3.0
