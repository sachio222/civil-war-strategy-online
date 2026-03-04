"""web_paths.py — File path resolution for browser/Pyodide environment.

Replaces cws_paths.py. Data files live at /data/ in Pyodide's virtual FS.
Save files go to /saves/ (persisted to localStorage via main thread).
"""

import os

_DATA_DIR = "/data"
_SAVE_DIR = "/saves"


def data_dir():
    return _DATA_DIR


def save_dir():
    return _SAVE_DIR


def data_path(filename):
    """Resolve a read-only data file path (case-insensitive)."""
    path = os.path.join(_DATA_DIR, filename)
    if os.path.exists(path):
        return path
    # Case-insensitive search
    target = filename.upper()
    try:
        for f in os.listdir(_DATA_DIR):
            if f.upper() == target:
                return os.path.join(_DATA_DIR, f)
    except OSError:
        pass
    return path


def save_path(filename):
    """Resolve a save file path (check saves, then data, then default)."""
    path = os.path.join(_SAVE_DIR, filename)
    if os.path.exists(path):
        return path
    fallback = os.path.join(_DATA_DIR, filename)
    if os.path.exists(fallback):
        return fallback
    # Case-insensitive fallback
    target = filename.upper()
    try:
        for f in os.listdir(_DATA_DIR):
            if f.upper() == target:
                return os.path.join(_DATA_DIR, f)
    except OSError:
        pass
    return os.path.join(_SAVE_DIR, filename)


def save_path_write(filename):
    """Return the writable path for a file (always in save dir)."""
    return os.path.join(_SAVE_DIR, filename)
