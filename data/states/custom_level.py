"""Custom Level loader and player for user-created levels"""

from __future__ import division

import pygame as pg
import json
import os
from .. import setup, tools
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
from .. components import score
from .. components import castle_flag
from .. components import coin
from .. components import powerups


class CustomLevel(tools._State):
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
        
        self.moving_score_list = []
        self.overhead_info_display = info.OverheadInfo(self.game_info, c.LEVEL)
        self.sound_manager = game_sound.Sound(self.overhead_info_display)
        self.return_state = self.game_info.get(c.CUSTOM_LEVEL_RETURN, c.MAIN_MENU)
        
        # Load the custom level
        self.level_path = self.game_info.get('custom_level_path', None)
        self.tile_size = 43
        self.grid_height = 13
        
        if self.level_path and os.path.exists(self.level_path):
            self.load_level()
        else:
            # Default empty level
            self.level_data = None
            self.grid_width = 50
        
        self.setup_background()
        self.setup_world_images()
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
    
    def load_level(self):
        """Load level data from JSON file"""
        with open(self.level_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.level_data = data.get('tiles', None)
        self.grid_width = data.get('width', 50)
        self.grid_height = data.get('height', 13)
        self.tile_size = data.get('tile_size', 43)
    
    def setup_background(self):
        """Sets the background image, rect and scales it to the correct
        proportions"""
        # Calculate level width based on grid
        level_width = self.grid_width * self.tile_size
        level_height = c.SCREEN_HEIGHT
        
        # Create a simple sky blue background
        self.level = pg.Surface((level_width, level_height)).convert()
        self.level.fill(c.SKY_BLUE)
        self.level_rect = self.level.get_rect()
        
        self.background = self.level.copy()
        self.back_rect = self.background.get_rect()
        
        self.viewport = setup.SCREEN.get_rect(bottom=self.level_rect.bottom)
        self.viewport.x = self.game_info.get(c.CAMERA_START_X, 0)
    
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
        self.level_complete = False
    
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
                world_y = y * self.tile_size + 70  # Offset matching editor
                
                self.create_tile(tile_type, world_x, world_y, x, y)
    
    def create_tile(self, tile_type, world_x, world_y, grid_x, grid_y):
        """Create appropriate game object for tile type"""
        
        if tile_type == c.TILE_GROUND:
            # Create ground collider
            ground = collider.Collider(world_x, world_y, 
                                       self.tile_size, self.tile_size)
            self.ground_group.add(ground)
        
        elif tile_type == c.TILE_BRICK:
            # Create breakable brick
            brick = bricks.Brick(world_x, world_y)
            self.brick_group.add(brick)
        
        elif tile_type == c.TILE_COIN_BOX:
            # Upgrade box: mushroom for small Mario, fireflower for big Mario.
            box = coin_box.Coin_box(world_x, world_y, c.MUSHROOM, self.powerup_group)
            self.coin_box_group.add(box)
        
        elif tile_type == c.TILE_PIPE:
            # Create full-size pipe collider (same style as 1-1 pipes)
            pipe = collider.Collider(world_x, world_y,
                                    self.pipe_world_width, self.pipe_world_height)
            self.pipe_group.add(pipe)
        
        elif tile_type == c.TILE_GOOMBA:
            # Create goomba enemy
            goomba = enemies.Goomba()
            goomba.rect.x = world_x
            goomba.rect.bottom = world_y + self.tile_size
            self.enemy_group.add(goomba)
        
        elif tile_type == c.TILE_KOOPA:
            # Create koopa enemy
            koopa = enemies.Koopa()
            koopa.rect.x = world_x
            koopa.rect.bottom = world_y + self.tile_size
            self.enemy_group.add(koopa)
        
        elif tile_type == c.TILE_COIN:
            # Coin question box that yields coin when bumped.
            box = coin_box.Coin_box(world_x, world_y, c.COIN, self.coin_group)
            self.coin_box_group.add(box)
        
        elif tile_type == c.TILE_FLAG:
            # Create flag pole (only create one)
            if not self.flag_placed:
                self.setup_flag_pole(world_x, world_y)
                self.flag_placed = True

        elif tile_type == c.TILE_MUSHROOM:
            # Place a mushroom powerup tile (same class as question-box mushroom)
            item = powerups.Mushroom(world_x + self.tile_size // 2, world_y)
            item.rect.bottom = world_y + self.tile_size
            item.state = c.SLIDE
            self.powerup_group.add(item)

        elif tile_type == c.TILE_FIREFLOWER:
            # Place a fire flower powerup tile (same class as question-box fireflower)
            item = powerups.FireFlower(world_x + self.tile_size // 2, world_y)
            item.rect.bottom = world_y + self.tile_size
            item.state = c.RESTING
            self.powerup_group.add(item)
    
    def setup_flag_pole(self, tile_world_x, tile_world_y):
        """Create a flag pole using the same anchor logic as the editor preview."""
        # In editor, full flagpole image is 2x10 tiles and the selected tile is the bottom-left anchor.
        image_top = tile_world_y - (self.tile_size * 9)
        pole_x = tile_world_x + (self.tile_size - 2)
        pole_top = image_top + self.tile_size

        # Keep top clear for finial and avoid overlap with flag head.
        self.flag = flagpole.Flag(tile_world_x + self.tile_size, pole_top + 3)

        poles = [flagpole.Pole(pole_x, pole_top + i * self.tile_size)
                 for i in range(9)]

        finial = flagpole.Finial(tile_world_x + self.tile_size, pole_top)

        self.flag_pole_group.add(self.flag, finial, *poles)

        # Keep checkpoint aligned to actual pole x position.
        flag_check = checkpoint.Checkpoint(pole_x - 1, '11', 5, 6)
        self.check_point_group.add(flag_check)
    
    def setup_mario(self):
        """Places Mario at the beginning of the level"""
        self.mario = mario.Mario()
        self.mario.rect.x = self.viewport.x + 110
        self.mario.rect.bottom = c.GROUND_HEIGHT
    
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
        if keys[pg.K_ESCAPE]:
            self.exit_to_return_state()
            return

        self.game_info[c.CURRENT_TIME] = self.current_time = current_time
        self.handle_states(keys)
        self.check_if_time_out()
        self.blit_everything(surface)
        self.sound_manager.update(self.game_info, self.mario)
    
    def handle_states(self, keys):
        """If the level is in a FROZEN state, only mario will update"""
        if self.state == c.FROZEN:
            self.update_during_transition_state(keys)
        elif self.state == c.NOT_FROZEN:
            self.update_all_sprites(keys)
        elif self.state == c.IN_CASTLE:
            self.update_while_in_castle()
        elif self.state == c.FLAG_AND_FIREWORKS:
            self.update_flag_and_fireworks()
    
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
        self.overhead_info_display.update(self.game_info, self.mario)
    
    def check_if_mario_in_transition_state(self):
        """If mario is in a transition state, the level will be in a FREEZE state"""
        if self.mario.in_transition_state:
            self.game_info[c.LEVEL_STATE] = self.state = c.FROZEN
        elif self.mario.in_transition_state == False:
            if self.state == c.FROZEN:
                self.game_info[c.LEVEL_STATE] = self.state = c.NOT_FROZEN
    
    def update_all_sprites(self, keys):
        """Updates the location of all sprites on the screen."""
        self.mario.update(keys, self.game_info, self.powerup_group)
        for score_obj in self.moving_score_list:
            score_obj.update(self.moving_score_list, self.game_info)
        if self.flag_score:
            self.flag_score.update(None, self.game_info)
            self.check_to_add_flag_score()
        self.flag_pole_group.update()
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
        self.overhead_info_display.update(self.game_info, self.mario)
    
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
                self.create_flag_points()
                self.level_complete = True
                self.flag_timer = self.current_time
    
    def create_flag_points(self):
        """Creates the points that appear when Mario touches the flag pole"""
        x = self.flag.rect.x + 13
        y = c.GROUND_HEIGHT - 60
        mario_bottom = self.mario.rect.bottom
        
        if mario_bottom > (c.GROUND_HEIGHT - 40 - 40):
            self.flag_score = score.Score(x, y, 100, True)
            self.flag_score_total = 100
        elif mario_bottom > (c.GROUND_HEIGHT - 40 - 160):
            self.flag_score = score.Score(x, y, 400, True)
            self.flag_score_total = 400
        elif mario_bottom > (c.GROUND_HEIGHT - 40 - 240):
            self.flag_score = score.Score(x, y, 800, True)
            self.flag_score_total = 800
        elif mario_bottom > (c.GROUND_HEIGHT - 40 - 360):
            self.flag_score = score.Score(x, y, 2000, True)
            self.flag_score_total = 2000
        else:
            self.flag_score = score.Score(x, y, 5000, True)
            self.flag_score_total = 5000
    
    def check_to_add_flag_score(self):
        """Adds flag score to total score"""
        if self.flag_score.y_vel == 0:
            self.game_info[c.SCORE] += self.flag_score_total
            self.flag_score = None
    
    def adjust_sprite_positions(self):
        """Adjusts sprites by their x and y velocities and collisions"""
        self.adjust_mario_position()
        self.adjust_enemy_position()
        self.adjust_shell_position()
        self.adjust_powerup_position()
    
    def adjust_mario_position(self):
        """Adjusts Mario's position based on his x, y velocities and
        potential collisions"""
        self.last_x_position = self.mario.rect.right
        self.mario.rect.x += round(self.mario.x_vel)
        self.check_mario_x_collisions()
        
        if self.mario.in_transition_state == False:
            self.mario.rect.y += round(self.mario.y_vel)
            self.check_mario_y_collisions()
        
        if self.mario.rect.x < (self.viewport.x + 5):
            self.mario.rect.x = (self.viewport.x + 5)
    
    def check_mario_x_collisions(self):
        """Check for collisions when Mario moves horizontally"""
        collider_hit = pg.sprite.spritecollideany(self.mario, self.ground_step_pipe_group)
        brick = pg.sprite.spritecollideany(self.mario, self.brick_group)
        coin_box_hit = pg.sprite.spritecollideany(self.mario, self.coin_box_group)
        powerup = pg.sprite.spritecollideany(self.mario, self.powerup_group)
        
        if collider_hit:
            self.adjust_mario_for_x_collisions(collider_hit)
        if brick:
            self.adjust_mario_for_x_collisions(brick)
        if coin_box_hit:
            self.adjust_mario_for_x_collisions(coin_box_hit)
        
        # Check enemy collisions
        enemy = pg.sprite.spritecollideany(self.mario, self.enemy_group)
        if enemy:
            self.mario_enemy_collision(enemy)
        
        shell = pg.sprite.spritecollideany(self.mario, self.shell_group)
        if shell:
            self.mario_shell_collision(shell)

        if powerup:
            self.handle_mario_powerup_collision(powerup)
    
    def adjust_mario_for_x_collisions(self, collider_obj):
        """Adjust Mario's position after horizontal collision"""
        if self.mario.rect.x < collider_obj.rect.x:
            self.mario.rect.right = collider_obj.rect.left
        else:
            self.mario.rect.left = collider_obj.rect.right
        
        self.mario.x_vel = 0
    
    def check_mario_y_collisions(self):
        """Check for collisions when Mario moves vertically"""
        ground = pg.sprite.spritecollideany(self.mario, self.ground_step_pipe_group)
        brick = pg.sprite.spritecollideany(self.mario, self.brick_group)
        coin_box_hit = pg.sprite.spritecollideany(self.mario, self.coin_box_group)
        powerup = pg.sprite.spritecollideany(self.mario, self.powerup_group)
        
        # Check if falling
        if self.mario.y_vel > 0:
            if ground:
                self.adjust_mario_for_y_ground_collisions(ground)
            elif brick:
                self.adjust_mario_for_y_ground_collisions(brick)
            elif coin_box_hit:
                self.adjust_mario_for_y_ground_collisions(coin_box_hit)
            
            self.check_if_falling(ground, brick, coin_box_hit)
        
        # Check if jumping up
        elif self.mario.y_vel < 0:
            if brick:
                self.adjust_mario_for_y_brick_collisions(brick)
            elif coin_box_hit:
                self.adjust_mario_for_y_coin_box_collisions(coin_box_hit)
            elif ground:
                self.adjust_mario_for_y_ground_collisions(ground)

        if powerup:
            self.handle_mario_powerup_collision(powerup)

        # Match 1-1 behavior: still test for ledge fall even when y_vel == 0.
        self.test_if_mario_is_falling()
    
    def adjust_mario_for_y_ground_collisions(self, collider_obj):
        """Adjust Mario's position after vertical collision with ground"""
        if self.mario.y_vel > 0:
            self.mario.rect.bottom = collider_obj.rect.top
            self.mario.y_vel = 0
            if self.mario.state != c.FLAGPOLE:
                self.mario.state = c.WALK
        else:
            self.mario.rect.top = collider_obj.rect.bottom
            self.mario.y_vel = 7
    
    def adjust_mario_for_y_brick_collisions(self, brick):
        """Adjust Mario when hitting brick from below"""
        if self.mario.rect.centerx < brick.rect.left or \
           self.mario.rect.centerx > brick.rect.right:
            return
        
        self.mario.rect.top = brick.rect.bottom
        self.mario.y_vel = 7
        self.mario.state = c.FALL
        
        if brick.state == c.RESTING:
            if self.mario.big:
                brick.kill()
                self.brick_pieces_group.add(
                    bricks.BrickPiece(brick.rect.x, brick.rect.y - 5, -2, -12),
                    bricks.BrickPiece(brick.rect.right, brick.rect.y - 5, 2, -12),
                    bricks.BrickPiece(brick.rect.x, brick.rect.y + 5, -2, -6),
                    bricks.BrickPiece(brick.rect.right, brick.rect.y + 5, 2, -6))
            else:
                brick.start_bump(self.moving_score_list)
    
    def adjust_mario_for_y_coin_box_collisions(self, coin_box_hit):
        """Adjust Mario when hitting coin box from below"""
        if self.mario.rect.centerx < coin_box_hit.rect.left or \
           self.mario.rect.centerx > coin_box_hit.rect.right:
            return
        
        self.mario.rect.top = coin_box_hit.rect.bottom
        self.mario.y_vel = 7
        self.mario.state = c.FALL
        
        if coin_box_hit.state == c.RESTING:
            # Match 1-1: upgrade boxes switch between mushroom/fireflower by Mario size.
            if coin_box_hit.contents in (c.MUSHROOM, c.FIREFLOWER):
                if self.mario.big:
                    coin_box_hit.contents = c.FIREFLOWER
                else:
                    coin_box_hit.contents = c.MUSHROOM
            coin_box_hit.start_bump(self.moving_score_list)
    
    def check_if_falling(self, ground, brick, coin_box_hit):
        """Check if Mario should be in falling state"""
        if not any([ground, brick, coin_box_hit]):
            if self.mario.state != c.JUMP and self.mario.state != c.FLAGPOLE:
                self.mario.state = c.FALL


    def test_if_mario_is_falling(self):
        """Mirror Level1 ledge test so Mario drops when leaving platforms."""
        self.mario.rect.y += 1
        test_group = pg.sprite.Group(self.ground_step_pipe_group,
                                     self.brick_group,
                                     self.coin_box_group)

        if pg.sprite.spritecollideany(self.mario, test_group) is None:
            if self.mario.state not in (c.JUMP, c.DEATH_JUMP,
                                        c.SMALL_TO_BIG, c.BIG_TO_FIRE,
                                        c.BIG_TO_SMALL, c.FLAGPOLE,
                                        c.WALKING_TO_CASTLE,
                                        c.END_OF_LEVEL_FALL):
                self.mario.state = c.FALL
            elif self.mario.state in (c.WALKING_TO_CASTLE, c.END_OF_LEVEL_FALL):
                self.mario.state = c.END_OF_LEVEL_FALL

        self.mario.rect.y -= 1
    
    def mario_enemy_collision(self, enemy):
        """Handle collision between Mario and enemy"""
        if self.mario.invincible:
            enemy.kill()
            self.sprites_about_to_die_group.add(enemy)
            enemy.start_death_jump(c.RIGHT)
            return
        
        if self.mario.y_vel > 0:
            if self.mario.rect.bottom < enemy.rect.centery:
                setup.SFX['stomp'].play()
                self.game_info[c.SCORE] += 100
                self.moving_score_list.append(
                    score.Score(enemy.rect.centerx - self.viewport.x,
                                enemy.rect.y, 100))

                enemy.state = c.JUMPED_ON

                if enemy.name == c.GOOMBA:
                    enemy.kill()
                    enemy.death_timer = self.current_time
                    self.sprites_about_to_die_group.add(enemy)
                elif enemy.name == c.KOOPA:
                    enemy.kill()
                    self.shell_group.add(enemy)

                self.mario.rect.bottom = enemy.rect.top
                self.mario.state = c.JUMP
                self.mario.y_vel = -7
            else:
                if self.mario.big:
                    setup.SFX['pipe'].play()
                    self.mario.fire = False
                    self.mario.y_vel = -1
                    self.mario.state = c.BIG_TO_SMALL
                    self.convert_fireflowers_to_mushrooms()
                elif not self.mario.hurt_invincible:
                    self.mario.start_death_jump(self.game_info)
                    self.state = c.FROZEN
        else:
            if self.mario.big:
                setup.SFX['pipe'].play()
                self.mario.fire = False
                self.mario.y_vel = -1
                self.mario.state = c.BIG_TO_SMALL
                self.convert_fireflowers_to_mushrooms()
            elif not self.mario.hurt_invincible:
                self.mario.start_death_jump(self.game_info)
                self.state = c.FROZEN
    
    def mario_shell_collision(self, shell):
        """Handle collision between Mario and shell"""
        if self.mario.invincible:
            shell.kill()
            self.sprites_about_to_die_group.add(shell)
            shell.start_death_jump(c.RIGHT)
            return
        
        if shell.state == c.SHELL_SLIDE:
            if self.mario.y_vel > 0 and self.mario.rect.bottom < shell.rect.centery:
                shell.state = c.JUMPED_ON
                self.game_info[c.SCORE] += 400
                self.moving_score_list.append(
                    score.Score(self.mario.rect.centerx - self.viewport.x,
                                self.mario.rect.y, 400))
                self.mario.y_vel = -7
            else:
                if self.mario.big and not self.mario.invincible:
                    self.mario.state = c.BIG_TO_SMALL
                    self.convert_fireflowers_to_mushrooms()
                elif not self.mario.hurt_invincible and not self.mario.invincible:
                    self.state = c.FROZEN
                    self.mario.start_death_jump(self.game_info)
        else:
            setup.SFX['kick'].play()
            if self.mario.rect.centerx < shell.rect.centerx:
                shell.direction = c.RIGHT
                shell.x_vel = 5
                shell.rect.left = self.mario.rect.right + 5
            else:
                shell.direction = c.LEFT
                shell.x_vel = -5
                shell.rect.right = self.mario.rect.left - 5
            shell.state = c.SHELL_SLIDE


    def handle_mario_powerup_collision(self, powerup):
        """Handle Mario collecting powerups (mirrors 1-1 core behavior)."""
        if powerup.name == c.STAR:
            setup.SFX['powerup'].play()
            self.game_info[c.SCORE] += 1000
            self.moving_score_list.append(
                score.Score(self.mario.rect.centerx - self.viewport.x,
                            self.mario.rect.y, 1000))
            self.mario.invincible = True
            self.mario.invincible_start_timer = self.current_time

        elif powerup.name == c.MUSHROOM:
            setup.SFX['powerup'].play()
            self.game_info[c.SCORE] += 1000
            self.moving_score_list.append(
                score.Score(self.mario.rect.centerx - self.viewport.x,
                            self.mario.rect.y - 20, 1000))

            if not self.mario.big:
                self.mario.y_vel = -1
                self.mario.state = c.SMALL_TO_BIG
                self.mario.in_transition_state = True
                self.convert_mushrooms_to_fireflowers()

        elif powerup.name == c.LIFE_MUSHROOM:
            self.game_info[c.LIVES] += 1
            self.moving_score_list.append(
                score.Score(powerup.rect.right - self.viewport.x,
                            powerup.rect.y,
                            c.ONEUP))
            setup.SFX['one_up'].play()

        elif powerup.name == c.FIREFLOWER:
            setup.SFX['powerup'].play()
            self.game_info[c.SCORE] += 1000
            self.moving_score_list.append(
                score.Score(self.mario.rect.centerx - self.viewport.x,
                            self.mario.rect.y, 1000))

            if self.mario.big and not self.mario.fire:
                self.mario.state = c.BIG_TO_FIRE
                self.mario.in_transition_state = True
            elif not self.mario.big:
                self.mario.state = c.SMALL_TO_BIG
                self.mario.in_transition_state = True
                self.convert_mushrooms_to_fireflowers()

        if powerup.name != c.FIREBALL:
            powerup.kill()


    def convert_mushrooms_to_fireflowers(self):
        """When Mario becomes big, upgrade box rewards become fireflowers."""
        for brick in self.brick_group:
            if brick.contents == c.MUSHROOM:
                brick.contents = c.FIREFLOWER
        for box in self.coin_box_group:
            if box.contents == c.MUSHROOM:
                box.contents = c.FIREFLOWER


    def convert_fireflowers_to_mushrooms(self):
        """When Mario becomes small, upgrade box rewards become mushrooms."""
        for brick in self.brick_group:
            if brick.contents == c.FIREFLOWER:
                brick.contents = c.MUSHROOM
        for box in self.coin_box_group:
            if box.contents == c.FIREFLOWER:
                box.contents = c.MUSHROOM
    
    def adjust_enemy_position(self):
        """Adjust enemy positions"""
        for enemy in self.enemy_group:
            enemy.rect.x += enemy.x_vel
            self.check_enemy_x_collisions(enemy)
            enemy.rect.y += enemy.y_vel
            self.check_enemy_y_collisions(enemy)
    
    def check_enemy_x_collisions(self, enemy):
        """Check enemy horizontal collisions"""
        collider_hit = pg.sprite.spritecollideany(enemy, self.ground_step_pipe_group)
        if not collider_hit:
            collider_hit = pg.sprite.spritecollideany(enemy, self.brick_group)
        if not collider_hit:
            collider_hit = pg.sprite.spritecollideany(enemy, self.coin_box_group)

        enemy_hit = None
        for other_enemy in self.enemy_group:
            if other_enemy != enemy and enemy.rect.colliderect(other_enemy.rect):
                enemy_hit = other_enemy
                break

        if collider_hit:
            if enemy.direction == c.LEFT:
                enemy.rect.left = collider_hit.rect.right
                enemy.direction = c.RIGHT
            else:
                enemy.rect.right = collider_hit.rect.left
                enemy.direction = c.LEFT
            enemy.x_vel = -enemy.x_vel
        elif enemy_hit:
            if enemy.rect.centerx < enemy_hit.rect.centerx:
                enemy.rect.right = enemy_hit.rect.left
            else:
                enemy.rect.left = enemy_hit.rect.right

            enemy.direction = c.LEFT if enemy.direction == c.RIGHT else c.RIGHT
            enemy.x_vel = -enemy.x_vel

            enemy_hit.direction = c.LEFT if enemy_hit.direction == c.RIGHT else c.RIGHT
            enemy_hit.x_vel = -enemy_hit.x_vel
    
    def check_enemy_y_collisions(self, enemy):
        """Check enemy vertical collisions"""
        collider_hit = pg.sprite.spritecollideany(enemy, self.ground_step_pipe_group)
        if not collider_hit:
            collider_hit = pg.sprite.spritecollideany(enemy, self.brick_group)
        if not collider_hit:
            collider_hit = pg.sprite.spritecollideany(enemy, self.coin_box_group)

        if collider_hit:
            enemy.rect.bottom = collider_hit.rect.top
            enemy.y_vel = 0
        else:
            enemy.y_vel = 7
    
    def adjust_shell_position(self):
        """Adjust shell positions"""
        for shell in self.shell_group:
            shell.rect.x += shell.x_vel
            self.check_shell_x_collisions(shell)
            shell.rect.y += shell.y_vel
            self.check_shell_y_collisions(shell)


    def check_shell_x_collisions(self, shell):
        """Shell collisions along x axis with terrain, blocks and enemies."""
        collider = pg.sprite.spritecollideany(shell, self.ground_step_pipe_group)
        if not collider:
            collider = pg.sprite.spritecollideany(shell, self.brick_group)
        if not collider:
            collider = pg.sprite.spritecollideany(shell, self.coin_box_group)

        enemy_hit = pg.sprite.spritecollideany(shell, self.enemy_group)

        if collider:
            setup.SFX['bump'].play()
            if shell.x_vel > 0:
                shell.direction = c.LEFT
                shell.rect.right = collider.rect.left
            else:
                shell.direction = c.RIGHT
                shell.rect.left = collider.rect.right
            shell.x_vel *= -1

        if enemy_hit:
            setup.SFX['kick'].play()
            self.game_info[c.SCORE] += 100
            self.moving_score_list.append(
                score.Score(enemy_hit.rect.right - self.viewport.x,
                            enemy_hit.rect.y, 100))
            enemy_hit.kill()
            self.sprites_about_to_die_group.add(enemy_hit)
            enemy_hit.start_death_jump(shell.direction)


    def check_shell_y_collisions(self, shell):
        """Shell collisions along y axis."""
        collider = pg.sprite.spritecollideany(shell, self.ground_step_pipe_group)
        if not collider:
            collider = pg.sprite.spritecollideany(shell, self.brick_group)
        if not collider:
            collider = pg.sprite.spritecollideany(shell, self.coin_box_group)

        if collider:
            shell.y_vel = 0
            shell.rect.bottom = collider.rect.top
            shell.state = c.SHELL_SLIDE
        else:
            shell.rect.y += 1
            test_group = pg.sprite.Group(self.ground_step_pipe_group,
                                         self.brick_group,
                                         self.coin_box_group)
            if pg.sprite.spritecollideany(shell, test_group) is None:
                shell.state = c.FALL
            shell.rect.y -= 1
    
    def adjust_powerup_position(self):
        """Adjust powerup positions with full ledge and block collisions."""
        for powerup in self.powerup_group:
            if powerup.name in (c.MUSHROOM, c.LIFE_MUSHROOM):
                self.adjust_mushroom_position(powerup)
            elif powerup.name == c.STAR:
                # Keep current lightweight behavior for stars.
                if powerup.state == c.BOUNCE:
                    powerup.rect.x += powerup.x_vel
                    powerup.rect.y += powerup.y_vel
            elif powerup.name == c.FIREBALL:
                self.adjust_fireball_position(powerup)


    def adjust_mushroom_position(self, mushroom):
        """Move mushroom and handle collisions like in 1-1."""
        if mushroom.state != c.REVEAL:
            mushroom.rect.x += mushroom.x_vel
            self.check_mushroom_x_collisions(mushroom)

            mushroom.rect.y += mushroom.y_vel
            self.check_mushroom_y_collisions(mushroom)


    def check_mushroom_x_collisions(self, mushroom):
        """Mushroom collisions along x axis."""
        collider = pg.sprite.spritecollideany(mushroom, self.ground_step_pipe_group)
        brick = pg.sprite.spritecollideany(mushroom, self.brick_group)
        coin_box_hit = pg.sprite.spritecollideany(mushroom, self.coin_box_group)

        if collider:
            self.adjust_mushroom_for_collision_x(mushroom, collider)
        elif brick:
            self.adjust_mushroom_for_collision_x(mushroom, brick)
        elif coin_box_hit:
            self.adjust_mushroom_for_collision_x(mushroom, coin_box_hit)


    def check_mushroom_y_collisions(self, mushroom):
        """Mushroom collisions along y axis."""
        collider = pg.sprite.spritecollideany(mushroom, self.ground_step_pipe_group)
        brick = pg.sprite.spritecollideany(mushroom, self.brick_group)
        coin_box_hit = pg.sprite.spritecollideany(mushroom, self.coin_box_group)

        if collider:
            self.adjust_mushroom_for_collision_y(mushroom, collider)
        elif brick:
            self.adjust_mushroom_for_collision_y(mushroom, brick)
        elif coin_box_hit:
            self.adjust_mushroom_for_collision_y(mushroom, coin_box_hit)
        else:
            self.check_if_sprite_falling(mushroom, self.ground_step_pipe_group)
            self.check_if_sprite_falling(mushroom, self.brick_group)
            self.check_if_sprite_falling(mushroom, self.coin_box_group)


    def adjust_mushroom_for_collision_x(self, item, collider_obj):
        """Reverse mushroom direction on horizontal collision."""
        if item.rect.x < collider_obj.rect.x:
            item.rect.right = collider_obj.rect.x
            item.direction = c.LEFT
        else:
            item.rect.x = collider_obj.rect.right
            item.direction = c.RIGHT


    def adjust_mushroom_for_collision_y(self, item, collider_obj):
        """Snap mushroom to surface and resume slide behavior."""
        item.rect.bottom = collider_obj.rect.y
        item.state = c.SLIDE
        item.y_vel = 0


    def check_if_sprite_falling(self, sprite, sprite_group):
        """Set sprite to FALL if there is no support directly under it."""
        sprite.rect.y += 1
        if pg.sprite.spritecollideany(sprite, sprite_group) is None:
            if sprite.state != c.JUMP:
                sprite.state = c.FALL
        sprite.rect.y -= 1


    def adjust_fireball_position(self, fireball):
        """Move fireball and apply collisions (matching 1-1 behavior)."""
        if fireball.state == c.FLYING:
            fireball.rect.x += fireball.x_vel
            self.check_fireball_x_collisions(fireball)
            fireball.rect.y += fireball.y_vel
            self.check_fireball_y_collisions(fireball)
        elif fireball.state == c.BOUNCING:
            fireball.rect.x += fireball.x_vel
            self.check_fireball_x_collisions(fireball)
            fireball.rect.y += fireball.y_vel
            self.check_fireball_y_collisions(fireball)
            fireball.y_vel += fireball.gravity
        self.delete_if_off_screen(fireball)


    def bounce_fireball(self, fireball):
        """Simulate fireball bounce off ground."""
        fireball.y_vel = -8
        fireball.x_vel = 15 if fireball.direction == c.RIGHT else -15

        if fireball in self.powerup_group:
            fireball.state = c.BOUNCING


    def check_fireball_x_collisions(self, fireball):
        """Fireball collisions along x axis."""
        collide_group = pg.sprite.Group(self.ground_group,
                                        self.pipe_group,
                                        self.step_group,
                                        self.coin_box_group,
                                        self.brick_group)

        collider_obj = pg.sprite.spritecollideany(fireball, collide_group)

        if collider_obj:
            fireball.kill()
            self.sprites_about_to_die_group.add(fireball)
            fireball.explode_transition()


    def check_fireball_y_collisions(self, fireball):
        """Fireball collisions along y axis."""
        collide_group = pg.sprite.Group(self.ground_group,
                                        self.pipe_group,
                                        self.step_group,
                                        self.coin_box_group,
                                        self.brick_group)

        collider_obj = pg.sprite.spritecollideany(fireball, collide_group)
        enemy = pg.sprite.spritecollideany(fireball, self.enemy_group)
        shell = pg.sprite.spritecollideany(fireball, self.shell_group)

        if collider_obj and (fireball in self.powerup_group):
            fireball.rect.bottom = collider_obj.rect.y
            self.bounce_fireball(fireball)
        elif enemy:
            self.fireball_kill(fireball, enemy)
        elif shell:
            self.fireball_kill(fireball, shell)


    def fireball_kill(self, fireball, enemy):
        """Kill enemy when hit by fireball."""
        setup.SFX['kick'].play()
        self.game_info[c.SCORE] += 100
        self.moving_score_list.append(
            score.Score(enemy.rect.centerx - self.viewport.x,
                        enemy.rect.y, 100))
        fireball.kill()
        enemy.kill()
        self.sprites_about_to_die_group.add(enemy, fireball)
        enemy.start_death_jump(fireball.direction)
        fireball.explode_transition()


    def delete_if_off_screen(self, enemy):
        """Remove sprites that are far outside the active viewport."""
        if enemy.rect.x < (self.viewport.x - 300):
            enemy.kill()
        elif enemy.rect.y > self.viewport.bottom:
            enemy.kill()
        elif enemy.state == c.SHELL_SLIDE:
            if enemy.rect.x > (self.viewport.right + 500):
                enemy.kill()
    
    def update_viewport(self):
        """Update the viewport/camera position"""
        third = self.viewport.x + self.viewport.w // 3
        mario_center = self.mario.rect.centerx
        
        if self.mario.x_vel > 0 and mario_center > third:
            self.viewport.x += round(self.mario.x_vel)
        
        # Keep viewport in bounds
        max_x = self.level_rect.w - self.viewport.w
        self.viewport.x = min(self.viewport.x, max_x)
        self.viewport.x = max(self.viewport.x, 0)
    
    def check_flag(self):
        """Check if Mario has reached the flag"""
        if self.mario.state == c.FLAGPOLE:
            if self.mario.rect.bottom >= c.GROUND_HEIGHT:
                self.mario.state = c.WALKING_TO_CASTLE

        if self.level_complete and self.flag_timer:
            if (self.current_time - self.flag_timer) > 1200:
                self.exit_to_return_state()
    
    def check_for_mario_death(self):
        """Check if Mario has died"""
        if self.mario.rect.top > c.SCREEN_HEIGHT:
            self.mario.dead = True
            self.game_info[c.MARIO_DEAD] = True
        
        if self.mario.dead:
            if self.death_timer == 0:
                self.death_timer = self.current_time
            elif (self.current_time - self.death_timer) > 3000:
                if self.return_state == c.LEVEL_EDITOR:
                    self.exit_to_return_state()
                else:
                    self.game_info[c.LIVES] -= 1
                    if self.game_info[c.LIVES] <= 0:
                        self.next = c.GAME_OVER
                    else:
                        self.next = c.MAIN_MENU
                    self.done = True
    
    def check_if_time_out(self):
        """Check if time has run out"""
        if self.overhead_info_display.time <= 0:
            self.mario.start_death_jump(self.game_info)
            self.state = c.FROZEN
    
    def update_while_in_castle(self):
        """Updates when Mario is in the castle"""
        self.overhead_info_display.update(self.game_info, self.mario)
        if self.overhead_info_display.state == c.END_OF_LEVEL:
            self.exit_to_return_state()
    
    def update_flag_and_fireworks(self):
        """Updates during flag and fireworks"""
        self.overhead_info_display.update(self.game_info, self.mario)
    
    def blit_everything(self, surface):
        """Blit all sprites to the screen"""
        # Mirror Level1 rendering flow: draw world to level surface, then crop by viewport.
        self.level.blit(self.background, self.viewport, self.viewport)
        self.draw_ground_tiles(self.level)

        # Keep draw order aligned with 1-1 so reveal animation is masked by the box.
        self.powerup_group.draw(self.level)
        self.coin_group.draw(self.level)
        self.brick_group.draw(self.level)
        self.coin_box_group.draw(self.level)
        self.brick_pieces_group.draw(self.level)
        self.enemy_group.draw(self.level)
        self.shell_group.draw(self.level)
        self.sprites_about_to_die_group.draw(self.level)
        self.flag_pole_group.draw(self.level)
        self.mario_and_enemy_group.draw(self.level)

        surface.blit(self.level, (0, 0), self.viewport)

        for score_obj in self.moving_score_list:
            score_obj.draw(surface)
        if self.flag_score:
            self.flag_score.draw(surface)

        self.overhead_info_display.draw(surface)
    
    def draw_ground_tiles(self, surface):
        """Draw visible ground tiles"""
        if self.level_data is None:
            return
        
        sprite_sheet = setup.GFX['tile_set']
        
        # Calculate visible range
        start_x = max(0, self.viewport.x // self.tile_size)
        end_x = min(self.grid_width, 
                   (self.viewport.x + c.SCREEN_WIDTH) // self.tile_size + 1)
        
        for y in range(self.grid_height):
            for x in range(start_x, end_x):
                tile_type = self.level_data[y][x]
                
                if tile_type == c.TILE_GROUND:
                    # Draw using world coordinates onto the level surface.
                    world_x = x * self.tile_size
                    world_y = y * self.tile_size + 70
                    
                    # Get ground tile image
                    tile_img = pg.Surface([16, 16])
                    tile_img.blit(sprite_sheet, (0, 0), (0, 16, 16, 16))
                    tile_img.set_colorkey(c.BLACK)
                    tile_img = pg.transform.scale(tile_img, 
                                                 (self.tile_size, self.tile_size))
                    surface.blit(tile_img, (world_x, world_y))
                
                elif tile_type == c.TILE_PIPE:
                    # Draw as a complete pipe in world coordinates.
                    world_x = x * self.tile_size
                    world_y = y * self.tile_size + 70

                    surface.blit(self.pipe_world_image, (world_x, world_y))


    def exit_to_return_state(self):
        """Exit custom level to its caller state and stop music."""
        self.sound_manager.stop_music()
        self.next = self.return_state
        self.done = True
