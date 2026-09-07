from ..entity import Entity
from ..config import TILE_SIZE
from ..timer import Timer
from ..particle import ParticleGenerator
from pygame import Vector2 as Vec2
import random
import pygame

def vector_to_key(vec):
    return (int(vec[0]), int(vec[1]))

class Tile(Entity):

    def __init__(self, grid_pos, name, action=None, collides=True, allow_stretch=True, placement_priority=0):
        self.grid_pos = grid_pos
        pos = grid_pos[0]*TILE_SIZE[0], grid_pos[1]*TILE_SIZE[1]
        super().__init__(pos, name, action)
        self.collides = collides
        self.allow_stretch = allow_stretch
        self.stepped_on = False
        self.stretch = Vec2(0)
        self.stretch_vel = Vec2(0)
        self.placement_priority = placement_priority
        self.stepping_tile = None

    def __repr__(self):
        return f'<{self.name},{self.grid_pos}>'

    @property
    def end_pos(self):
        return Vec2(self.grid_pos[0]*TILE_SIZE[0], self.grid_pos[1]*TILE_SIZE[1])

    @property
    def pull_strength(self):
        return 0.3*(-self.pos+self.end_pos)

    @property
    def img(self):
        base_img = super().img
        if not self.allow_stretch: return base_img
        ratio = [
                (1+abs(self.stretch[0])),
                (1+abs(self.stretch[1]))
                ]
        ratio = (ratio[0]/ratio[1],
                 ratio[1]/ratio[0])  # Stretch one axis while compressing the other
        return pygame.transform.scale(base_img,
                                      (base_img.get_width()*ratio[0],
                                       base_img.get_height()*ratio[1])
                                      )

    def render(self, surf, offset=(0, 0)):
        offset = pygame.Vector2(offset)
        # To keep it centered when stretching
        offset -= 0.5*(Vec2(self.img.get_size()) - super().img.get_size())  
        # To render using the topleft of the animation rect
        if self.animation.action is not None:
            offset -= self.animation.rect.topleft
        #     pygame.draw.rect(surf, (255, 0, 0), (self.rect[0]+offset[0], self.rect[1]+offset[1], *self.rect.size), width=1)
        return super().render(surf, offset)

    def update(self, game):
        self.real_pos += self.pull_strength

        # self.stretch_vel += 0.03*self.pull_strength
        # self.stretch += self.stretch_vel 
        # self.stretch_vel += 0.3*-self.stretch
        # self.stretch_vel *= 0.8

        self.stretch = self.pull_strength*0.1


        return super().update()

    def on_fg_contact(self, level, blocking_tile):
        """When I move on a fg tile that doesn\'t move.
        Returns True if fg_tiles can move to my pos"""
        return False

    def on_bg_contact(self, level, blocking_tile):
        """When I move on a bg tile that doesn\'t move.
        Returns True if fg_tiles can move to my pos"""
        return False

    def on_fg_move_collision(self, level, moving_tiles, desired_grid_pos):
        """When several tiles want to move to the same spot."""
        return False

    def on_fg_place_collision(self, level, blocking_tile):
        """When I am request to be placed on a tile that already has a fg_tile
        Return True if I still get placed."""
        return False

    def on_stepped(self, level, stepping_tile):
        self.stepping_tile = stepping_tile
        self.stepped_on = True

    def on_stepped_released(self, level):
        self.stepping_tile = None
        self.stepped_on = False

    def on_removal(self, level):
        level.request_fg_delete(self.grid_pos)

class RotatedTile(Tile):

    img_cache = {}

    def __init__(self, *args, **kwargs):
        self.look_angle = random.choice((0, 90, 180, 270))
        super().__init__(*args, **kwargs)

    @property
    def img(self):
        key = (self.name, self.look_angle)
        if key not in self.img_cache:
            self.img_cache[key] = pygame.transform.rotate(super().img, self.look_angle)
        return self.img_cache[key]
        

