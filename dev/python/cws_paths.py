"""cws_paths.py - Centralized path resolution for bundled and source modes.

When running from source: data files are at the project root (../../ from here).
When running as a PyInstaller bundle: data files are in sys._MEIPASS.

Writable files (saves, config, hiscore, history) go to ~/.cws/ in frozen mode,
or to the project root in source mode.
"""

import os
import sys

# ── Base directories ─────────────────────────────────────────────────────────

if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle — read-only data extracted here
    _DATA_DIR = sys._MEIPASS
    # Writable directory for saves, config, hiscore
    _SAVE_DIR = os.path.join(os.path.expanduser("~"), ".cws")
    os.makedirs(_SAVE_DIR, exist_ok=True)
else:
    # Running from source — data files at project root (two levels up)
    _DATA_DIR = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    _SAVE_DIR = _DATA_DIR


def data_dir() -> str:
    """Return the read-only data directory."""
    return _DATA_DIR


def save_dir() -> str:
    """Return the writable directory for saves/config/hiscore."""
    return _SAVE_DIR


def data_path(filename: str) -> str:
    """Resolve a read-only data file path (case-insensitive lookup)."""
    path = os.path.join(_DATA_DIR, filename)
    if os.path.exists(path):
        return path
    target = filename.upper()
    try:
        for f in os.listdir(_DATA_DIR):
            if f.upper() == target:
                return os.path.join(_DATA_DIR, f)
    except OSError:
        pass
    return path


def save_path(filename: str) -> str:
    """Resolve a writable file path in the save directory.

    For reading: checks save_dir first, falls back to data_dir.
    For writing: always returns a path in save_dir.
    """
    # Check save dir first
    path = os.path.join(_SAVE_DIR, filename)
    if os.path.exists(path):
        return path
    # Fall back to data dir (e.g. bundled default HISCORE.CWS)
    fallback = os.path.join(_DATA_DIR, filename)
    if os.path.exists(fallback):
        return fallback
    # Case-insensitive fallback in data dir
    target = filename.upper()
    try:
        for f in os.listdir(_DATA_DIR):
            if f.upper() == target:
                return os.path.join(_DATA_DIR, f)
    except OSError:
        pass
    # Default: return save dir path (for new file creation)
    return os.path.join(_SAVE_DIR, filename)


def save_path_write(filename: str) -> str:
    """Return the writable path for a file (always in save_dir)."""
    return os.path.join(_SAVE_DIR, filename)
