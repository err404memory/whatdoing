"""Theme presets and dynamic color building for whatdoing.

Provides three built-in color schemes (default, ocean, forest) and helpers
to merge user overrides, resolve header/status colors, and detect optional
image-background support.
"""

from __future__ import annotations

PRESETS: dict[str, dict[str, str]] = {
    "default": {
        "bg-color": "#1a1a2e",
        "accent-color": "#0f3460",
        "header-color": "#282840",
        "text-color": "#e0e0e0",
        "table-alt-color": "#1f1f3a",
        "primary": "#0f3460",
        "secondary": "#533483",
        "accent": "#e94560",
        "surface": "#16213e",
    },
    "ocean": {
        "bg-color": "#0a1628",
        "accent-color": "#1a6b8a",
        "header-color": "#0d2137",
        "text-color": "#c8e6f0",
        "table-alt-color": "#0d2a3a",
        "primary": "#1a6b8a",
        "secondary": "#2d9cbc",
        "accent": "#4fd1c5",
        "surface": "#0d2137",
    },
    "forest": {
        "bg-color": "#1a2e1a",
        "accent-color": "#2d5a27",
        "header-color": "#1e3a1e",
        "text-color": "#d4e8c8",
        "table-alt-color": "#1f3a1a",
        "primary": "#2d5a27",
        "secondary": "#8b6914",
        "accent": "#d4a017",
        "surface": "#1e3a1e",
    },
}


def build_theme_colors(theme_config: dict) -> dict[str, str]:
    """Merge user config overrides with a preset base palette.

    Args:
        theme_config: The ``theme`` dict from Config, expected to have at
            minimum a ``name`` key selecting a preset.  Any extra keys
            whose names match preset color keys will override the preset
            value.

    Returns:
        A complete color dict ready for use in styling.
    """
    name = theme_config.get("name", "default")
    base = dict(PRESETS.get(name, PRESETS["default"]))

    # Layer any explicit color overrides from user config
    for key, value in theme_config.items():
        if key != "name" and key in base:
            base[key] = value

    return base


def get_header_color(theme_config: dict) -> str:
    """Return the header background color for Rich markup.

    Args:
        theme_config: The ``theme`` dict from Config.

    Returns:
        A hex color string suitable for Rich ``[on <color>]`` markup.
    """
    colors = build_theme_colors(theme_config)
    return colors["header-color"]


def get_status_color(theme_config: dict, status: str) -> str | None:
    """Return a custom color for the given status, if configured.

    Users can define ``status-colors`` inside their theme config::

        theme:
          name: ocean
          status-colors:
            Active: "#00ff88"
            Paused: "#ff8800"

    Args:
        theme_config: The ``theme`` dict from Config.
        status: The status string to look up (case-sensitive).

    Returns:
        The hex color string if configured, or ``None``.
    """
    status_colors = theme_config.get("status-colors", {})
    if not isinstance(status_colors, dict):
        return None
    return status_colors.get(status)


def supports_image_background() -> bool:
    """Check whether the textual-image package is installed.

    This optional dependency enables image-based terminal backgrounds.

    Returns:
        ``True`` if ``textual_image`` can be imported, ``False`` otherwise.
    """
    try:
        import importlib.util  # noqa: F401

        return importlib.util.find_spec("textual_image") is not None
    except Exception:
        return False
