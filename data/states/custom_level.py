"""Custom Level loader and player for user-created levels"""

from __future__ import division

import pygame as pg
from .. import setup, tools, storage
from .. import constants as c
from .. import game_sound
from .. components import mario
from .. components import collider
from .. components import bricks
from .. components import coin_box
from .. components import enemies
from .. components import checkpoint
from .. components import flagpole
from .. components import info
from .. components import castle_flag
from .. components import powerups
from .level_common import LevelCommon


class CustomLevel(LevelCommon, tools._State):
    """State for playing custom levels created in the level editor"""
    
    def __init__(self):
        tools._State.__init__(self)
    
    def startup(self, current_time, persist):
        """Called when the State object is created"""
        self.game_info = persist
        self.persist = self.game_info
        self.game_info[c.CURRENT_TIME] = current_time
        self.game_info[c.LEVEL_STATE] = c.NOT_FROZEN
        self.game_info[c.MARIO_DEAD] = False
        
        self.state = c.NOT_FROZEN
        self.death_timer = 0
        self.flag_timer = 0
        self.flag_score = None
        self.flag_score_total = 0
        self.flag = None
        self.flag_ground_y = c.GROUND_HEIGHT
        self.game_info.pop('resume_custom_level', None)
        self.pending_enemies = []
        self.pending_powerups = []

        self.moving_score_list = []
        self.overhead_info_display = info.OverheadInfo(self.game_info, c.LEVEL)
        self.sound_manager = game_sound.Sound(self.overhead_info_display)
        self.return_state = self.game_info.get(c.CUSTOM_LEVEL_RETURN, c.MAIN_MENU)
        
        # Load the custom level
        self.level_path = self.game_info.get('custom_level_path', None)
        self.tile_size = c.TILE_SIZE
        self.grid_height = c.GRID_HEIGHT
        self.flag_tile = None
        
        self.load_error = None
        self.level_data = None
        self.grid_width = 50
        try:
            if not self.level_path:
                raise storage.LevelLoadError('no level path')
            self.load_level()
        except storage.LevelLoadError as exc:
            # Leave on the first frame and report the error to the caller.
            self.load_error = str(exc)
            self.level_data = None
            self.grid_width = 50
        
        self.setup_world_images()
        self.find_flag_tile()
        self.setup_background()
        self.setup_groups()
        self.setup_level_from_data()
        self.setup_mario()
        self.setup_spritegroups()


    def setup_world_images(self):
        """Prepare composed world-size images used by custom tiles."""
        sprite_sheet = setup.GFX['tile_set']

        top_part = pg.Surface([32, 16]).convert()
        top_part.blit(sprite_sheet, (0, 0), (0, 160, 32, 16))
        top_part.set_colorkey(c.BLACK)

        body_part = pg.Surface([32, 16]).convert()
        body_part.blit(sprite_sheet, (0, 0), (0, 176, 32, 16))
        body_part.set_colorkey(c.BLACK)

        pipe_comp = pg.Surface([32, 32]).convert()
        pipe_comp.set_colorkey(c.BLACK)
        pipe_comp.blit(top_part, (0, 0))
        pipe_comp.blit(body_part, (0, 16))

        # Match original 1-1 style proportions.
        self.pipe_world_width = 83
        self.pipe_world_height = 82
        self.pipe_world_image = pg.transform.scale(
            pipe_comp,
            (self.pipe_world_width, self.pipe_world_height))

        self.ground_tile_image = self.get_image(sprite_sheet, 0, 16, 16, 16)
        self.castle_image = self.get_castle_image()


    def get_image(self, sprite_sheet, x, y, width, height):
        """Extract and scale a tile-sized image from a sprite sheet."""
        image = pg.Surface([width, height]).convert()
        image.blit(sprite_sheet, (0, 0), (x, y, width, height))
        image.set_colorkey(c.BLACK)
        return pg.transform.scale(image, (self.tile_size, self.tile_size))


    def get_castle_image(self):
        """Extract the 1-1 castle from the background for custom levels."""
        castle = pg.Surface((112, 160)).convert()
        level_1 = setup.GFX['level_1']
        castle.blit(level_1, (0, 0), (3208, 40, 112, 160))
        castle.set_colorkey(level_1.get_at((0, 0)))
        rect = castle.get_rect()
        return pg.transform.scale(
            castle,
            (int(rect.width * c.BACKGROUND_MULTIPLER),
             int(rect.height * c.BACKGROUND_MULTIPLER)))


    def find_flag_tile(self):
        """Find the editor-placed flagpole anchor, if this map has one."""
        self.flag_tile = None
        if self.level_data is None:
            return

        for y, row in enumerate(self.level_data):
            for x, tile_type in enumerate(row):
                if tile_type == c.TILE_FLAG:
                    self.flag_tile = (x, y)
                    return
    
    def load_level(self):
        """Load level data from JSON file"""
        data = storage.load_level(self.level_path)

        self.level_data = data['tiles']
        self.grid_width = data['width']
        self.grid_height = data['height']
        self.tile_size = data['tile_size']
        if data['unknown_tiles']:
            print('Level %s: %d unknown tile(s) treated as empty'
                  % (self.level_path, data['unknown_tiles']))
    
    def setup_background(self):
        """Sets the background image, rect and scales it to the correct
        proportions"""
        # Calculate level width based on grid, extending at runtime for the
        # automatically generated castle after the flagpole.
        level_width = max(self.grid_width * self.tile_size,
                          self.get_runtime_level_width())
        level_height = c.SCREEN_HEIGHT
        
        # Create a simple sky blue background
        self.level = pg.Surface((level_width, level_height)).convert()
        self.level.fill(c.SKY_BLUE)
        self.level_rect = self.level.get_rect()
        
        self.background = self.level.copy()
        self.back_rect = self.background.get_rect()
        
        self.viewport = setup.SCREEN.get_rect(bottom=self.level_rect.bottom)
        self.viewport.x = 0


    def get_runtime_level_width(self):
        """Return the width needed for the generated end-of-level scene."""
        if self.flag_tile is None:
            return self.grid_width * self.tile_size

        flag_world_x = self.flag_tile[0] * self.tile_size
        pole_x = flag_world_x + (self.tile_size - 2)
        castle_x = pole_x + 90
        return castle_x + self.castle_image.get_width() + 220
    
    def setup_groups(self):
        """Initialize sprite groups"""
        self.ground_group = pg.sprite.Group()
        self.pipe_group = pg.sprite.Group()
        self.step_group = pg.sprite.Group()
        self.coin_group = pg.sprite.Group()
        self.powerup_group = pg.sprite.Group()
        self.brick_group = pg.sprite.Group()
        self.coin_box_group = pg.sprite.Group()
        self.enemy_group = pg.sprite.Group()
        self.brick_pieces_group = pg.sprite.Group()
        self.flag_pole_group = pg.sprite.Group()
        self.check_point_group = pg.sprite.Group()
        self.static_coin_group = pg.sprite.Group()
        self.castle_rect = None
        self.castle_flag_added = False
        self.end_sequence_timer = 0
    
    def setup_level_from_data(self):
        """Create game objects from level data"""
        if self.level_data is None:
            # Create default ground if no level data
            ground_rect = collider.Collider(0, c.GROUND_HEIGHT, 
                                           self.grid_width * self.tile_size, 60)
            self.ground_group.add(ground_rect)
            return
        
        # Track positions for multi-tile objects like pipes
        self.flag_placed = False
        
        for y, row in enumerate(self.level_data):
            for x, tile_type in enumerate(row):
                world_x = x * self.tile_size
                world_y = y * self.tile_size + c.EDITOR_TOP
                
                self.create_tile(tile_type, world_x, world_y, x, y)
    
    def create_tile(self, tile_type, world_x, world_y, grid_x, grid_y):
        """Create the game object for a tile ID via TILE_CREATORS."""
        creator = self.TILE_CREATORS.get(tile_type)
        if creator is not None:
            creator(self, world_x, world_y)

    def _make_ground(self, world_x, world_y):
        self.ground_group.add(collider.Collider(
            world_x, world_y, self.tile_size, self.tile_size))

    def _make_brick(self, world_x, world_y):
        self.brick_group.add(bricks.Brick(world_x, world_y))

    def _make_upgrade_box(self, world_x, world_y):
        # Mushroom for small Mario, fireflower for big Mario.
        self.coin_box_group.add(coin_box.Coin_box(
            world_x, world_y, c.MUSHROOM, self.powerup_group))

    def _make_coin_box(self, world_x, world_y):
        self.coin_box_group.add(coin_box.Coin_box(
            world_x, world_y, c.COIN, self.coin_group))

    def _make_pipe(self, world_x, world_y):
        # Full-size pipe collider (same size as 1-1 pipes).
        self.pipe_group.add(collider.Collider(
            world_x, world_y, self.pipe_world_width, self.pipe_world_height))

    def _make_enemy(self, enemy_cls):
        def make(self, world_x, world_y):
            enemy = enemy_cls()
            enemy.rect.x = world_x
            enemy.rect.bottom = world_y + self.tile_size
            self.pending_enemies.append(enemy)
        return make

    def _make_flag(self, world_x, world_y):
        if not self.flag_placed:  # only the first flagpole counts
            self.setup_flag_pole(world_x, world_y)
            self.flag_placed = True

    def _make_mushroom(self, world_x, world_y):
        item = powerups.Mushroom(world_x + self.tile_size // 2, world_y)
        item.rect.bottom = world_y + self.tile_size
        item.state = c.SLIDE
        self.pending_powerups.append(item)

    def _make_fireflower(self, world_x, world_y):
        item = powerups.FireFlower(world_x + self.tile_size // 2, world_y)
        item.rect.bottom = world_y + self.tile_size
        item.state = c.RESTING
        self.powerup_group.add(item)

    # Tile ID -> creator. To add a tile, add its ID in constants.py, a row in
    # data/tiles.py, and an entry here.
    TILE_CREATORS = {
        c.TILE_GROUND: _make_ground,
        c.TILE_BRICK: _make_brick,
        c.TILE_COIN_BOX: _make_upgrade_box,
        c.TILE_COIN: _make_coin_box,
        c.TILE_PIPE: _make_pipe,
        c.TILE_GOOMBA: _make_enemy(None, enemies.Goomba),
        c.TILE_KOOPA: _make_enemy(None, enemies.Koopa),
        c.TILE_FLAG: _make_flag,
        c.TILE_MUSHROOM: _make_mushroom,
        c.TILE_FIREFLOWER: _make_fireflower,
    }

    def setup_flag_pole(self, tile_world_x, tile_world_y):
        """Create a flag pole using the same anchor logic as the editor preview."""
        # In editor, full flagpole image is 2x10 tiles and the selected tile is the bottom-left anchor.
        image_top = tile_world_y - (self.tile_size * 9)
        pole_x = tile_world_x + (self.tile_size - 2)
        pole_top = image_top + self.tile_size

        # Keep top clear for finial and avoid overlap with flag head.
        self.flag = flagpole.Flag(tile_world_x + self.tile_size, pole_top + 3)

        # Bottom of the pole: slide-down end points are measured from here.
        self.flag_ground_y = tile_world_y + self.tile_size
        self.flag.ground_y = self.flag_ground_y

        poles = [flagpole.Pole(pole_x, pole_top + i * self.tile_size)
                 for i in range(9)]

        finial = flagpole.Finial(tile_world_x + self.tile_size, pole_top)

        self.flag_pole_group.add(self.flag, finial, *poles)

        # Keep checkpoint aligned to actual pole x position.
        flag_check = checkpoint.Checkpoint(pole_x - 1, '11', 5, 6)
        self.check_point_group.add(flag_check)
        self.setup_castle_end(tile_world_y, pole_x)


    def setup_castle_end(self, tile_world_y, pole_x):
        """Create the runtime-only castle and optional doorway trigger."""
        ground_top = tile_world_y + self.tile_size
        castle_x = pole_x + 90
        castle_y = ground_top - self.castle_image.get_height()
        self.castle_rect = self.castle_image.get_rect(topleft=(castle_x, castle_y))

        door_x = castle_x + 180
        castle_check = checkpoint.Checkpoint(door_x, '12', 0, 10, c.SCREEN_HEIGHT)
        self.check_point_group.add(castle_check)
    
    def setup_mario(self):
        """Places Mario at the beginning of the level"""
        self.mario = mario.Mario()
        self.mario.rect.x = self.viewport.x + 110
        self.mario.rect.bottom = c.GROUND_HEIGHT
        self.mario.flag_pole_ground = self.flag_ground_y

    def setup_spritegroups(self):
        """Sprite groups created for convenience"""
        self.sprites_about_to_die_group = pg.sprite.Group()
        self.shell_group = pg.sprite.Group()
        
        self.ground_step_pipe_group = pg.sprite.Group(self.ground_group,
                                                      self.pipe_group,
                                                      self.step_group)
        
        self.mario_and_enemy_group = pg.sprite.Group(self.mario,
                                                     self.enemy_group)
    
    def update(self, surface, keys, current_time):
        """Updates Entire level using states. Called by the control object"""
        if self.load_error:
            self.game_info['level_error'] = self.load_error
            self.exit_to_return_state()
            return
        if keys[pg.K_ESCAPE]:
            self.exit_to_return_state()
            return

        self.game_info[c.CURRENT_TIME] = self.current_time = current_time
        self.handle_states(keys)
        self.check_if_time_out()
        self.blit_everything(surface)
        self.sound_manager.update(self.game_info, self.mario)
    
    def update_during_transition_state(self, keys):
        """Updates mario in a transition state"""
        self.mario.update(keys, self.game_info, self.powerup_group)
        for score_obj in self.moving_score_list:
            score_obj.update(self.moving_score_list, self.game_info)
        if self.flag_score:
            self.flag_score.update(None, self.game_info)
            self.check_to_add_flag_score()
        self.coin_box_group.update(self.game_info)
        self.flag_pole_group.update(self.game_info)
        self.check_if_mario_in_transition_state()
        self.check_flag()
        self.check_for_mario_death()
        self.check_auto_finish_after_flag()
        self.overhead_info_display.update(self.game_info, self.mario)
    
    def update_all_sprites(self, keys):
        """Updates the location of all sprites on the screen."""
        self.mario.update(keys, self.game_info, self.powerup_group)
        for score_obj in self.moving_score_list:
            score_obj.update(self.moving_score_list, self.game_info)
        if self.flag_score:
            self.flag_score.update(None, self.game_info)
            self.check_to_add_flag_score()
        self.flag_pole_group.update()
        self.activate_pending_sprites()
        self.check_points_check()
        self.enemy_group.update(self.game_info)
        self.sprites_about_to_die_group.update(self.game_info, self.viewport)
        self.shell_group.update(self.game_info)
        self.brick_group.update()
        self.coin_box_group.update(self.game_info)
        self.powerup_group.update(self.game_info, self.viewport)
        self.coin_group.update(self.game_info, self.viewport)
        self.brick_pieces_group.update()
        self.adjust_sprite_positions()
        self.check_if_mario_in_transition_state()
        self.check_for_mario_death()
        self.update_viewport()
        self.check_auto_finish_after_flag()
        self.overhead_info_display.update(self.game_info, self.mario)
    
    def activate_pending_sprites(self):
        """Add enemies and placed mushrooms to the active groups once they
        reach the right edge of the camera. 1-1 spawns its enemies the same
        way, just off the right edge of the screen."""
        limit = self.viewport.right
        for enemy in list(self.pending_enemies):
            if enemy.rect.x <= limit:
                self.pending_enemies.remove(enemy)
                self.enemy_group.add(enemy)
                self.mario_and_enemy_group.add(enemy)
        for item in list(self.pending_powerups):
            if item.rect.x <= limit:
                self.pending_powerups.remove(item)
                self.powerup_group.add(item)


    def check_points_check(self):
        """Detect if checkpoint collision occurs"""
        checkpoint_hit = pg.sprite.spritecollideany(self.mario,
                                                     self.check_point_group)
        if checkpoint_hit:
            checkpoint_hit.kill()

            if checkpoint_hit.name == '11':
                self.mario.state = c.FLAGPOLE
                self.mario.invincible = False
                self.mario.flag_pole_right = checkpoint_hit.rect.right
                if self.mario.rect.bottom < self.flag.rect.y:
                    self.mario.rect.bottom = self.flag.rect.y
                self.flag.state = c.SLIDE_DOWN
                self.create_flag_points(self.flag.rect.x + 13,
                                        self.flag_ground_y)
                self.end_sequence_timer = self.current_time

            elif checkpoint_hit.name == '12':
                self.start_castle_countdown()


    def check_enemy_x_collisions(self, enemy):
        """Enemy collisions along the x axis.  Removes enemy from enemy group
        in order to check against all other enemies then adds it back."""
        enemy.kill()

        # Unlike 1-1, custom maps can put bricks and boxes at walking height,
        # so they block sideways too. Otherwise the y pass lifts the enemy on
        # top of a block that is one tile higher.
        collider = pg.sprite.spritecollideany(enemy, self.ground_step_pipe_group)
        if not collider:
            collider = pg.sprite.spritecollideany(enemy, self.brick_group)
        if not collider:
            collider = pg.sprite.spritecollideany(enemy, self.coin_box_group)
        enemy_collider = pg.sprite.spritecollideany(enemy, self.enemy_group)

        if collider:
            if enemy.direction == c.RIGHT:
                enemy.rect.right = collider.rect.left
                enemy.direction = c.LEFT
                enemy.x_vel = -2
            elif enemy.direction == c.LEFT:
                enemy.rect.left = collider.rect.right
                enemy.direction = c.RIGHT
                enemy.x_vel = 2

        elif enemy_collider:
            if enemy.direction == c.RIGHT:
                enemy.rect.right = enemy_collider.rect.left
                enemy.direction = c.LEFT
                enemy_collider.direction = c.RIGHT
                enemy.x_vel = -2
                enemy_collider.x_vel = 2
            elif enemy.direction == c.LEFT:
                enemy.rect.left = enemy_collider.rect.right
                enemy.direction = c.RIGHT
                enemy_collider.direction = c.LEFT
                enemy.x_vel = 2
                enemy_collider.x_vel = -2

        self.enemy_group.add(enemy)
        self.mario_and_enemy_group.add(self.enemy_group)


    def adjust_powerup_position(self):
        """Moves mushrooms, stars and fireballs along the x, y axes"""
        for powerup in self.powerup_group:
            if powerup.name == c.MUSHROOM:
                self.adjust_mushroom_position(powerup)
            elif powerup.name == c.STAR:
                self.adjust_star_position(powerup)
            elif powerup.name == c.FIREBALL:
                self.adjust_fireball_position(powerup)
            elif powerup.name == c.LIFE_MUSHROOM:
                self.adjust_mushroom_position(powerup)


    def update_viewport(self):
        """Changes the view of the camera (same rule as 1-1, including the
        half-speed zone left of the screen centre)."""
        third = self.viewport.x + self.viewport.w // 3
        mario_center = self.mario.rect.centerx
        mario_right = self.mario.rect.right

        if self.mario.x_vel > 0 and mario_center >= third:
            mult = 0.5 if mario_right < self.viewport.centerx else 1
            new = self.viewport.x + mult * self.mario.x_vel
            highest = max(0, self.level_rect.w - self.viewport.w)
            self.viewport.x = min(highest, new)


    def check_flag(self):
        """Check if Mario has reached the flag"""
        if self.flag is None:
            return

        if (self.flag.state == c.BOTTOM_OF_POLE
            and self.mario.state == c.FLAGPOLE):
            self.mario.set_state_to_bottom_of_pole()


    def check_auto_finish_after_flag(self):
        """Finish the ending scene even if Mario gets stuck before the castle."""
        if self.mario.state not in (c.FLAGPOLE, c.BOTTOM_OF_POLE,
                                    c.WALKING_TO_CASTLE,
                                    c.END_OF_LEVEL_FALL):
            return

        if self.end_sequence_timer == 0:
            self.end_sequence_timer = self.current_time
        elif (self.current_time - self.end_sequence_timer) > 3500:
            self.start_castle_countdown()


    def start_castle_countdown(self):
        """Move from the auto-walk scene into the 1-1 style time tally."""
        if self.state == c.IN_CASTLE or self.mario.in_castle:
            return

        self.state = c.IN_CASTLE
        self.mario.kill()
        self.mario.state = c.STAND
        self.mario.in_castle = True
        self.overhead_info_display.state = c.FAST_COUNT_DOWN
    
    def check_for_mario_death(self):
        """Check if Mario has died"""
        if (self.mario.rect.top > c.SCREEN_HEIGHT
            and not self.mario.in_castle
            and self.mario.state not in (c.WALKING_TO_CASTLE,
                                         c.END_OF_LEVEL_FALL)):
            self.mario.dead = True
            self.mario.x_vel = 0
            self.state = c.FROZEN
            self.game_info[c.MARIO_DEAD] = True
        
        if self.mario.dead:
            self.play_death_song()


    def update_top_score(self):
        if self.game_info[c.SCORE] > self.persist[c.TOP_SCORE]:
            self.persist[c.TOP_SCORE] = self.game_info[c.SCORE]


    def set_game_info_values(self):
        """Sets the new game values after Mario's death. Opened from the
        editor, the level returns to the editor instead."""
        self.update_top_score()
        self.sound_manager.stop_music()

        if self.return_state == c.LEVEL_EDITOR:
            self.next = c.LEVEL_EDITOR
            return

        self.persist[c.LIVES] -= 1
        if self.persist[c.LIVES] <= 0:
            self.next = c.GAME_OVER
        elif self.overhead_info_display.time == 0:
            self.persist['resume_custom_level'] = True
            self.next = c.TIME_OUT
        else:
            self.persist['resume_custom_level'] = True
            self.next = c.LOAD_SCREEN

    def check_if_time_out(self):
        """Check if time has run out"""
        if (self.overhead_info_display.time <= 0
            and not self.mario.dead
            and not self.mario.in_castle
            and self.mario.state not in (c.WALKING_TO_CASTLE,
                                         c.END_OF_LEVEL_FALL)):
            self.mario.start_death_jump(self.game_info)
            self.state = c.FROZEN
    
    def update_while_in_castle(self):
        """Updates when Mario is in the castle"""
        for score_obj in self.moving_score_list:
            score_obj.update(self.moving_score_list, self.game_info)
        self.overhead_info_display.update(self.game_info, self.mario)
        if self.overhead_info_display.state == c.END_OF_LEVEL:
            self.state = c.FLAG_AND_FIREWORKS
            if self.castle_rect and not self.castle_flag_added:
                self.flag_pole_group.add(castle_flag.Flag(
                    self.castle_rect.x + 150,
                    self.castle_rect.y + 215))
                self.castle_flag_added = True
    
    def update_flag_and_fireworks(self):
        """Updates during flag and fireworks"""
        for score_obj in self.moving_score_list:
            score_obj.update(self.moving_score_list, self.game_info)
        self.overhead_info_display.update(self.game_info, self.mario)
        self.flag_pole_group.update()
        self.end_game()


    def end_game(self):
        """Finish custom level after the castle flag animation."""
        if self.flag_timer == 0:
            self.flag_timer = self.current_time
        elif (self.current_time - self.flag_timer) > 2000:
            self.update_top_score()
            self.exit_to_return_state()
    
    def blit_everything(self, surface):
        """Blit all sprites to the screen"""
        # Mirror Level1 rendering flow: draw world to level surface, then crop by viewport.
        self.level.blit(self.background, self.viewport, self.viewport)
        self.draw_ground_tiles(self.level)
        self.draw_castle(self.level)
        if self.flag_score:
            self.flag_score.draw(self.level)

        # Keep draw order aligned with 1-1 so reveal animation is masked by the box.
        self.powerup_group.draw(self.level)
        self.coin_group.draw(self.level)
        self.brick_group.draw(self.level)
        self.coin_box_group.draw(self.level)
        self.brick_pieces_group.draw(self.level)
        self.shell_group.draw(self.level)
        self.sprites_about_to_die_group.draw(self.level)
        self.flag_pole_group.draw(self.level)
        self.mario_and_enemy_group.draw(self.level)

        surface.blit(self.level, (0, 0), self.viewport)

        for score_obj in self.moving_score_list:
            score_obj.draw(surface)

        self.overhead_info_display.draw(surface)


    def draw_castle(self, surface):
        """Draw the generated castle behind the ending sprites."""
        if self.castle_rect:
            surface.blit(self.castle_image, self.castle_rect)

    def draw_ground_tiles(self, surface):
        """Draw visible ground tiles"""
        if self.level_data is None:
            return
        
        # Visible range. A pipe is two tiles wide and anchored on its left
        # column, so start two columns early to keep it until it leaves.
        vx = int(self.viewport.x)
        start_x = max(0, vx // self.tile_size - 2)
        end_x = min(self.grid_width,
                    (vx + c.SCREEN_WIDTH) // self.tile_size + 1)

        for y in range(self.grid_height):
            for x in range(start_x, end_x):
                tile_type = self.level_data[y][x]

                if tile_type == c.TILE_GROUND:
                    # Draw using world coordinates onto the level surface.
                    world_x = x * self.tile_size
                    world_y = y * self.tile_size + c.EDITOR_TOP
                    surface.blit(self.ground_tile_image, (world_x, world_y))
                
                elif tile_type == c.TILE_PIPE:
                    # Draw as a complete pipe in world coordinates.
                    world_x = x * self.tile_size
                    world_y = y * self.tile_size + c.EDITOR_TOP

                    surface.blit(self.pipe_world_image, (world_x, world_y))


    def exit_to_return_state(self):
        """Exit custom level to its caller state and stop music."""
        self.sound_manager.stop_music()
        self.next = self.return_state
        self.done = True
