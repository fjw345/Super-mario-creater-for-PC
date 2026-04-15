"""Level Editor for Mario Maker style gameplay"""

import pygame as pg
import json
import os
from .. import setup, tools
from .. import constants as c
from .. components import mario


class LevelEditor(tools._State):
    """Level Editor state for creating custom levels"""
    
    def __init__(self):
        tools._State.__init__(self)
        self._editor_test_snapshot = None
        
    def startup(self, current_time, persist):
        """Initialize the level editor"""
        self.persist = persist
        self.game_info = persist
        if c.LANGUAGE not in self.game_info:
            self.game_info[c.LANGUAGE] = 'zh'
        self.next = c.MAIN_MENU
        
        # Grid settings
        self.tile_size = 43  # Size of each tile in pixels
        self.grid_width = 200  # Number of tiles horizontally
        self.grid_height = 13  # Number of tiles vertically
        
        # Camera/viewport
        self.camera_x = 0
        self.scroll_speed = 10
        
        # Level data - 2D array storing tile types
        self.level_data = []
        
        # Current selected tile type
        # Slot order:
        # 1 ground, 2 upgrade box, 3 pipe, 4 goomba, 5 koopa,
        # 6 coin box, 7 brick, 8 flag, 9 mushroom, 0 fireflower.
        self.tile_types = [c.TILE_GROUND, c.TILE_COIN_BOX,
                  c.TILE_PIPE, c.TILE_GOOMBA, c.TILE_KOOPA,
              c.TILE_COIN, c.TILE_BRICK, c.TILE_FLAG,
              c.TILE_MUSHROOM, c.TILE_FIREFLOWER]
        self.current_tile_index = 0
        self.current_tile = self.tile_types[self.current_tile_index]
        
        # Load sprites
        self.setup_sprites()
        self.setup_background()
        self.setup_ui()
        
        # Input handling
        self.key_pressed = False
        self.mouse_pressed = False
        self.lang_key_pressed = False
        self.palette_click_pressed = False
        self.help_toggle_key_pressed = False
        self.help_tab_click_pressed = False
        self.wait_for_escape_release = True
        self.clear_confirm_pending = False
        self.exit_confirm_pending = False
        self.naming_mode = False
        self.name_input = ""
        self.name_error = ""
        self.ui_message = ""
        self.show_help_panel = True
        self.help_panel_width = 290
        self.level_name = "custom_level"
        self.has_unsaved_changes = False

        # Restore previous editor snapshot after test-run, otherwise start fresh.
        self.restore_editor_state_if_needed()
        self.current_tile = self.tile_types[self.current_tile_index]

        # Mario spawn preview (same start as runtime custom level).
        self.spawn_world_x = 110
        self.spawn_world_bottom = c.GROUND_HEIGHT
        self.spawn_mario_preview = mario.Mario()
        
        # Ensure custom levels directory exists
        self.levels_dir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(__file__))), 'custom_levels')
        if not os.path.exists(self.levels_dir):
            os.makedirs(self.levels_dir)


    def reset_level_data(self):
        """Reset editor map to a clean layout with default ground rows."""
        self.level_data = [[c.TILE_EMPTY for _ in range(self.grid_width)]
                           for _ in range(self.grid_height)]
        for x in range(self.grid_width):
            self.level_data[self.grid_height - 1][x] = c.TILE_GROUND
            self.level_data[self.grid_height - 2][x] = c.TILE_GROUND


    def restore_editor_state_if_needed(self):
        """Restore map/camera after test play return; otherwise start fresh."""
        snapshot = None

        if self.game_info.get('editor_resume_after_test'):
            snapshot = self.game_info.get('editor_test_snapshot')

            # Fallback for older saved key format.
            if snapshot is None:
                saved = self.game_info.get('editor_saved_level_data')
                if isinstance(saved, list) and saved:
                    snapshot = {
                        'level_data': [row[:] for row in saved],
                        'camera_x': self.game_info.get('editor_saved_camera_x', 0),
                        'tile_index': self.game_info.get('editor_saved_tile_index', 0),
                        'level_name': self.game_info.get('editor_saved_level_name', 'custom_level'),
                        'unsaved': bool(self.game_info.get('editor_saved_unsaved_changes', False)),
                    }

            # Final fallback in case persist dict was reset unexpectedly.
            if snapshot is None:
                snapshot = self._editor_test_snapshot

        if snapshot and isinstance(snapshot.get('level_data'), list):
            self.level_data = [row[:] for row in snapshot['level_data']]
            self.camera_x = snapshot.get('camera_x', 0)
            self.current_tile_index = snapshot.get('tile_index', 0)
            self.current_tile_index = max(0, min(self.current_tile_index, len(self.tile_types) - 1))
            self.level_name = snapshot.get('level_name', 'custom_level')
            self.has_unsaved_changes = bool(snapshot.get('unsaved', False))
        else:
            self.reset_level_data()
            self.has_unsaved_changes = False

        self.game_info['editor_resume_after_test'] = False
        self.game_info.pop('editor_test_snapshot', None)
        self._editor_test_snapshot = None
    
    def setup_sprites(self):
        """Load sprite images for tiles"""
        self.sprite_sheet = setup.GFX['tile_set']
        self.item_sheet = setup.GFX['item_objects']
        self.enemy_sheet = setup.GFX['smb_enemies_sheet']
        
        self.tile_images = {}
        
        # Ground tile
        self.tile_images[c.TILE_GROUND] = self.get_image(self.sprite_sheet, 0, 16, 16, 16)
        # Brick tile
        self.tile_images[c.TILE_BRICK] = self.get_image(self.sprite_sheet, 16, 0, 16, 16)
        # Coin box (question block)
        self.tile_images[c.TILE_COIN_BOX] = self.get_image(self.sprite_sheet, 384, 0, 16, 16)
        # Pipe icon: complete pipe shrunk into a 1x1 slot for palette display.
        self.tile_images[c.TILE_PIPE] = self.get_pipe_icon_image()
        # Full-size pipe used when drawing placed tiles in the level area.
        self.pipe_world_image = self.get_pipe_world_image()
        # Coin block (question block variant)
        self.tile_images[c.TILE_COIN] = self.get_image(self.sprite_sheet, 416, 0, 16, 16)
        # Goomba
        self.tile_images[c.TILE_GOOMBA] = self.get_image(self.enemy_sheet, 0, 4, 16, 16)
        # Koopa icon: complete koopa shrunk into a 1x1 slot for palette display.
        self.tile_images[c.TILE_KOOPA] = self.get_koopa_icon_image()
        # Full-size koopa used when drawing placed tiles in the level area.
        self.koopa_world_image = self.get_koopa_world_image()
        # Flag
        self.tile_images[c.TILE_FLAG] = self.get_image(self.item_sheet, 128, 32, 16, 16)
        # Mushroom
        self.tile_images[c.TILE_MUSHROOM] = self.get_image(self.item_sheet, 0, 0, 16, 16)
        # Fire flower
        self.tile_images[c.TILE_FIREFLOWER] = self.get_image(self.item_sheet, 0, 32, 16, 16)
        # Full-size flagpole used when drawing placed tiles in the level area.
        self.flagpole_world_image = self.get_flagpole_world_image()
        # Empty is kept for right-click erase logic, but no longer shown in the palette.
        empty_surface = pg.Surface([16, 16], pg.SRCALPHA)
        empty_surface.fill((0, 0, 0, 0))
        self.tile_images[c.TILE_EMPTY] = pg.transform.scale(
            empty_surface, (self.tile_size, self.tile_size))
    
    def get_image(self, sheet, x, y, width, height):
        """Extract and scale image from sprite sheet"""
        image = pg.Surface([width, height], pg.SRCALPHA)
        image.blit(sheet, (0, 0), (x, y, width, height))
        image.set_colorkey(c.BLACK)
        return pg.transform.scale(image, (self.tile_size, self.tile_size))


    def get_pipe_icon_image(self):
        """Compose a full pipe and shrink to the editor icon size."""
        top_part = pg.Surface([32, 16], pg.SRCALPHA)
        top_part.blit(self.sprite_sheet, (0, 0), (0, 160, 32, 16))
        top_part.set_colorkey(c.BLACK)

        body_part = pg.Surface([32, 16], pg.SRCALPHA)
        body_part.blit(self.sprite_sheet, (0, 0), (0, 176, 32, 16))
        body_part.set_colorkey(c.BLACK)

        full_pipe = pg.Surface([32, 32], pg.SRCALPHA)
        full_pipe.blit(top_part, (0, 0))
        full_pipe.blit(body_part, (0, 16))

        return pg.transform.scale(full_pipe, (self.tile_size, self.tile_size))


    def get_pipe_world_image(self):
        """Compose a full pipe at gameplay/world proportions."""
        top_part = pg.Surface([32, 16], pg.SRCALPHA)
        top_part.blit(self.sprite_sheet, (0, 0), (0, 160, 32, 16))
        top_part.set_colorkey(c.BLACK)

        body_part = pg.Surface([32, 16], pg.SRCALPHA)
        body_part.blit(self.sprite_sheet, (0, 0), (0, 176, 32, 16))
        body_part.set_colorkey(c.BLACK)

        full_pipe = pg.Surface([32, 32], pg.SRCALPHA)
        full_pipe.blit(top_part, (0, 0))
        full_pipe.blit(body_part, (0, 16))

        return pg.transform.scale(full_pipe, (83, 82))


    def get_flagpole_world_image(self):
        """Compose a full flagpole image for world rendering in the editor."""
        # Build pieces from original sprites.
        pole_seg = pg.Surface([2, 16], pg.SRCALPHA)
        pole_seg.blit(self.sprite_sheet, (0, 0), (263, 144, 2, 16))
        pole_seg.set_colorkey(c.BLACK)
        pole_seg = pg.transform.scale(pole_seg, (5, self.tile_size))

        finial = pg.Surface([8, 8], pg.SRCALPHA)
        finial.blit(self.sprite_sheet, (0, 0), (228, 120, 8, 8))
        finial.set_colorkey(c.BLACK)
        finial = pg.transform.scale(finial, (20, 20))

        flag = pg.Surface([16, 16], pg.SRCALPHA)
        flag.blit(self.item_sheet, (0, 0), (128, 32, 16, 16))
        flag.set_colorkey(c.BLACK)
        flag = pg.transform.scale(flag, (self.tile_size, self.tile_size))

        width = self.tile_size * 2
        height = self.tile_size * 10
        image = pg.Surface([width, height], pg.SRCALPHA)

        pole_x = (width // 2) - (pole_seg.get_width() // 2)
        for i in range(10):
            y = height - (i + 1) * self.tile_size
            image.blit(pole_seg, (pole_x, y))

        image.blit(finial, ((width // 2) - (finial.get_width() // 2), 0))
        image.blit(flag, (pole_x - flag.get_width() + 2, 20))

        return image


    def get_koopa_icon_image(self):
        """Compose a complete koopa icon for palette display."""
        koopa_full = pg.Surface([16, 24], pg.SRCALPHA)
        koopa_full.blit(self.enemy_sheet, (0, 0), (150, 0, 16, 24))
        koopa_full.set_colorkey(c.BLACK)
        return pg.transform.scale(koopa_full, (self.tile_size, self.tile_size))


    def get_koopa_world_image(self):
        """Compose a koopa at gameplay/world proportions."""
        koopa_full = pg.Surface([16, 24], pg.SRCALPHA)
        koopa_full.blit(self.enemy_sheet, (0, 0), (150, 0, 16, 24))
        koopa_full.set_colorkey(c.BLACK)
        return pg.transform.scale(koopa_full, (40, 60))
    
    def setup_background(self):
        """Setup the sky blue background"""
        self.background = pg.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT))
        self.background.fill(c.SKY_BLUE)
    
    def setup_ui(self):
        """Setup the UI elements"""
        self.font = self.load_font(24)
        self.small_font = self.load_font(20)
        
        # Tile palette background
        self.palette_rect = pg.Rect(10, 10, 400, 50)


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
        
    def update(self, surface, keys, current_time):
        """Update the editor state"""
        self.handle_input(keys)
        self.handle_mouse()
        self.draw(surface)


    def cleanup(self):
        """Ensure text input is closed when leaving editor state."""
        if self.naming_mode:
            pg.key.stop_text_input()
            self.naming_mode = False
        return super().cleanup()


    def get_event(self, event):
        """Handle text input events when naming save file."""
        if not self.naming_mode:
            return

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                self.cancel_naming_mode()
            elif event.key in (pg.K_RETURN, pg.K_KP_ENTER):
                self.confirm_save_with_name()
            elif event.key == pg.K_BACKSPACE:
                self.name_input = self.name_input[:-1]
                self.name_error = ""
        elif event.type == pg.TEXTINPUT:
            if len(self.name_input) < 32:
                self.name_input += event.text
                self.name_error = ""
    
    def handle_input(self, keys):
        """Handle keyboard input"""
        if self.naming_mode:
            return

        if self.wait_for_escape_release:
            if not keys[pg.K_ESCAPE]:
                self.wait_for_escape_release = False
            return

        if keys[pg.K_l] and not self.lang_key_pressed:
            current = self.game_info.get(c.LANGUAGE, 'zh')
            self.game_info[c.LANGUAGE] = 'en' if current == 'zh' else 'zh'
            self.lang_key_pressed = True
        elif not keys[pg.K_l]:
            self.lang_key_pressed = False

        # Scroll camera
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            self.camera_x = min(self.camera_x + self.scroll_speed, 
                              (self.grid_width * self.tile_size) - c.SCREEN_WIDTH)
        if keys[pg.K_LEFT] or keys[pg.K_a]:
            self.camera_x = max(self.camera_x - self.scroll_speed, 0)
        
        # Change tile type with number keys
        if keys[pg.K_1] and not self.key_pressed:
            self.current_tile_index = 0
            self.key_pressed = True
        elif keys[pg.K_2] and not self.key_pressed:
            self.current_tile_index = 1
            self.key_pressed = True
        elif keys[pg.K_3] and not self.key_pressed:
            self.current_tile_index = 2
            self.key_pressed = True
        elif keys[pg.K_4] and not self.key_pressed:
            self.current_tile_index = 3
            self.key_pressed = True
        elif keys[pg.K_5] and not self.key_pressed:
            self.current_tile_index = 4
            self.key_pressed = True
        elif keys[pg.K_6] and not self.key_pressed:
            self.current_tile_index = 5
            self.key_pressed = True
        elif keys[pg.K_7] and not self.key_pressed:
            self.current_tile_index = 6
            self.key_pressed = True
        elif keys[pg.K_8] and not self.key_pressed:
            self.current_tile_index = 7
            self.key_pressed = True
        elif keys[pg.K_9] and not self.key_pressed:
            self.current_tile_index = 8
            self.key_pressed = True
        elif keys[pg.K_0] and not self.key_pressed:
            self.current_tile_index = 9
            self.key_pressed = True
        
        # Cycle tiles with Q/E
        elif keys[pg.K_q] and not self.key_pressed:
            self.current_tile_index = (self.current_tile_index - 1) % len(self.tile_types)
            self.key_pressed = True
        elif keys[pg.K_e] and not self.key_pressed:
            self.current_tile_index = (self.current_tile_index + 1) % len(self.tile_types)
            self.key_pressed = True

        # Toggle right-side help table
        elif keys[pg.K_h] and not self.help_toggle_key_pressed:
            self.show_help_panel = not self.show_help_panel
            self.help_toggle_key_pressed = True
        
        # Save level with Ctrl+S (with naming dialog)
        elif keys[pg.K_s] and (keys[pg.K_LCTRL] or keys[pg.K_RCTRL]) and not self.key_pressed:
            if self.has_flag_tile():
                self.start_naming_mode()
            else:
                self.ui_message = self.tr('还没有旗杆，无法保存',
                                          'Cannot save: no flagpole in level')
            self.key_pressed = True

        # Reset design with C (double press to confirm)
        elif keys[pg.K_c] and not self.key_pressed:
            if self.clear_confirm_pending:
                self.reset_level_data()
                self.clear_confirm_pending = False
                self.has_unsaved_changes = True
                self.exit_confirm_pending = False
            else:
                self.clear_confirm_pending = True
            self.key_pressed = True
        
        # Return to menu with Escape
        elif keys[pg.K_ESCAPE] and not self.key_pressed:
            if self.clear_confirm_pending:
                self.clear_confirm_pending = False
            elif self.has_unsaved_changes and not self.exit_confirm_pending:
                self.exit_confirm_pending = True
                self.ui_message = self.tr('检测到未保存修改，再按一次ESC确认退出',
                                          'Unsaved changes detected, press ESC again to exit')
            else:
                self.done = True
            self.key_pressed = True
        
        # Test play with T
        elif keys[pg.K_t] and not self.key_pressed:
            # Save an in-memory editor snapshot so returning from test keeps current work.
            snapshot = {
                'level_data': [row[:] for row in self.level_data],
                'camera_x': self.camera_x,
                'tile_index': self.current_tile_index,
                'level_name': self.level_name,
                'unsaved': self.has_unsaved_changes,
            }
            self._editor_test_snapshot = snapshot
            self.persist['editor_test_snapshot'] = snapshot
            self.persist['editor_resume_after_test'] = True

            # Keep old keys for backward compatibility with existing sessions.
            self.persist['editor_saved_level_data'] = [row[:] for row in self.level_data]
            self.persist['editor_saved_camera_x'] = self.camera_x
            self.persist['editor_saved_tile_index'] = self.current_tile_index
            self.persist['editor_saved_level_name'] = self.level_name
            self.persist['editor_saved_unsaved_changes'] = self.has_unsaved_changes

            save_path = self.save_level('上次测试的关卡')
            if save_path:
                self.persist['custom_level_path'] = save_path
                self.persist[c.CUSTOM_LEVEL_RETURN] = c.LEVEL_EDITOR
                self.next = c.CUSTOM_LEVEL
                self.done = True
            self.key_pressed = True
        
        # Reset key pressed when no keys
        if not any([keys[pg.K_1], keys[pg.K_2], keys[pg.K_3], keys[pg.K_4],
                                     keys[pg.K_5], keys[pg.K_6], keys[pg.K_7], keys[pg.K_8],
                                     keys[pg.K_9], keys[pg.K_0],
                                 keys[pg.K_q], keys[pg.K_e], keys[pg.K_s], keys[pg.K_c],
                   keys[pg.K_ESCAPE], keys[pg.K_t]]):
            self.key_pressed = False

        if not keys[pg.K_h]:
            self.help_toggle_key_pressed = False
        
        self.current_tile = self.tile_types[self.current_tile_index]
    
    def handle_mouse(self):
        """Handle mouse input for placing tiles"""
        if self.naming_mode:
            return

        mouse_buttons = pg.mouse.get_pressed()
        mouse_pos = pg.mouse.get_pos()

        if mouse_buttons[0] and not self.help_tab_click_pressed:
            if self.get_help_panel_tab_rect().collidepoint(mouse_pos):
                self.show_help_panel = not self.show_help_panel
                self.help_tab_click_pressed = True
                return
        elif not mouse_buttons[0]:
            self.help_tab_click_pressed = False

        # Click tile palette to select tile type
        if mouse_buttons[0] and mouse_pos[1] <= 60 and not self.palette_click_pressed:
            for i, _ in enumerate(self.tile_types):
                x = 10 + i * 45
                y = 10
                tile_rect = pg.Rect(x, y, self.tile_size, self.tile_size)
                if tile_rect.collidepoint(mouse_pos):
                    self.current_tile_index = i
                    self.current_tile = self.tile_types[self.current_tile_index]
                    self.palette_click_pressed = True
                    return
        elif not mouse_buttons[0]:
            self.palette_click_pressed = False
        
        # Convert mouse position to grid coordinates
        grid_x = (mouse_pos[0] + self.camera_x) // self.tile_size
        grid_y = (mouse_pos[1] - 70) // self.tile_size  # Offset for UI

        # Ignore map editing clicks on expanded help table area.
        if self.show_help_panel and self.get_help_panel_rect().collidepoint(mouse_pos):
            return
        
        # Check if within grid bounds and not in UI area
        if (0 <= grid_x < self.grid_width and 
            0 <= grid_y < self.grid_height and
            mouse_pos[1] > 70):
            
            # Left click to place tile
            if mouse_buttons[0]:
                if self.level_data[grid_y][grid_x] != self.current_tile:
                    self.level_data[grid_y][grid_x] = self.current_tile
                    self.has_unsaved_changes = True
                    self.exit_confirm_pending = False
            
            # Right click to erase (set to empty)
            elif mouse_buttons[2]:
                if self.level_data[grid_y][grid_x] != c.TILE_EMPTY:
                    self.level_data[grid_y][grid_x] = c.TILE_EMPTY
                    self.has_unsaved_changes = True
                    self.exit_confirm_pending = False
    
    def draw(self, surface):
        """Draw the editor interface"""
        # Draw background
        surface.blit(self.background, (0, 0))
        
        # Draw grid and tiles
        self.draw_tiles(surface)
        self.draw_tile_preview(surface)
        self.draw_spawn_marker(surface)
        self.draw_grid(surface)
        
        # Draw UI
        self.draw_ui(surface)
        self.draw_help_panel(surface)


    def draw_tile_preview(self, surface):
        """Draw a semi-transparent preview at current mouse grid position."""
        mouse_x, mouse_y = pg.mouse.get_pos()

        if mouse_y <= 70:
            return

        if self.show_help_panel and self.get_help_panel_rect().collidepoint((mouse_x, mouse_y)):
            return

        grid_x = (mouse_x + self.camera_x) // self.tile_size
        grid_y = (mouse_y - 70) // self.tile_size

        if not (0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height):
            return

        if self.current_tile == c.TILE_EMPTY:
            return

        screen_x = grid_x * self.tile_size - self.camera_x
        screen_y = grid_y * self.tile_size + 70

        if self.current_tile == c.TILE_PIPE:
            preview = self.pipe_world_image.copy()
            preview.set_alpha(140)
            surface.blit(preview, (screen_x, screen_y))
        elif self.current_tile == c.TILE_KOOPA:
            preview = self.koopa_world_image.copy()
            preview.set_alpha(140)
            koopa_y = screen_y - (self.koopa_world_image.get_height() - self.tile_size)
            surface.blit(preview, (screen_x, koopa_y))
        elif self.current_tile == c.TILE_FLAG:
            preview = self.flagpole_world_image.copy()
            preview.set_alpha(140)
            flag_y = screen_y - (self.flagpole_world_image.get_height() - self.tile_size)
            surface.blit(preview, (screen_x, flag_y))
        elif self.current_tile in self.tile_images:
            preview = self.tile_images[self.current_tile].copy()
            preview.set_alpha(140)
            surface.blit(preview, (screen_x, screen_y))
    
    def draw_tiles(self, surface):
        """Draw all placed tiles"""
        # Calculate visible tile range
        start_x = max(0, self.camera_x // self.tile_size)
        end_x = min(self.grid_width, (self.camera_x + c.SCREEN_WIDTH) // self.tile_size + 1)
        
        for y in range(self.grid_height):
            for x in range(start_x, end_x):
                tile_type = self.level_data[y][x]
                if tile_type != c.TILE_EMPTY:
                    screen_x = x * self.tile_size - self.camera_x
                    screen_y = y * self.tile_size + 70  # Offset for UI

                    if tile_type == c.TILE_PIPE:
                        surface.blit(self.pipe_world_image, (screen_x, screen_y))
                    elif tile_type == c.TILE_KOOPA:
                        koopa_y = screen_y - (self.koopa_world_image.get_height() - self.tile_size)
                        surface.blit(self.koopa_world_image, (screen_x, koopa_y))
                    elif tile_type == c.TILE_FLAG:
                        flag_y = screen_y - (self.flagpole_world_image.get_height() - self.tile_size)
                        surface.blit(self.flagpole_world_image, (screen_x, flag_y))
                    elif tile_type in self.tile_images:
                        surface.blit(self.tile_images[tile_type], (screen_x, screen_y))
    
    def draw_grid(self, surface):
        """Draw the grid lines"""
        # Calculate visible tile range
        start_x = self.camera_x // self.tile_size
        
        # Vertical lines
        for x in range(start_x, start_x + c.SCREEN_WIDTH // self.tile_size + 2):
            screen_x = x * self.tile_size - self.camera_x
            pg.draw.line(surface, (100, 100, 100), 
                        (screen_x, 70), (screen_x, c.SCREEN_HEIGHT), 1)
        
        # Horizontal lines
        for y in range(self.grid_height + 1):
            screen_y = y * self.tile_size + 70
            pg.draw.line(surface, (100, 100, 100),
                        (0, screen_y), (c.SCREEN_WIDTH, screen_y), 1)
    
    def draw_ui(self, surface):
        """Draw the UI panel"""
        # Draw UI background
        pg.draw.rect(surface, (50, 50, 50), (0, 0, c.SCREEN_WIDTH, 70))
        
        # Draw tile palette
        for i, tile_type in enumerate(self.tile_types):
            x = 10 + i * 45
            y = 10
            
            # Highlight selected tile
            if i == self.current_tile_index:
                pg.draw.rect(surface, c.GOLD, (x - 2, y - 2, 44, 44), 3)
            
            # Draw tile image
            if tile_type in self.tile_images:
                surface.blit(self.tile_images[tile_type], (x, y))
            
            # Draw number below
            shortcut_label = str(i + 1) if i < 9 else '0'
            num_text = self.small_font.render(shortcut_label, True, c.WHITE)
            surface.blit(num_text, (x + 15, y + 45))
        
        # Draw current tile name
        tile_name = self.get_tile_display_name(self.current_tile)
        name_text = self.font.render(
            self.tr(f"当前: {tile_name}", f"Current: {tile_name}"),
            True,
            c.WHITE)
        surface.blit(name_text, (500, 15))
        
        help_hint = self.small_font.render(
            self.tr("H 折叠/展开右侧说明表", "H Collapse/Expand Right Help Table"),
            True,
            c.WHITE)
        surface.blit(help_hint, (500, 46))
        
        # Draw camera position
        pos_text = self.small_font.render(f"Pos: {self.camera_x}", True, c.WHITE)
        surface.blit(pos_text, (690, 15))

        if self.clear_confirm_pending:
            clear_tip = self.small_font.render(
                self.tr("再次按C确认清空，按ESC取消", "Press C again to clear, ESC to cancel"),
                True,
                c.GOLD)
            clear_rect = clear_tip.get_rect(centerx=c.SCREEN_WIDTH // 2, y=78)
            surface.blit(clear_tip, clear_rect)

        if self.has_unsaved_changes:
            unsaved_text = self.small_font.render(
                self.tr('状态: 未保存', 'Status: Unsaved'),
                True,
                c.GOLD)
            surface.blit(unsaved_text, (690, 40))

        if self.ui_message:
            msg = self.small_font.render(self.ui_message, True, c.GOLD)
            msg_rect = msg.get_rect(centerx=c.SCREEN_WIDTH // 2, y=98)
            surface.blit(msg, msg_rect)

        if self.naming_mode:
            self.draw_save_name_modal(surface)


    def draw_spawn_marker(self, surface):
        """Draw Mario sprite preview at initial spawn position."""
        image = self.spawn_mario_preview.image
        rect = image.get_rect()
        rect.x = int(self.spawn_world_x - self.camera_x)
        rect.bottom = int(self.spawn_world_bottom)

        if rect.right < 0 or rect.left > c.SCREEN_WIDTH:
            return
        if rect.bottom <= 70 or rect.top >= c.SCREEN_HEIGHT:
            return

        surface.blit(image, rect)


    def get_help_panel_rect(self):
        """Return right-side help panel rectangle."""
        x = c.SCREEN_WIDTH - self.help_panel_width - 10
        return pg.Rect(x, 80, self.help_panel_width, c.SCREEN_HEIGHT - 90)


    def get_help_panel_tab_rect(self):
        """Return fold tab rectangle for help panel."""
        panel = self.get_help_panel_rect()
        if self.show_help_panel:
            return pg.Rect(panel.x - 24, panel.y + 10, 24, 80)
        return pg.Rect(c.SCREEN_WIDTH - 24, panel.y + 10, 24, 80)


    def draw_help_panel(self, surface):
        """Draw collapsible key-action table at the map's right side."""
        tab = self.get_help_panel_tab_rect()
        pg.draw.rect(surface, (30, 30, 30), tab)
        pg.draw.rect(surface, c.WHITE, tab, 1)
        tab_symbol = "<" if self.show_help_panel else ">"
        tab_text = self.font.render(tab_symbol, True, c.WHITE)
        tab_rect = tab_text.get_rect(center=tab.center)
        surface.blit(tab_text, tab_rect)

        if not self.show_help_panel:
            return

        panel = self.get_help_panel_rect()
        pg.draw.rect(surface, (32, 32, 44), panel)
        pg.draw.rect(surface, c.WHITE, panel, 2)

        title = self.font.render(self.tr("操作说明", "Controls"), True, c.GOLD)
        surface.blit(title, (panel.x + 14, panel.y + 10))

        rows = [
            ("A / D", self.tr("滚动地图", "Scroll map")),
            ("1-0", self.tr("选择方块", "Select tile")),
            ("Q / E", self.tr("上/下一个方块", "Cycle tiles")),
            ("Ctrl+S", self.tr("保存并命名", "Save as")),
            ("T", self.tr("测试并保存", "Test save as Last Tested Level")),
            ("C", self.tr("重置（再次按C确认）", "Reset (press C again)")),
            ("ESC", self.tr("取消重置/退出", "Cancel reset / Exit")),
            ("L", self.tr("中英文切换", "Language toggle")),
            ("H", self.tr("折叠/展开本表", "Collapse/Expand panel")),
            ("左键/右键", self.tr("放置/擦除", "Place / Erase")),
        ]

        table_x = panel.x + 12
        table_y = panel.y + 52
        key_col_w = 88
        row_h = 34

        header_bg = pg.Rect(table_x, table_y, panel.width - 24, row_h)
        pg.draw.rect(surface, (52, 52, 70), header_bg)
        pg.draw.rect(surface, c.WHITE, header_bg, 1)
        key_head = self.small_font.render(self.tr("键位", "Key"), True, c.WHITE)
        act_head = self.small_font.render(self.tr("功能", "Action"), True, c.WHITE)
        surface.blit(key_head, (table_x + 8, table_y + 7))
        surface.blit(act_head, (table_x + key_col_w + 12, table_y + 7))

        for idx, (key_name, action_name) in enumerate(rows):
            y = table_y + row_h * (idx + 1)
            row_rect = pg.Rect(table_x, y, panel.width - 24, row_h)
            if idx % 2 == 0:
                pg.draw.rect(surface, (42, 42, 58), row_rect)
            pg.draw.rect(surface, c.WHITE, row_rect, 1)
            pg.draw.line(surface, c.WHITE,
                         (table_x + key_col_w, y),
                         (table_x + key_col_w, y + row_h), 1)

            key_text = self.small_font.render(key_name, True, c.GOLD)
            action_text = self.small_font.render(action_name, True, c.WHITE)
            surface.blit(key_text, (table_x + 8, y + 7))
            surface.blit(action_text, (table_x + key_col_w + 8, y + 7))


    def draw_save_name_modal(self, surface):
        """Draw a centered save-name modal for Ctrl+S."""
        overlay = pg.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        panel_w = 620
        panel_h = 220
        panel_x = (c.SCREEN_WIDTH - panel_w) // 2
        panel_y = (c.SCREEN_HEIGHT - panel_h) // 2
        pg.draw.rect(surface, (40, 40, 40), (panel_x, panel_y, panel_w, panel_h))
        pg.draw.rect(surface, c.WHITE, (panel_x, panel_y, panel_w, panel_h), 2)

        title = self.font.render(
            self.tr("保存关卡名称", "Save Level Name"), True, c.WHITE)
        surface.blit(title, (panel_x + 20, panel_y + 20))

        input_bg = pg.Rect(panel_x + 20, panel_y + 70, panel_w - 40, 44)
        pg.draw.rect(surface, (20, 20, 20), input_bg)
        pg.draw.rect(surface, c.GOLD, input_bg, 2)

        shown_name = self.name_input if self.name_input else "_"
        name_text = self.font.render(shown_name, True, c.WHITE)
        surface.blit(name_text, (input_bg.x + 10, input_bg.y + 6))

        suffix_text = self.small_font.render(".json", True, c.GRAY)
        surface.blit(suffix_text, (input_bg.right - 70, input_bg.y + 10))

        hint = self.small_font.render(
            self.tr("Enter确认保存 | Esc取消 | 自动保存到 custom_levels",
                    "Enter Save | Esc Cancel | Saved to custom_levels"),
            True,
            c.WHITE)
        surface.blit(hint, (panel_x + 20, panel_y + 135))

        if self.name_error:
            err = self.small_font.render(self.name_error, True, c.RED)
            surface.blit(err, (panel_x + 20, panel_y + 170))


    def get_tile_display_name(self, tile_type):
        """Return localized, user-friendly tile name for the palette."""
        zh_names = {
            c.TILE_GROUND: '地面',
            c.TILE_COIN_BOX: '升级问号砖',
            c.TILE_PIPE: '管道',
            c.TILE_GOOMBA: '栗子怪',
            c.TILE_KOOPA: '乌龟',
            c.TILE_COIN: '金币问号砖',
            c.TILE_BRICK: '砖块',
            c.TILE_FLAG: '旗杆',
            c.TILE_MUSHROOM: '蘑菇',
            c.TILE_FIREFLOWER: '火焰花',
        }
        en_names = {
            c.TILE_GROUND: 'GROUND',
            c.TILE_COIN_BOX: 'UPGRADE QUESTION BOX',
            c.TILE_PIPE: 'PIPE',
            c.TILE_GOOMBA: 'GOOMBA',
            c.TILE_KOOPA: 'KOOPA',
            c.TILE_COIN: 'COIN QUESTION BOX',
            c.TILE_BRICK: 'BRICK',
            c.TILE_FLAG: 'FLAGPOLE',
            c.TILE_MUSHROOM: 'MUSHROOM',
            c.TILE_FIREFLOWER: 'FIRE FLOWER',
        }

        if self.game_info.get(c.LANGUAGE, 'zh') == 'zh':
            return zh_names.get(tile_type, tile_type)
        return en_names.get(tile_type, tile_type.upper())
    
    def sanitize_level_name(self, raw_name):
        """Return a safe file name without extension."""
        invalid_chars = '<>:"/\\|?*'
        name = ''.join(ch for ch in raw_name if ch not in invalid_chars)
        name = name.strip().strip('.')
        return name[:32]


    def start_naming_mode(self):
        """Enter save-as mode for Ctrl+S."""
        self.naming_mode = True
        self.name_input = self.level_name
        self.name_error = ""
        pg.key.start_text_input()


    def cancel_naming_mode(self):
        """Cancel save-as mode."""
        self.naming_mode = False
        self.name_error = ""
        pg.key.stop_text_input()


    def confirm_save_with_name(self):
        """Validate name and save level."""
        if not self.has_flag_tile():
            self.name_error = self.tr('还没有旗杆，无法保存',
                                      'Cannot save: no flagpole in level')
            return

        safe_name = self.sanitize_level_name(self.name_input)
        if not safe_name:
            self.name_error = self.tr("名称不能为空或包含非法字符", "Invalid or empty name")
            return

        save_path = self.save_level(safe_name)
        if save_path:
            self.cancel_naming_mode()


    def save_level(self, level_name=None):
        """Save the level to a JSON file and return path."""
        if not self.has_flag_tile():
            self.ui_message = self.tr('还没有旗杆，无法保存',
                                      'Cannot save: no flagpole in level')
            return None

        if level_name:
            self.level_name = level_name

        level_data = {
            'name': self.level_name,
            'width': self.grid_width,
            'height': self.grid_height,
            'tile_size': self.tile_size,
            'tiles': self.level_data
        }
        
        filepath = os.path.join(self.levels_dir, f"{self.level_name}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(level_data, f, ensure_ascii=False)
        
        print(f"Level saved to {filepath}")
        self.ui_message = self.tr(f'保存成功: {self.level_name}',
                                  f'Saved: {self.level_name}')
        self.has_unsaved_changes = False
        self.exit_confirm_pending = False
        return filepath


    def has_flag_tile(self):
        """Return True if at least one flag tile exists in the map."""
        for row in self.level_data:
            if c.TILE_FLAG in row:
                return True
        return False
