"""Level Select screen for choosing custom levels to play"""

import pygame as pg
import os
import json
from .. import setup, tools
from .. import constants as c
from .. components import info


class LevelSelect(tools._State):
    """Level Select state for choosing custom levels"""
    
    def __init__(self):
        tools._State.__init__(self)
    
    def startup(self, current_time, persist):
        """Initialize the level select screen"""
        self.persist = persist
        self.game_info = persist
        if c.LANGUAGE not in self.game_info:
            self.game_info[c.LANGUAGE] = 'zh'
        self.next = c.MAIN_MENU
        
        # Setup
        self.setup_background()
        self.setup_font()
        self.load_level_list()
        self.setup_cursor()
        
        # Input handling
        self.key_pressed = False
        self.lang_key_pressed = False
        self.delete_confirm_pending = False
        self.wait_for_confirm_release = True
    
    def setup_background(self):
        """Setup the background"""
        self.background = pg.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT))
        self.background.fill(c.SKY_BLUE)
    
    def setup_font(self):
        """Setup fonts"""
        self.title_font = self.load_font(48)
        self.font = self.load_font(32)
        self.small_font = self.load_font(24)


    def load_font(self, size):
        """Load a compatible font with fallback to pygame default."""
        windows_font_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
        for filename in ('msyh.ttc', 'msyhbd.ttc', 'simhei.ttf', 'arial.ttf'):
            font_path = os.path.join(windows_font_dir, filename)
            if os.path.isfile(font_path):
                return pg.font.Font(font_path, size)
        return pg.font.Font(None, size)


    def tr(self, zh_text, en_text):
        """Translate text by current language setting."""
        return zh_text if self.game_info.get(c.LANGUAGE, 'zh') == 'zh' else en_text
    
    def load_level_list(self):
        """Load list of available custom levels"""
        self.levels_dir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(__file__))), 'custom_levels')
        
        self.level_files = []
        self.level_names = []
        
        if os.path.exists(self.levels_dir):
            for filename in sorted(os.listdir(self.levels_dir)):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.levels_dir, filename)
                    self.level_files.append(filepath)
                    
                    # Try to get level name from file
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            name = data.get('name', filename[:-5])
                    except Exception:
                        name = filename[:-5]
                    
                    self.level_names.append(name)
        
        # Add back option
        self.level_names.append('__BACK__')
        self.level_files.append(None)
    
    def setup_cursor(self):
        """Setup the cursor"""
        self.cursor = pg.sprite.Sprite()
        dest = (100, 150)
        self.cursor.image, self.cursor.rect = self.get_image(
            24, 160, 8, 8, dest, setup.GFX['item_objects'])
        
        self.cursor_index = 0
        self.max_visible = 10  # Maximum levels shown at once
        self.scroll_offset = 0
    
    def get_image(self, x, y, width, height, dest, sprite_sheet):
        """Get image from sprite sheet"""
        image = pg.Surface([width, height])
        rect = image.get_rect()
        
        image.blit(sprite_sheet, (0, 0), (x, y, width, height))
        image.set_colorkey(c.BLACK)
        image = pg.transform.scale(image, (int(rect.width * 3), int(rect.height * 3)))
        
        rect = image.get_rect()
        rect.x = dest[0]
        rect.y = dest[1]
        return (image, rect)
    
    def update(self, surface, keys, current_time):
        """Update the level select screen"""
        self.handle_input(keys)
        self.draw(surface)
    
    def handle_input(self, keys):
        """Handle keyboard input"""
        # Avoid key carry-over from previous state (main menu confirm key).
        confirm_held = keys[pg.K_RETURN] or keys[pg.K_k] or keys[pg.K_j]
        if self.wait_for_confirm_release:
            if not confirm_held:
                self.wait_for_confirm_release = False
            return

        if keys[pg.K_l] and not self.lang_key_pressed:
            current = self.game_info.get(c.LANGUAGE, 'zh')
            self.game_info[c.LANGUAGE] = 'en' if current == 'zh' else 'zh'
            self.lang_key_pressed = True
        elif not keys[pg.K_l]:
            self.lang_key_pressed = False

        if (keys[pg.K_DOWN] or keys[pg.K_s]) and not self.key_pressed:
            self.cursor_index = min(self.cursor_index + 1, len(self.level_names) - 1)
            self.delete_confirm_pending = False
            self.key_pressed = True
            self.update_scroll()
        
        elif (keys[pg.K_UP] or keys[pg.K_w]) and not self.key_pressed:
            self.cursor_index = max(self.cursor_index - 1, 0)
            self.delete_confirm_pending = False
            self.key_pressed = True
            self.update_scroll()
        
        elif (keys[pg.K_RETURN] or keys[pg.K_k]) and not self.key_pressed:
            self.key_pressed = True
            self.delete_confirm_pending = False
            self.select_level()

        elif (keys[pg.K_DELETE] or keys[pg.K_x]) and not self.key_pressed:
            self.key_pressed = True
            self.handle_delete_selected_level()
        
        elif keys[pg.K_ESCAPE] and not self.key_pressed:
            self.key_pressed = True
            if self.delete_confirm_pending:
                self.delete_confirm_pending = False
            else:
                self.done = True
        
        if not any([keys[pg.K_DOWN], keys[pg.K_s], keys[pg.K_UP], keys[pg.K_w], keys[pg.K_RETURN], 
                   keys[pg.K_k], keys[pg.K_ESCAPE], keys[pg.K_DELETE], keys[pg.K_x]]):
            self.key_pressed = False
    
    def update_scroll(self):
        """Update scroll offset based on cursor position"""
        if self.cursor_index < self.scroll_offset:
            self.scroll_offset = self.cursor_index
        elif self.cursor_index >= self.scroll_offset + self.max_visible:
            self.scroll_offset = self.cursor_index - self.max_visible + 1
    
    def select_level(self):
        """Select the current level"""
        selected_file = self.level_files[self.cursor_index]
        
        if selected_file is None:
            # Back to menu
            self.next = c.MAIN_MENU
        else:
            # Load selected level
            self.persist['custom_level_path'] = selected_file
            self.persist[c.CUSTOM_LEVEL_RETURN] = c.MAIN_MENU
            self.next = c.CUSTOM_LEVEL
        
        self.done = True


    def handle_delete_selected_level(self):
        """Delete currently selected custom level with confirmation."""
        selected_file = self.level_files[self.cursor_index]

        if selected_file is None:
            self.delete_confirm_pending = False
            return

        if not self.delete_confirm_pending:
            self.delete_confirm_pending = True
            return

        try:
            if os.path.exists(selected_file):
                os.remove(selected_file)
        except OSError:
            return

        old_index = self.cursor_index
        self.load_level_list()
        self.cursor_index = max(0, min(old_index, len(self.level_names) - 1))
        self.update_scroll()
        self.delete_confirm_pending = False
    
    def draw(self, surface):
        """Draw the level select screen"""
        # Draw background
        surface.blit(self.background, (0, 0))
        
        # Draw title
        title_text = self.title_font.render(
            self.tr('选择关卡', 'SELECT LEVEL'),
            True,
            c.WHITE)
        title_rect = title_text.get_rect(centerx=c.SCREEN_WIDTH // 2, y=50)
        surface.blit(title_text, title_rect)
        
        # Draw level list
        if len(self.level_names) == 1:
            # Only "Back to Menu" - no custom levels
            no_levels_text = self.font.render(
                self.tr('未找到自定义关卡！', 'No custom levels found!'),
                True,
                c.WHITE)
            no_levels_rect = no_levels_text.get_rect(
                centerx=c.SCREEN_WIDTH // 2, y=200)
            surface.blit(no_levels_text, no_levels_rect)
            
            hint_text = self.small_font.render(
                self.tr('请先在关卡编辑器中创建关卡', 'Create a level first in the Level Editor'),
                True,
                c.GOLD)
            hint_rect = hint_text.get_rect(centerx=c.SCREEN_WIDTH // 2, y=250)
            surface.blit(hint_text, hint_rect)
        
        # Draw visible levels
        visible_start = self.scroll_offset
        visible_end = min(visible_start + self.max_visible, len(self.level_names))
        
        for i in range(visible_start, visible_end):
            y = 150 + (i - visible_start) * 40
            
            # Highlight selected level
            if i == self.cursor_index:
                self.cursor.rect.y = y
            
            # Draw level name
            level_name = self.level_names[i]
            if level_name == '__BACK__':
                level_name = self.tr('< 返回主菜单 >', '< Back to Menu >')
            text = self.font.render(level_name, True, c.WHITE)
            surface.blit(text, (140, y))

            if i != len(self.level_names) - 1:
                file_base = os.path.basename(self.level_files[i])
                small = self.small_font.render(file_base, True, c.GRAY)
                surface.blit(small, (470, y + 6))
        
        # Draw cursor
        surface.blit(self.cursor.image, self.cursor.rect)
        
        # Draw scroll indicators if needed
        if self.scroll_offset > 0:
            up_text = self.small_font.render(self.tr('^ 上方还有 ^', '^ More above ^'), True, c.GOLD)
            up_rect = up_text.get_rect(centerx=c.SCREEN_WIDTH // 2, y=120)
            surface.blit(up_text, up_rect)
        
        if visible_end < len(self.level_names):
            down_text = self.small_font.render(self.tr('v 下方还有 v', 'v More below v'), True, c.GOLD)
            down_rect = down_text.get_rect(centerx=c.SCREEN_WIDTH // 2, 
                                           y=150 + self.max_visible * 40)
            surface.blit(down_text, down_rect)

        if self.delete_confirm_pending:
            warn_text = self.small_font.render(
                self.tr('再次按Delete/X确认删除，按Esc取消',
                        'Press Delete/X again to confirm delete, ESC to cancel'),
                True,
                c.GOLD)
            warn_rect = warn_text.get_rect(centerx=c.SCREEN_WIDTH // 2, y=520)
            surface.blit(warn_text, warn_rect)
        
        # Draw instructions
        instr_text = self.small_font.render(
            self.tr('上下:选择 | ENTER/K:游玩 | Delete/X:删除 | ESC:返回/取消 | L:中英',
                'UP/DOWN: Select | ENTER/K: Play | Delete/X: Delete | ESC: Back/Cancel | L: Lang'),
            True,
            c.WHITE)
        instr_rect = instr_text.get_rect(centerx=c.SCREEN_WIDTH // 2, 
                                         y=c.SCREEN_HEIGHT - 50)
        surface.blit(instr_text, instr_rect)