class Slime(Tile):

    DIRECTION_MAP = {
            ('w', 'up'): (0, -1),
            ('s', 'down'): (0, 1),
            ('d', 'right'): (1, 0),
            ('a', 'left'): (-1, 0),
            }

    @classmethod
    def init_regular_slime(cls, x, y):
        return cls((x, y), 'regular_slime', action='idle', weight=1)

    @classmethod
    def init_heavy_slime(cls, x, y):
        return cls((x, y), 'heavy_slime', action='idle', weight=2)

    def __init__(self, *args, weight=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.weight = weight
        self.move_timer = Timer(5, True)
        self.enable_movement()

    def disable_movement(self):
        self.movement_enabled = False

    def enable_movement(self):
        self.movement_enabled = True

    def update(self, game):
        super().update(game)

        level = game.game_map.level
        
        if self.movement_enabled:
            move_direction = None
            for keys, looped_direction in Slime.DIRECTION_MAP.items():
                for k in keys:

                    if game.inputs['held'].get('left shift'):
                        if game.inputs['held'].get(k) and self.move_timer.done:
                            self.move_timer.reset()
                            move_direction = looped_direction
                            break

                    elif game.inputs['pressed'].get(k):
                        move_direction = looped_direction
                        break

            if move_direction:
                level.notify_player_moved()
                desired_pos = Vec2(self.grid_pos) + move_direction
                level.request_fg_move(self.grid_pos, desired_pos)

        self.move_timer.update()

    def can_merge(self, tile):
        if not isinstance(tile, Slime):
            return False
        if tile.weight > 1:
            return False
        if self.weight > 1:
            return False
        return True
    
    def on_fg_contact(self, level, blocking_tile):
        if not self.can_merge(blocking_tile): return False
        level.request_fg_delete(self.grid_pos)
        level.request_swap(blocking_tile.grid_pos, Slime.init_heavy_slime(*blocking_tile.grid_pos))
        level.play_sound(f'merge', f'_{random.randint(1, 3)}.wav')
        return True  # Give permission for the guy behind me to go

    def on_fg_move_collision(self, level, moving_tiles, desired_grid_pos):
        if len(moving_tiles) != 2: return False
        
        # Attempt at making mergin work when conveyor slime and other slime move to the same tile
        # if self is level.fg_tiles.get(moving_tiles[0]):
        #     moving_tile_coord = moving_tiles[1]
        # else:
        #     moving_tile_coord = moving_tiles[0]
        #
        # moving_tile = level.fg_tiles[moving_tile_coord]
        #
        # if self.can_merge(moving_tile):
        #     level.request_fg_delete(moving_tile_coord)
        #     level.request_swap(self.grid_pos, Slime.init_heavy_slime(*self.grid_pos))
        #     level.play_sound(f'merge', f'_{random.randint(1, 3)}.wav')
        #     return True
        # else:
        #     return isinstance(level.bg_tiles[moving_tile_coord], Conveyor)

        if self is level.fg_tiles.get(moving_tiles[0]):
            moving_tile_coord = moving_tiles[1]
        else:
            moving_tile_coord = moving_tiles[0]

        moving_tile = level.fg_tiles[moving_tile_coord]
        # Give myself permission to go if the other slime is on conveyor
        # So non conveyor slime has more priority
        return isinstance(level.bg_tiles[moving_tile_coord], Conveyor)  

    def on_removal(self, level):
        super().on_removal(level)
        gen = ParticleGenerator.from_template(TILE_SIZE[0]*Vec2(self.grid_pos)+0.5*Vec2(TILE_SIZE), 'smoke')
        level.particle_gens.append(gen)
        gen = ParticleGenerator.from_template(TILE_SIZE[0]*Vec2(self.grid_pos)+0.5*Vec2(TILE_SIZE), 'slime')
        level.particle_gens.append(gen)
        if self.weight > 1:
            particle = "dead heavy slime"
        else:
            particle = "dead regular slime"
        gen = ParticleGenerator.from_template(TILE_SIZE[0]*Vec2(self.grid_pos)+0.5*Vec2(TILE_SIZE), particle)
        level.particle_gens.append(gen)

class PressurePlate(Tile):

    def __init__(self, pos):
        super().__init__(pos, 'pressure_plate', action='up', collides=False)
        
    def on_stepped(self, level, tile):
        if tile.weight > 1:
            if not self.stepped_on:
                level.play_sound('pressure_plate', suffix=f'_{random.randint(1,3)}.wav')
            super().on_stepped(level, tile)
            self.animation.set_action('down')
        else:
            if self.stepped_on:
                self.on_stepped_released(level)

    def on_stepped_released(self, level):
        super().on_stepped_released(level)
        self.animation.set_action('up')

class Spikes(Tile):
    def __init__(self, pos, action, triggers):
        super().__init__(pos, 'spikes', action=action, collides=False, placement_priority=1)
        self.triggers = triggers
        self.original_action = action

        self.first_update = False

    def update(self, game):
        level = game.game_map.level

        # On the first update, make sure the spike is stored in the right fg/bg
        if not self.first_update:
            self.first_update = True
            self.set_action(level, self.animation.action, force=True)

        super().update(game)
        triggered = all([level.bg_tiles[trigger_tile].stepped_on for trigger_tile in self.triggers])
        if triggered:
            if self.animation.action == self.original_action:
                if self.animation.action == "down":
                    self.set_action(level, 'up')
                else:
                    self.set_action(level, 'down')
        else:
            self.set_action(level, self.original_action)

    def set_action(self, level, action, force=False):
        if self.animation.action == action and not force: return
        self.animation.set_action(action)
        if action == 'up':
            # Place spike on fg with a ground bg tile
            level.request_bg_set(self.grid_pos, Tile(self.grid_pos, 'tile_00'))
            level.request_fg_place(self, self.grid_pos)
        elif action == 'down':
            # Delete spike from fg and set bg to the spike
            level.request_fg_delete(self.grid_pos)
            level.request_bg_set(self.grid_pos, self)

    def on_fg_place_collision(self, level, blocking_tile):
        # When a slime stops the spike from rising up
        gen = ParticleGenerator.from_template(TILE_SIZE[0]*Vec2(self.grid_pos)+0.5*Vec2(TILE_SIZE), 'smoke')
        level.particle_gens.append(gen)
        gen = ParticleGenerator.from_template(TILE_SIZE[0]*Vec2(self.grid_pos)+0.5*Vec2(TILE_SIZE), 'slime')
        level.particle_gens.append(gen)
        if blocking_tile.weight > 1:
            particle = "dead heavy slime"
        else:
            particle = "dead regular slime"
        gen = ParticleGenerator.from_template(TILE_SIZE[0]*Vec2(self.grid_pos)+0.5*Vec2(TILE_SIZE), particle)
        level.particle_gens.append(gen)

        return True  # Replace the slime with the spike

class Arrow(Tile):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, allow_stretch=False)  # Arrow looks bad when it gets stretched
    
    def update(self, game):
        super().update(game)
        level = game.game_map.level
        if level.player_moved:
            level.request_fg_move(self.grid_pos, self.grid_pos+Vec2(1,0))
            # import pprint
            # pprint.pprint(level.fg_tiles)

    def on_fg_move_collision(self, level, moving_tiles, desired_grid_pos):
        for moving_tile in moving_tiles:
            level.fg_tiles[moving_tile].on_removal(level)
        return True

    def on_fg_contact(self, level, blocking_tile):
        if isinstance(blocking_tile, Slime):
            level.fg_tiles[vector_to_key(blocking_tile.grid_pos)].on_removal(level)
            return True
        else:
            return False

    def on_bg_contact(self, level, blocking_tile):
        level.fg_tiles[vector_to_key(self.grid_pos)].on_removal(level)
        gen = ParticleGenerator.from_template(TILE_SIZE[0]*Vec2(self.grid_pos)+0.5*Vec2(TILE_SIZE), 'smoke')
        level.particle_gens.append(gen)
        return True

    def on_fg_place_collision(self, level, blocking_tile):
        return self.on_fg_contact(level, blocking_tile)

