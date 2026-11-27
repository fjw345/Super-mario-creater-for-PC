"""Custom level storage: paths, listing, loading, saving and deleting.

This module is pure Python (no pygame) so it can be tested without a window.
"""

import json
import os
import re
import shutil
import sys

from . import constants as c

APP_DIR_NAME = 'SuperMarioCreater'
MIGRATION_MARKER = '.migrated_v1'
LEVEL_VERSION = 1
GRID_HEIGHT = 13
MAX_WIDTH = 1000
TILE_SIZE = 43
MAX_NAME_LEN = 32

RESERVED_NAMES = {'CON', 'PRN', 'AUX', 'NUL'}
RESERVED_NAMES.update('COM%d' % i for i in range(1, 10))
RESERVED_NAMES.update('LPT%d' % i for i in range(1, 10))

KNOWN_TILES = {
    c.TILE_GROUND, c.TILE_BRICK, c.TILE_COIN_BOX, c.TILE_PIPE, c.TILE_GOOMBA,
    c.TILE_KOOPA, c.TILE_COIN, c.TILE_FLAG, c.TILE_MUSHROOM,
    c.TILE_FIREFLOWER, c.TILE_EMPTY,
}


class LevelLoadError(Exception):
    """Raised when a level file cannot be read or is not a valid level."""


class LevelSaveError(Exception):
    """Raised when a level file cannot be written."""


def is_frozen():
    return bool(getattr(sys, 'frozen', False))


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_base_dir():
    """Directory holding read-only resources (`_internal/` when packaged)."""
    return _repo_root()


def _user_data_dir():
    appdata = os.environ.get('APPDATA')
    if appdata:
        return os.path.join(appdata, APP_DIR_NAME, 'custom_levels')
    return os.path.join(os.path.expanduser('~'), '.supermariocreater',
                        'custom_levels')


def levels_dir():
    """Return the writable save directory, creating it if needed."""
    if is_frozen():
        path = _user_data_dir()
    else:
        path = os.path.join(_repo_root(), 'custom_levels')
    os.makedirs(path, exist_ok=True)
    if is_frozen():
        migrate_legacy_levels(path)
    return path


def builtin_dir():
    return os.path.join(resource_base_dir(), 'levels')


def legacy_dirs():
    """Old save locations used by packaged v1.0."""
    dirs = [os.path.join(resource_base_dir(), 'custom_levels')]
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    dirs.append(os.path.join(exe_dir, 'custom_levels'))
    return dirs


def migrate_legacy_levels(dest_dir, sources=None):
    """Copy JSON files from old locations into dest_dir. Never deletes.

    Returns the number of files copied. Writes a marker so it runs once.
    """
    marker = os.path.join(dest_dir, MIGRATION_MARKER)
    if os.path.exists(marker):
        return 0
    copied = 0
    dest_abs = os.path.abspath(dest_dir)
    for src in (sources if sources is not None else legacy_dirs()):
        if os.path.abspath(src) == dest_abs or not os.path.isdir(src):
            continue
        try:
            names = sorted(os.listdir(src))
        except OSError:
            continue
        for fname in names:
            if not fname.lower().endswith('.json'):
                continue
            target = os.path.join(dest_dir, fname)
            if os.path.exists(target):
                continue
            try:
                shutil.copy2(os.path.join(src, fname), target)
                copied += 1
            except OSError:
                pass
    try:
        with open(marker, 'w', encoding='utf-8') as f:
            f.write('1')
    except OSError:
        pass
    return copied


def sanitize_name(raw):
    """Return a safe file name without extension ('' if nothing usable)."""
    invalid = '<>:"/\\|?*'
    name = ''.join(ch for ch in raw
                   if ch not in invalid and ord(ch) >= 32)
    name = name.strip().strip('.')
    name = name[:MAX_NAME_LEN].strip().strip('.')
    if not name:
        return ''
    stem = name.split('.')[0].strip().upper()
    if stem in RESERVED_NAMES:
        return ''
    return name


def _path_for(name, directory=None):
    return os.path.join(directory or levels_dir(), name + '.json')


def level_exists(name, directory=None):
    safe = sanitize_name(name)
    return bool(safe) and os.path.exists(_path_for(safe, directory))


def normalize_level(data):
    """Validate and normalize parsed JSON. Returns (level_dict, unknown_count)."""
    if not isinstance(data, dict):
        raise LevelLoadError('not a level object')
    tiles = data.get('tiles')
    if (not isinstance(tiles, list) or not tiles
            or not all(isinstance(row, list) for row in tiles)):
        raise LevelLoadError('tiles must be a 2D list')

    width = max(len(row) for row in tiles)
    if width < 1:
        raise LevelLoadError('level has no columns')
    width = min(width, MAX_WIDTH)

    unknown = 0
    rows = []
    for row in tiles[:GRID_HEIGHT]:
        new_row = []
        for tile in row[:width]:
            if isinstance(tile, str) and tile in KNOWN_TILES:
                new_row.append(tile)
            else:
                new_row.append(c.TILE_EMPTY)
                unknown += 1
        new_row.extend([c.TILE_EMPTY] * (width - len(new_row)))
        rows.append(new_row)
    while len(rows) < GRID_HEIGHT:
        rows.append([c.TILE_EMPTY] * width)

    name = data.get('name')
    level = {
        'version': LEVEL_VERSION,
        'name': name if isinstance(name, str) else '',
        'width': width,
        'height': GRID_HEIGHT,
        'tile_size': TILE_SIZE,
        'tiles': rows,
    }
    return level, unknown


def load_level(path):
    """Read, validate and normalize a level file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        raise LevelLoadError(str(exc))
    level, unknown = normalize_level(data)
    level['unknown_tiles'] = unknown
    if not level['name']:
        level['name'] = os.path.splitext(os.path.basename(path))[0]
    return level


def save_level(name, tiles, directory=None):
    """Atomically write a level. Returns the file path."""
    safe = sanitize_name(name)
    if not safe:
        raise LevelSaveError('invalid name')
    directory = directory or levels_dir()
    path = _path_for(safe, directory)
    tmp = path + '.tmp'
    data = {
        'version': LEVEL_VERSION,
        'name': safe,
        'width': len(tiles[0]) if tiles else 0,
        'height': len(tiles),
        'tile_size': TILE_SIZE,
        'tiles': tiles,
    }
    try:
        os.makedirs(directory, exist_ok=True)
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except (OSError, TypeError, ValueError) as exc:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise LevelSaveError(str(exc))
    return path


def _list_dir(directory, builtin):
    result = []
    if not os.path.isdir(directory):
        return result
    for fname in sorted(os.listdir(directory)):
        if not fname.lower().endswith('.json'):
            continue
        path = os.path.join(directory, fname)
        try:
            level = load_level(path)
            name, ok = level['name'], True
        except LevelLoadError:
            name, ok = fname[:-5], False
        result.append((path, name, ok, builtin))
    return result


def builtin_levels():
    return _list_dir(builtin_dir(), True)


def list_levels(directory=None):
    """Return [(path, name, ok, builtin)] for saves followed by built-ins."""
    saves = _list_dir(directory or levels_dir(), False)
    if directory is None:
        return saves + builtin_levels()
    return saves


def delete_level(path, directory=None):
    """Delete a save. Refuses files outside the save directory."""
    directory = os.path.abspath(directory or levels_dir())
    target = os.path.abspath(path)
    if os.path.dirname(target) != directory or \
            not target.lower().endswith('.json'):
        raise PermissionError('refusing to delete outside save directory')
    os.remove(target)
