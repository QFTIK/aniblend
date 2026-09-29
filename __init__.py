"""
AniBlend Extension for Blender 5+.
Fast Anime Cel-Shading and Stylized Outlines.
"""

from . import operators
from . import panels


def register():
    operators.register()
    panels.register()


def unregister():
    panels.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()