class Bow(Tile):

    def __init__(self, grid_pos, name, shoot_direction):
        super().__init__(grid_pos, name, action='charging')
        self.shoot_direction = shoot_direction
        self.charge()

    def charge(self):
        self.charged = True
        self.animation.set_action('charging', reset=True)

    def shoot(self, level):
        arrow_grid_pos = self.grid_pos+self.shoot_direction
        arrow = Arrow(arrow_grid_pos, 'arrow', action='idle')
        level.request_fg_place(arrow, arrow_grid_pos)
        self.charged = False
        self.animation.set_action('shoot')

    def update(self, game):
        animation_done = super().update
        level = game.game_map.level
        if animation_done and self.animation.action == 'charging':
            self.animation.set_action('charged')

        if level.player_moved:
            if self.charged:
                self.shoot(level)
            else:
                self.charge()

class AttackTile(Tile):

    def __init__(self, pos):
        super().__init__(pos, 'attack_tile', action='up', collides=False)
        self.attack_timer = Timer(30)

    def update(self, game):
        self.attack_timer.update()
        return super().update(game)

    def on_stepped(self, level, tile):
        if tile.weight > 1:
            if not self.stepped_on:
                level.play_sound('pressure_plate', suffix=f'_{random.randint(1,3)}.wav')
            super().on_stepped(level, tile)
            self.animation.set_action('down')
        else:
            if self.stepped_on:
                self.on_stepped_released(level)

    def on_stepped_released(self, level):
        super().on_stepped_released(level)
        self.animation.set_action('up')

