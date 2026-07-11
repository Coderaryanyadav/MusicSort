import json
import os
from pathlib import Path
from typing import List, Set, Dict, Any

APP_NAME = "MusicSort"
APP_VERSION = "1.0.0"

# Directories
DEFAULT_APP_DIR = Path.home() / ".musicsort"
DEFAULT_DB_PATH = DEFAULT_APP_DIR / "musicsort.db"
DEFAULT_BACKUP_DIR = DEFAULT_APP_DIR / "backups"
DEFAULT_LOGS_DIR = DEFAULT_APP_DIR / "logs"
DEFAULT_REPORTS_DIR = DEFAULT_APP_DIR / "reports"
SETTINGS_FILE_PATH = DEFAULT_APP_DIR / "settings.json"

# Create directories
DEFAULT_APP_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOGS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Default configuration settings
DEFAULT_SETTINGS: Dict[str, Any] = {
    "default_target_dir": "",
    "theme": "dark",  # "dark" or "light"
    "accent_color": "#00adb5",
    "scan_frequency": 0,  # in hours (0 = manual)
    "backup_dir": str(DEFAULT_BACKUP_DIR),
    "auto_scan": False,
    "auto_classification": True,
    "rename_rules": "{artist} - {title}",  # standard rename format
    "conflict_mode": "Rename",  # "Rename", "Skip", "Replace"
    "ignore_folders": [".git", "node_modules", ".musicsort", ".venv", "backups"],
    "ignored_extensions": []
}

# Audio Extensions Supported
SUPPORTED_EXTENSIONS: Set[str] = {
    ".mp3", ".m4a", ".flac", ".aac", ".alac", ".wav", ".aiff", ".ogg", ".opus", ".ape"
}

# Default initial categories (User can add/remove later via DB)
DEFAULT_CATEGORIES: List[str] = [
    "Romantic", "Heartbreak", "Chill", "Night Drive", "Workout", "Party",
    "Punjabi", "Rap", "English", "Bollywood", "Devotional", "Others"
]

ALLOWED_FOLDERS = DEFAULT_CATEGORIES

class ConfigManager:
    """Manages application configurations and user settings persisted in JSON."""
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load_settings()

    def load_settings(self):
        if SETTINGS_FILE_PATH.exists():
            try:
                with open(SETTINGS_FILE_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.settings.update(saved)
            except Exception:
                pass  # Fallback to defaults

    def save_settings(self):
        try:
            with open(SETTINGS_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        self.settings[key] = value
        self.save_settings()

# Global config instance
config = ConfigManager()

CHECKPOINT_FILE_NAME = ".musicsort_progress.json"
