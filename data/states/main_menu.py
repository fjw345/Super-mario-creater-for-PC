__author__ = 'justinarmstrong'

import pygame as pg
import os
from .. import setup, tools
from .. import constants as c
from .. components import info, mario


class Menu(tools._State):
    def __init__(self):
        """Initializes the state"""
        tools._State.__init__(self)
        persist = {c.COIN_TOTAL: 0,
                   c.SCORE: 0,
                   c.LIVES: 3,
                   c.TOP_SCORE: 0,
                   c.CURRENT_TIME: 0.0,
                   c.LEVEL_STATE: None,
                   c.CAMERA_START_X: 0,
                   c.MARIO_DEAD: False,
                   c.LANGUAGE: 'zh'}
        self.startup(0.0, persist)

    def startup(self, current_time, persist):
        """Called every time the game's state becomes this one.  Initializes
        certain values"""
        self.next = c.LOAD_SCREEN
        self.persist = persist
        self.game_info = persist
        self.overhead_info = info.OverheadInfo(self.game_info, c.MAIN_MENU)

        self.sprite_sheet = setup.GFX['title_screen']
        self.setup_background()
        self.setup_mario()
        self.setup_fonts()
        self.setup_cursor()
        self.setup_menu_text()
        self.lang_key_pressed = False
        self.wait_for_confirm_release = True


    def setup_fonts(self):
        """Setup fonts for multilingual UI."""
        self.font = self.load_font(32)
        self.hint_font = self.load_font(24)


    def load_font(self, size):
        """Load a compatible font with fallback to pygame default."""
        windows_font_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
        for filename in ('msyh.ttc', 'msyhbd.ttc', 'simhei.ttf', 'arial.ttf'):
            font_path = os.path.join(windows_font_dir, filename)
            if os.path.isfile(font_path):
                return pg.font.Font(font_path, size)
        return pg.font.Font(None, size)


    def setup_cursor(self):
        """Creates the mushroom cursor to select menu option"""
        self.cursor = pg.sprite.Sprite()
        dest = (160, 318)
        self.cursor.image, self.cursor.rect = self.get_image(
            24, 160, 8, 8, dest, setup.GFX['item_objects'])
        self.cursor.state = c.CREATE_LEVEL
        self.menu_options = [c.CREATE_LEVEL, c.PLAY_LEVEL, c.PLAY_1_1]
        self.cursor_index = 0
        self.cursor_positions = [318, 358, 398]
        self.key_pressed = False


    def setup_menu_text(self):
        """Setup menu text options"""
        language = self.game_info.get(c.LANGUAGE, 'zh')
        if language == 'zh':
            texts = ['创建关卡', '游玩自定义关卡', '游玩世界 1-1']
            self.lang_hint = '按 L 切换中文/English'
        else:
            texts = ['CREATE LEVEL', 'PLAY CUSTOM LEVEL', 'PLAY WORLD 1-1']
            self.lang_hint = 'Press L to switch English/中文'

        self.menu_texts = []
        y_positions = [320, 360, 400]

        for i, text in enumerate(texts):
            text_surface = self.font.render(text, True, c.WHITE)
            text_rect = text_surface.get_rect()
            text_rect.x = 220
            text_rect.y = y_positions[i]
            self.menu_texts.append((text_surface, text_rect))


    def setup_mario(self):
        """Places Mario at the beginning of the level"""
        self.mario = mario.Mario()
        self.mario.rect.x = 110
        self.mario.rect.bottom = c.GROUND_HEIGHT


    def setup_background(self):
        """Setup the background image to blit"""
        self.background = setup.GFX['level_1']
        self.background_rect = self.background.get_rect()
        self.background = pg.transform.scale(self.background,
                                   (int(self.background_rect.width*c.BACKGROUND_MULTIPLER),
                                    int(self.background_rect.height*c.BACKGROUND_MULTIPLER)))
        self.viewport = setup.SCREEN.get_rect(bottom=setup.SCREEN_RECT.bottom)

        self.image_dict = {}
        self.image_dict['GAME_NAME_BOX'] = self.get_image(
            1, 60, 176, 88, (170, 100), setup.GFX['title_screen'])



    def get_image(self, x, y, width, height, dest, sprite_sheet):
        """Returns images and rects to blit onto the screen"""
        image = pg.Surface([width, height])
        rect = image.get_rect()

        image.blit(sprite_sheet, (0, 0), (x, y, width, height))
        if sprite_sheet == setup.GFX['title_screen']:
            image.set_colorkey((255, 0, 220))
            image = pg.transform.scale(image,
                                   (int(rect.width*c.SIZE_MULTIPLIER),
                                    int(rect.height*c.SIZE_MULTIPLIER)))
        else:
            image.set_colorkey(c.BLACK)
            image = pg.transform.scale(image,
                                   (int(rect.width*3),
                                    int(rect.height*3)))

        rect = image.get_rect()
        rect.x = dest[0]
        rect.y = dest[1]
        return (image, rect)


    def update(self, surface, keys, current_time):
        """Updates the state every refresh"""
        self.current_time = current_time
        self.game_info[c.CURRENT_TIME] = self.current_time
        self.update_language(keys)
        self.update_cursor(keys)
        self.overhead_info.update(self.game_info)

        surface.blit(self.background, self.viewport, self.viewport)
        surface.blit(self.image_dict['GAME_NAME_BOX'][0],
                     self.image_dict['GAME_NAME_BOX'][1])
        surface.blit(self.mario.image, self.mario.rect)
        surface.blit(self.cursor.image, self.cursor.rect)
        
        # Draw menu text
        for text_surface, text_rect in self.menu_texts:
            surface.blit(text_surface, text_rect)

        hint = self.hint_font.render(self.lang_hint, True, c.WHITE)
        hint_rect = hint.get_rect(centerx=c.SCREEN_WIDTH // 2, y=500)
        surface.blit(hint, hint_rect)


    def update_language(self, keys):
        """Toggle language between Chinese and English."""
        if keys[pg.K_l] and not self.lang_key_pressed:
            current = self.game_info.get(c.LANGUAGE, 'zh')
            self.game_info[c.LANGUAGE] = 'en' if current == 'zh' else 'zh'
            self.setup_menu_text()
            self.lang_key_pressed = True
        elif not keys[pg.K_l]:
            self.lang_key_pressed = False


    def update_cursor(self, keys):
        """Update the position of the cursor"""
        input_list = [pg.K_RETURN, pg.K_k, pg.K_j]

        if self.wait_for_confirm_release:
            if not any(keys[k] for k in input_list):
                self.wait_for_confirm_release = False
            return

        if keys[pg.K_DOWN] and not self.key_pressed:
            self.cursor_index = (self.cursor_index + 1) % len(self.menu_options)
            self.cursor.state = self.menu_options[self.cursor_index]
            self.cursor.rect.y = self.cursor_positions[self.cursor_index]
            self.key_pressed = True
        elif keys[pg.K_UP] and not self.key_pressed:
            self.cursor_index = (self.cursor_index - 1) % len(self.menu_options)
            self.cursor.state = self.menu_options[self.cursor_index]
            self.cursor.rect.y = self.cursor_positions[self.cursor_index]
            self.key_pressed = True
        elif not keys[pg.K_DOWN] and not keys[pg.K_UP]:
            self.key_pressed = False

        for input_key in input_list:
            if keys[input_key]:
                self.reset_game_info()
                if self.cursor.state == c.CREATE_LEVEL:
                    self.next = c.LEVEL_EDITOR
                elif self.cursor.state == c.PLAY_LEVEL:
                    self.next = c.LEVEL_SELECT
                elif self.cursor.state == c.PLAY_1_1:
                    self.next = c.LOAD_SCREEN
                self.done = True


    def reset_game_info(self):
        """Resets the game info in case of a Game Over and restart"""
        self.game_info[c.COIN_TOTAL] = 0
        self.game_info[c.SCORE] = 0
        self.game_info[c.LIVES] = 3
        self.game_info[c.CURRENT_TIME] = 0.0
        self.game_info[c.LEVEL_STATE] = None

        self.persist = self.game_info
















