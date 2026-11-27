"""Deterministic gameplay trace, used to prove refactors change no behaviour.

  python scripts/trace.py record <file>    # write per-frame hashes
  python scripts/trace.py compare <file>   # compare against a recording

Runs 1-1 and a custom level with scripted input in the dummy video driver and
hashes the observable state of every frame (Mario, enemies, shells, powerups,
blocks, score, camera).
"""
import hashlib
import json
import os
import sys
import tempfile

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame as pg  # noqa: E402
from data import constants as c, setup, tools  # noqa: E402
from data.states.level1 import Level1  # noqa: E402
from data.states.custom_level import CustomLevel  # noqa: E402

FRAMES = 1200


class Keys(object):
    def __init__(self, held):
        self.held = held

    def __getitem__(self, key):
        return key in self.held


def scripted_keys(frame, jump_every, fire_every, run):
    held = set()
    held.add(tools.keybinding['right'])
    if (frame % jump_every) < 14:
        held.add(tools.keybinding['jump'])
    if run and (frame % fire_every) < 6:
        held.add(tools.keybinding['action'])
    return Keys(held)


def sprite_state(group):
    return sorted((s.rect.x, s.rect.y, str(getattr(s, 'state', '')),
                   getattr(s, 'x_vel', 0), getattr(s, 'y_vel', 0))
                  for s in group)


def snapshot(st):
    m = st.mario
    data = [m.rect.x, m.rect.y, str(m.state), m.x_vel, m.y_vel, m.big, m.fire,
            m.invincible, m.dead, st.game_info[c.SCORE],
            st.game_info[c.COIN_TOTAL], st.game_info[c.LIVES], str(st.state),
            round(st.viewport.x, 3), st.done, str(getattr(st, 'next', None)),
            sprite_state(st.enemy_group), sprite_state(st.shell_group),
            sprite_state(st.powerup_group), sprite_state(st.brick_group),
            sprite_state(st.coin_box_group), sprite_state(st.brick_pieces_group),
            sprite_state(st.sprites_about_to_die_group),
            len(st.moving_score_list), len(st.coin_group),
            st.flag_score_total]
    return hashlib.md5(json.dumps(data, default=str).encode()).hexdigest()


def custom_tiles():
    width = 90
    t = [['empty'] * width for _ in range(13)]
    for x in range(width):
        t[11][x] = t[12][x] = 'ground'
    for x in (30, 31):
        t[11][x] = t[12][x] = 'empty'      # a pit
    t[8][8], t[8][9], t[8][10] = 'brick', 'coin_box', 'brick'
    t[8][11], t[8][12] = 'coin', 'brick'
    t[8][13] = 'brick'
    t[10][16] = 'pipe'
    t[10][22], t[10][24] = 'goomba', 'koopa'
    t[10][26] = 'goomba'
    t[10][34], t[10][36] = 'goomba', 'koopa'
    t[10][40] = 'mushroom_tile'
    t[10][44] = 'fireflower_tile'
    for i, x in enumerate(range(48, 52)):
        t[10 - i][x] = 'ground'
    t[7][56], t[7][57] = 'coin_box', 'brick'
    t[10][60], t[10][62] = 'koopa', 'goomba'
    t[10][70] = 'flag'
    return t


def run_one(label, make_state, start_x, jump_every, fire_every, run, power=0):
    st = make_state()
    if power:
        st.mario.become_big()
        st.mario.fire = power == 2
    if start_x:
        st.mario.rect.x = start_x
        st.viewport.x = max(0, start_x - 110)
    hashes = []
    t = 0
    for frame in range(FRAMES):
        t += 16
        st.update(setup.SCREEN, scripted_keys(frame, jump_every, fire_every, run), t)
        hashes.append(snapshot(st))
        if st.done:
            break
    return label, hashes


def new_persist():
    return {c.LANGUAGE: 'zh', c.LIVES: 3, c.TOP_SCORE: 0, c.SCORE: 0,
            c.COIN_TOTAL: 0, c.MARIO_DEAD: False, c.CURRENT_TIME: 0,
            c.LEVEL_STATE: c.NOT_FROZEN, c.CAMERA_START_X: 0,
            c.CUSTOM_LEVEL_RETURN: c.MAIN_MENU}


def build_runs(tmp):
    path = os.path.join(tmp, 'trace.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'name': 'trace', 'tiles': custom_tiles()}, f)

    def level1():
        st = Level1()
        st.startup(0, new_persist())
        return st

    def custom():
        p = new_persist()
        p['custom_level_path'] = path
        st = CustomLevel()
        st.startup(0, p)
        return st

    # (start_x, jump_every, fire_every, hold_action, power 0/1/2)
    runs = []
    for i, args in enumerate([(0, 53, 31, True, 0), (0, 37, 23, True, 0),
                              (2300, 61, 29, True, 0), (5600, 45, 41, False, 0),
                              (8300, 70, 33, True, 0),
                              (700, 47, 17, True, 1), (3200, 43, 13, True, 2),
                              (4200, 39, 19, True, 2), (6500, 51, 15, True, 1)]):
        runs.append(('level1-%d' % i, level1) + args)
    for i, args in enumerate([(0, 53, 31, True, 0), (0, 37, 23, True, 0),
                              (0, 29, 19, True, 0), (0, 61, 37, False, 0),
                              (1500, 45, 27, True, 0),
                              (0, 41, 17, True, 1), (0, 33, 11, True, 2),
                              (700, 57, 13, True, 2), (1900, 49, 21, True, 1)]):
        runs.append(('custom-%d' % i, custom) + args)
    return runs


def main():
    mode, path = sys.argv[1], sys.argv[2]
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for label, make, sx, je, fe, run, power in build_runs(tmp):
            name, hashes = run_one(label, make, sx, je, fe, run, power)
            results[name] = hashes
            print('%-10s %4d frames  %s' % (name, len(hashes),
                  hashlib.md5(''.join(hashes).encode()).hexdigest()[:10]))
    if mode == 'record':
        with open(path, 'w') as f:
            json.dump(results, f)
        print('recorded', path)
        return
    with open(path) as f:
        base = json.load(f)
    bad = 0
    for name, hashes in results.items():
        old = base.get(name)
        if old == hashes:
            continue
        bad += 1
        first = next((i for i, (a, b) in enumerate(zip(old or [], hashes))
                      if a != b), min(len(old or []), len(hashes)))
        print('DIFFERS %s: first different frame %d' % (name, first))
    if bad:
        sys.exit(1)
    print('IDENTICAL to recording (%d runs)' % len(results))


if __name__ == '__main__':
    main()
