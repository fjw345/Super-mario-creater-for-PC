__author__ = 'justinarmstrong'

"""
This module initializes the display and creates dictionaries of resources.
"""

import os
import pygame as pg
from . import tools
from .import constants as c

ORIGINAL_CAPTION = c.ORIGINAL_CAPTION
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCE_DIR = os.path.join(BASE_DIR, "resources")


os.environ['SDL_VIDEO_CENTERED'] = '1'
pg.init()
pg.event.set_allowed([pg.KEYDOWN, pg.KEYUP, pg.QUIT])
pg.display.set_caption(c.ORIGINAL_CAPTION)
SCREEN = pg.display.set_mode(c.SCREEN_SIZE)
SCREEN_RECT = SCREEN.get_rect()


FONTS = tools.load_all_fonts(os.path.join(RESOURCE_DIR, "fonts"))
MUSIC = tools.load_all_music(os.path.join(RESOURCE_DIR, "music"))
GFX   = tools.load_all_gfx(os.path.join(RESOURCE_DIR, "graphics"))
SFX   = tools.load_all_sfx(os.path.join(RESOURCE_DIR, "sound"))


