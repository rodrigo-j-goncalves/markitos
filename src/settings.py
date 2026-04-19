import json
import os
from platformdirs import user_config_dir


class Settings:
    APP_NAME = "markitos"
    DEFAULTS = {
        "font_family": "Sans Serif",
        "font_size": 14,
        "text_color": "#1a1a1a",
        "bg_color": "#ffffff",
        "heading_color": "#2c5282",
        "window_x": 100,
        "window_y": 100,
        "window_width": 1000,
        "window_height": 700,
        "guide_color": "",       # empty = derive from text_color
        "guide_opacity": 0.5,    # 0.0 – 1.0
        "guide_width": 1,        # pixels
        "symbol_opacity": 0.5,   # 0.0 – 1.0  opacity of space/tab/¶ markers
        "toggle_mode_shortcut": "Ctrl+Return",
        "collapse_all_shortcut": "Ctrl+Shift+C",
        "expand_all_shortcut": "Ctrl+Shift+X",
        "recent_files": [],
        "last_file": None,
        "reopen_last_file": False,
        "show_line_numbers": False,
        "ln_bg_color": "",           # empty = auto-derive (guide_color @ 12% on bg)
        "open_dir": "",              # last directory used in open/save dialogs
        "line_spacing": "1.65",
        "para_spacing": "0.6em",
        "md_max_width": "95%", # default: 66
        "word_wrap": True,
        "md_font_family": "",   # "" = use font_family
        "md_font_size": 0,      # 0  = use font_size
        "image_paste_folder": "assets",  # folder for pasted images (relative to the .md file)
    }

    def __init__(self):
        config_dir = user_config_dir(self.APP_NAME)
        os.makedirs(config_dir, exist_ok=True)
        self.config_path = os.path.join(config_dir, "settings.json")
        self._data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = json.load(f)
            self._data.update(data)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    # Keys that change during normal use (not via the settings dialog)
    # and must be written on close without overwriting appearance settings
    # saved by other windows.
    _SESSION_KEYS = (
        "window_x", "window_y", "window_width", "window_height",
        "recent_files", "last_file", "open_dir", "word_wrap",
        "font_size",
    )

    def save_geometry(self):
        """Reload settings from disk and update only session-state keys.

        This preserves appearance settings saved by other windows while
        still persisting geometry, recent files, and other operational state.
        """
        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        for key in self._SESSION_KEYS:
            data[key] = self._data[key]
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def copy(self) -> dict:
        """Return a shallow copy of the current settings data."""
        return dict(self._data)

    def restore(self, data: dict):
        self._data.update(data)

    def __getitem__(self, key):
        return self._data.get(key, self.DEFAULTS.get(key))

    def __setitem__(self, key, value):
        self._data[key] = value

    def get(self, key, default=None):
        return self._data.get(
            key, default if default is not None else self.DEFAULTS.get(key)
        )

    def add_recent_file(self, path: str):
        path = os.path.abspath(path)
        recent = list(self._data.get("recent_files", []))
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self._data["recent_files"] = recent[:10]
