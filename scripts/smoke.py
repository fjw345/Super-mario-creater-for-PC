"""Headless smoke test: python scripts/smoke.py

Starts every state under the dummy video driver and runs CustomLevel for a few
hundred frames on valid, broken, short and unknown-tile levels.
"""
import json
import os
import sys
import tempfile

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame as pg  # noqa: E402
from data import constants as c  # noqa: E402
from data import main as game_main, setup, storage  # noqa: E402
from data.states.custom_level import CustomLevel  # noqa: E402
from data.states.level_select import LevelSelect  # noqa: E402
from data.states.level_editor import LevelEditor  # noqa: E402


def make_tiles(rows=13, width=30, flag=True, tile='ground'):
    t = [['empty'] * width for _ in range(rows)]
    for x in range(width):
        t[rows - 1][x] = tile
    if flag and rows > 4:
        t[rows - 3][width - 8] = 'flag'
    return t


def new_persist():
    return {c.LANGUAGE: 'zh', c.LIVES: 3, c.TOP_SCORE: 0, c.SCORE: 0,
            c.COIN_TOTAL: 0, c.MARIO_DEAD: False, c.CURRENT_TIME: 0,
            c.LEVEL_STATE: c.NOT_FROZEN, c.CAMERA_START_X: 0,
            c.CUSTOM_LEVEL_RETURN: c.MAIN_MENU}


def run_state(state, persist, frames, label):
    state.startup(0, persist)
    keys = pg.key.get_pressed()
    t = 0
    for _ in range(frames):
        t += 16
        state.update(setup.SCREEN, keys, t)
        if state.done:
            break
    print('ok  ', label, 'next=%s' % getattr(state, 'next', None))


def main():
    game_main.main  # import check only
    with tempfile.TemporaryDirectory() as tmp:
        cases = {
            'valid': make_tiles(),
            'short_rows': make_tiles(rows=3, flag=False),
            'unknown_tile': make_tiles(tile='bogus'),
            'all_tiles': [['empty'] * 12 for _ in range(13)],
        }
        row = cases['all_tiles'][12]
        for i, tile in enumerate(['ground', 'brick', 'coin_box', 'pipe',
                                  'goomba', 'koopa', 'coin', 'mushroom_tile',
                                  'fireflower_tile']):
            row[i] = tile if tile != 'pipe' else 'ground'
        cases['all_tiles'][10][10] = 'flag'
        for name, tiles in cases.items():
            p = os.path.join(tmp, name + '.json')
            with open(p, 'w', encoding='utf-8') as f:
                json.dump({'name': name, 'tiles': tiles}, f)
            persist = new_persist()
            persist['custom_level_path'] = p
            run_state(CustomLevel(), persist, 300, 'CustomLevel ' + name)

        broken = os.path.join(tmp, 'broken.json')
        with open(broken, 'w') as f:
            f.write('{oops')
        persist = new_persist()
        persist['custom_level_path'] = broken
        st = CustomLevel()
        run_state(st, persist, 5, 'CustomLevel broken')
        assert st.done and persist.get('level_error'), 'broken level must exit'

    for cls in (LevelSelect, LevelEditor):
        run_state(cls(), new_persist(), 30, cls.__name__)
    print('smoke passed')


if __name__ == '__main__':
    main()
