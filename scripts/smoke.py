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


def start_level(tmp, tiles, **extra):
    p = os.path.join(tmp, 'b.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump({'name': 'b', 'tiles': tiles}, f)
    persist = new_persist()
    persist['custom_level_path'] = p
    persist.update(extra)
    st = CustomLevel()
    st.startup(0, persist)
    return st, persist


def tick(st, n=1, keys=None):
    keys = keys or pg.key.get_pressed()
    for _ in range(n):
        st.current_time += 16
        st.update(setup.SCREEN, keys, st.current_time)
        if st.done:  # Control flips state before the next update
            break


def check_behaviors(tmp):
    # Death from the list: life lost, resume through the load screen.
    tiles = make_tiles()
    for x in range(5, 12):
        tiles[12][x] = 'empty'
    st, persist = start_level(tmp, tiles)
    st.current_time = 0
    st.mario.rect.top = c.SCREEN_HEIGHT + 5
    tick(st, 2)
    assert st.mario.dead and st.state == c.FROZEN and st.mario.x_vel == 0
    persist[c.SCORE] = 4321
    tick(st, 200)
    assert st.done and st.next == c.LOAD_SCREEN, st.next
    assert persist[c.LIVES] == 2 and persist[c.TOP_SCORE] == 4321
    assert persist['resume_custom_level']
    from data.states.load_screen import LoadScreen
    ls = LoadScreen()
    ls.startup(0, persist)
    assert ls.next == c.CUSTOM_LEVEL

    # Last life: game over, and no resume flag left behind.
    st, persist = start_level(tmp, tiles)
    persist[c.LIVES] = 1
    st.mario.rect.top = c.SCREEN_HEIGHT + 5
    tick(st, 200)
    assert st.next == c.GAME_OVER and not persist.get('resume_custom_level')

    # From the editor: returns to the editor, lives untouched.
    st, persist = start_level(tmp, tiles, **{c.CUSTOM_LEVEL_RETURN: c.LEVEL_EDITOR})
    st.mario.rect.top = c.SCREEN_HEIGHT + 5
    tick(st, 200)
    assert st.next == c.LEVEL_EDITOR and persist[c.LIVES] == 3

    # Enemies only join once the camera's right edge reaches them.
    tiles = make_tiles(width=60)
    tiles[11][50] = 'goomba'
    st, _ = start_level(tmp, tiles)
    assert len(st.enemy_group) == 0 and len(st.pending_enemies) == 1
    st.viewport.x = 50 * 43 - 800 + 10
    tick(st, 1)
    assert len(st.enemy_group) == 1 and not st.pending_enemies

    # Bumping a coin box from below scores 200 and a coin.
    tiles = make_tiles(width=30)
    tiles[8][3] = 'coin'
    st, persist = start_level(tmp, tiles)
    box = list(st.coin_box_group)[0]
    st.mario.rect.centerx = box.rect.centerx
    st.mario.rect.top = box.rect.bottom - 3
    st.mario.y_vel = -8
    st.mario.state = c.JUMP
    st.mario.big = False
    st.check_mario_y_collisions()
    assert persist[c.SCORE] == 200 and persist[c.COIN_TOTAL] == 1, persist
    assert st.mario.y_vel == 7

    # Stomping a goomba from above works on the y axis in one frame.
    tiles = make_tiles(width=30)
    st, persist = start_level(tmp, tiles)
    from data.components import enemies
    g = enemies.Goomba()
    g.rect.x = 300
    g.rect.bottom = c.GROUND_HEIGHT
    st.enemy_group.add(g)
    st.mario_and_enemy_group.add(g)
    st.mario.rect.centerx = g.rect.centerx
    st.mario.rect.bottom = g.rect.top + 4
    st.mario.y_vel = 5
    st.check_mario_y_collisions()
    assert persist[c.SCORE] == 100 and st.mario.y_vel == -7 \
        and g not in st.enemy_group and g in st.sprites_about_to_die_group

    # Flag score uses the pole bottom, so a raised pole scores the same.
    for lift in (0, 3):
        tiles = make_tiles(width=30)
        for x in range(30):
            tiles[12 - lift][x] = 'ground' if lift else tiles[12][x]
        tiles[9 - lift][15] = 'flag'
        st, _ = start_level(tmp, tiles)
        st.mario.rect.bottom = st.flag_ground_y - 10
        st.flag.rect.x += 0
        st.create_flag_points(st.flag.rect.x + 13, st.flag_ground_y)
        assert st.flag_score_total == 100, (lift, st.flag_score_total)

    # Enemies turn around at a brick/box one tile higher instead of climbing it.
    for kind in ('brick', 'coin_box'):
        tiles = make_tiles(width=50)
        for x in range(50):
            tiles[11][x] = tiles[12][x] = 'ground'
        tiles[10][12] = tiles[9][12] = 'ground'
        tiles[10][20] = kind
        tiles[10][14] = 'goomba'
        st, _ = start_level(tmp, tiles)
        st.viewport.x = 10 * 43
        tick(st, 1)
        enemy = list(st.enemy_group)[0]
        lowest = 10 ** 9
        for _ in range(400):
            tick(st, 1)
            lowest = min(lowest, enemy.rect.bottom)
        floor = 11 * 43 + 70  # top of the ground row the enemy walks on
        assert lowest >= floor, (kind, lowest, floor)

    # A second run of the state does not see the previous level's flag.
    tiles = make_tiles(flag=False)
    st2, _ = start_level(tmp, tiles)
    assert st2.flag is None
    print('ok   behaviours')


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

        check_behaviors(tmp)

    for cls in (LevelSelect, LevelEditor):
        run_state(cls(), new_persist(), 30, cls.__name__)
    print('smoke passed')


if __name__ == '__main__':
    main()