class Mine(Tile):

    def __init__(self, pos):
        super().__init__(pos, 'mine', action='up', collides=False)

    def on_stepped(self, level, tile):
        if tile.weight > 1:
            super().on_stepped(level, tile)
            level.play_sound('boom.wav')
            level.fg_tiles[vector_to_key(tile.grid_pos)].on_removal(level)
            gen = ParticleGenerator.from_template(TILE_SIZE[0]*Vec2(tile.grid_pos)+0.5*Vec2(TILE_SIZE), 'explosion smoke')
            level.particle_gens.append(gen)
            level.shake_screen(4)
            self.animation.set_action("debris")
            self.collides=True

class Conveyor(Tile):

    DIRECTION_MAP = {
            'right': (1, 0),
            'left': (-1, 0),
            'up': (0, -1),
            'down': (0, 1),
            }

    def __init__(self, pos, direction='right'):
        self.direction = direction
        super().__init__(pos, 'conveyor', action=f'{direction} idle', collides=False)

        self._img = super().img

        # base_img = super().img
        # if self.direction == 'right':
        #     self._img = base_img
        # elif self.direction == 'left':
        # self._img = pygame.transform.flip(base_img, True, False)
        # elif direction == 'up':
        #     self._img = pygame.transform.rotate(base_img, 90)
        # elif direction == 'down':
        #     self._img = pygame.transform.rotate(base_img, -90)


    @property
    def img(self):
        return self._img

    def on_stepped(self, level, tile):
        if isinstance(tile, Slime):
            tile.disable_movement()

        # Two slimes swapped places
        if self.stepping_tile and (tile is not self.stepping_tile):
            if isinstance(self.stepping_tile, Slime):
                self.stepping_tile.enable_movement()

        return super().on_stepped(level, tile)

    def on_stepped_released(self, level):
        if isinstance(self.stepping_tile, Slime): self.stepping_tile.enable_movement()
        return super().on_stepped_released(level)

    def update(self, game):
        level = game.game_map.level

        if level.player_moved:
            if self.stepping_tile:
                desired_pos = Vec2(self.grid_pos) + self.DIRECTION_MAP[self.direction]
                level.request_fg_move(self.grid_pos, desired_pos)

        animation_done = super().update(game)
        if self.animation.action.endswith('move'):
            self.animation.set_action(f'{self.direction} idle')
