import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import storage  # noqa: E402
from data import constants as c  # noqa: E402


def grid(w=5, h=13, fill=c.TILE_EMPTY):
    return [[fill] * w for _ in range(h)]


@pytest.mark.parametrize('raw,expected', [
    ('abc', 'abc'),
    ('a<b>c:d"e/f\\g|h?i*j', 'abcdefghij'),
    ('  name. ', 'name'),
    ('...', ''),
    ('CON', ''),
    ('con', ''),
    ('NUL.txt', ''),
    ('COM1', ''),
    ('LPT9', ''),
    ('COM10', 'COM10'),
    ('x' * 40, 'x' * 32),
    ('a' * 31 + ' b', 'a' * 31),
    ('a' * 31 + '.b', 'a' * 31),
    ('关卡 一', '关卡 一'),
])
def test_sanitize_name(raw, expected):
    assert storage.sanitize_name(raw) == expected


def test_save_and_load_roundtrip(tmp_path):
    tiles = grid()
    tiles[12][0] = c.TILE_GROUND
    path = storage.save_level('lv', tiles, str(tmp_path))
    assert os.path.basename(path) == 'lv.json'
    assert not (tmp_path / 'lv.json.tmp').exists()
    level = storage.load_level(path)
    assert level['tiles'] == tiles
    assert level['version'] == 1
    assert level['unknown_tiles'] == 0


def test_save_overwrite_is_atomic_on_failure(tmp_path):
    storage.save_level('lv', grid(), str(tmp_path))
    with pytest.raises(storage.LevelSaveError):
        storage.save_level('lv', [[object()]], str(tmp_path))
    assert not (tmp_path / 'lv.json.tmp').exists()
    assert storage.load_level(str(tmp_path / 'lv.json'))['width'] == 5


def test_save_rejects_bad_name(tmp_path):
    with pytest.raises(storage.LevelSaveError):
        storage.save_level('CON', grid(), str(tmp_path))


def test_level_exists(tmp_path):
    storage.save_level('lv', grid(), str(tmp_path))
    assert storage.level_exists('lv', str(tmp_path))
    assert not storage.level_exists('other', str(tmp_path))


def write(tmp_path, data, name='x.json'):
    p = tmp_path / name
    p.write_text(data if isinstance(data, str) else json.dumps(data),
                 encoding='utf-8')
    return str(p)


def test_normalize_pads_rows_and_ragged_width(tmp_path):
    p = write(tmp_path, {'tiles': [['ground'], ['ground', 'brick', 'flag']],
                         'width': 999, 'tile_size': 0})
    level = storage.load_level(p)
    assert level['height'] == 13 and len(level['tiles']) == 13
    assert level['width'] == 3
    assert all(len(r) == 3 for r in level['tiles'])
    assert level['tile_size'] == 43
    assert level['name'] == 'x'


def test_normalize_crops(tmp_path):
    p = write(tmp_path, {'tiles': grid(2000, 20)})
    level = storage.load_level(p)
    assert level['width'] == 1000 and len(level['tiles']) == 13


def test_unknown_tiles_become_empty(tmp_path):
    p = write(tmp_path, {'tiles': [['ground', 'bogus', 5, None]]})
    level = storage.load_level(p)
    assert level['tiles'][0] == ['ground', 'empty', 'empty', 'empty']
    assert level['unknown_tiles'] == 3


@pytest.mark.parametrize('data', [
    '{not json', '[]', {'tiles': 'x'}, {'tiles': []}, {'tiles': [1, 2]},
    {'tiles': [[]]}, {},
])
def test_invalid_files_raise(tmp_path, data):
    with pytest.raises(storage.LevelLoadError):
        storage.load_level(write(tmp_path, data))


def test_missing_file_raises(tmp_path):
    with pytest.raises(storage.LevelLoadError):
        storage.load_level(str(tmp_path / 'nope.json'))


def test_list_levels_marks_broken(tmp_path):
    storage.save_level('good', grid(), str(tmp_path))
    write(tmp_path, '{bad', 'broken.json')
    items = {os.path.basename(p): (ok, b) for p, _, ok, b in
             storage.list_levels(str(tmp_path))}
    assert items == {'good.json': (True, False), 'broken.json': (False, False)}


def test_delete_only_inside_dir(tmp_path):
    save = tmp_path / 'saves'
    save.mkdir()
    other = tmp_path / 'other.json'
    other.write_text('{}')
    p = storage.save_level('lv', grid(), str(save))
    storage.delete_level(p, str(save))
    assert not os.path.exists(p)
    with pytest.raises(PermissionError):
        storage.delete_level(str(other), str(save))
    assert other.exists()


def test_builtin_cannot_be_deleted(tmp_path):
    builtin = storage.builtin_levels()
    assert builtin and all(b for *_, b in builtin)
    with pytest.raises(PermissionError):
        storage.delete_level(builtin[0][0], str(tmp_path))


def test_builtin_example_loads():
    for path, _, ok, _ in storage.builtin_levels():
        assert ok
        storage.load_level(path)


def test_migration(tmp_path):
    old1 = tmp_path / 'old1'
    old2 = tmp_path / 'old2'
    dest = tmp_path / 'dest'
    for d in (old1, old2, dest):
        d.mkdir()
    (old1 / 'a.json').write_text('A')
    (old1 / 'b.json').write_text('B1')
    (old2 / 'b.json').write_text('B2')
    (old2 / 'c.txt').write_text('ignored')
    (dest / 'a.json').write_text('KEEP')

    n = storage.migrate_legacy_levels(str(dest), [str(old1), str(old2)])
    assert n == 1
    assert (dest / 'a.json').read_text() == 'KEEP'
    assert (dest / 'b.json').read_text() == 'B1'
    assert not (dest / 'c.txt').exists()
    assert (old1 / 'a.json').exists() and (old2 / 'b.json').exists()

    (old1 / 'new.json').write_text('N')
    assert storage.migrate_legacy_levels(str(dest), [str(old1)]) == 0
    assert not (dest / 'new.json').exists()


def test_frozen_dir_uses_appdata(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setenv('APPDATA', str(tmp_path))
    monkeypatch.setattr(storage, 'legacy_dirs', lambda: [])
    d = storage.levels_dir()
    assert d == str(tmp_path / 'SuperMarioCreater' / 'custom_levels')
    assert os.path.isdir(d)


def test_tile_table_is_consistent():
    from data import tiles
    ids = [t.id for t in tiles.TILES]
    assert len(ids) == len(set(ids)) == 10
    assert set(ids) <= storage.KNOWN_TILES
    assert storage.KNOWN_TILES - set(ids) == {c.TILE_EMPTY}
    assert all(t.zh and t.en for t in tiles.TILES)
    assert tiles.display_name('nope', 'en') == 'NOPE'


def test_every_tile_has_a_runtime_creator():
    pytest.importorskip('pygame')
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    from data import tiles
    from data.states.custom_level import CustomLevel
    assert set(CustomLevel.TILE_CREATORS) == {t.id for t in tiles.TILES}
