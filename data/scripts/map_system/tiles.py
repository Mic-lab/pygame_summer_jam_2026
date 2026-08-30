from ..entity import Entity
from ..config import TILE_SIZE
from ..timer import Timer
from pygame import Vector2 as Vec2
import random
import pygame

def vector_to_key(vec):
    return (int(vec[0]), int(vec[1]))

class Tile(Entity):

    def __init__(self, grid_pos, name, action=None, collides=True):
        self.grid_pos = grid_pos
        pos = grid_pos[0]*TILE_SIZE[0], grid_pos[1]*TILE_SIZE[1]
        super().__init__(pos, name, action)
        self.collides = collides
        self.stepped_on = False
        self.stretch = Vec2(0)
        self.stretch_vel = Vec2(0)

    @property
    def end_pos(self):
        return Vec2(self.grid_pos[0]*TILE_SIZE[0], self.grid_pos[1]*TILE_SIZE[1])

    @property
    def pull_strength(self):
        return 0.3*(-self.pos+self.end_pos)

    @property
    def img(self):
        base_img = super().img
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
        offset -= 0.5*(Vec2(self.img.get_size()) - super().img.get_size())
        return super().render(surf, offset)

    def update(self, game):
        self.real_pos += self.pull_strength

        # self.stretch_vel += 0.03*self.pull_strength
        # self.stretch += self.stretch_vel 
        # self.stretch_vel += 0.3*-self.stretch
        # self.stretch_vel *= 0.8

        self.stretch = self.pull_strength*0.1


        return super().update()

    def on_contact(self, level, blocking_tile):
        """When I move on a a tile that doesn\'t move.
        Returns True if fg_tiles can move to my pos"""
        return False

    def on_stepped(self, level, blocking_tile):
        self.stepped_on = True

    def on_stepped_released(self, level):
        self.stepped_on = False

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

    def update(self, game):
        super().update(game)

        level = game.game_map.level
        
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
            desired_pos = Vec2(self.grid_pos) + move_direction
            level.request_fg_move(vector_to_key(self.grid_pos), vector_to_key(desired_pos))

        self.move_timer.update()
    
    def on_contact(self, level, blocking_tile):
        if not isinstance(blocking_tile, Slime):
            return False
        if blocking_tile.weight > 1:
            return False
        if self.weight > 1:
            return False
        level.request_delete(self.grid_pos)
        level.request_swap(blocking_tile.grid_pos, Slime.init_heavy_slime(*blocking_tile.grid_pos))
        return True  # Give permission for the guy behind me to go

class PressurePlate(Tile):

    def __init__(self, pos):
        super().__init__(pos, 'pressure_plate', action='up', collides=False)

    def on_stepped(self, level, tile):
        if tile.weight > 1:
            super().on_stepped(level, tile)
            self.animation.set_action('down')
        else:
            if self.stepped_on:
                self.on_stepped_released(level)

    def on_stepped_released(self, level):
        super().on_stepped_released(level)
        self.animation.set_action('up')

class Arrow(Tile):
    pass
    
    # def update(self, game):
    #     super().update(game)

class Bow(Tile):

    def __init__(self, grid_pos, name):
        super().__init__(grid_pos, name, action='charging')
        self.shoot_direction = Vec2(1, 0)
        self.charge()

    def charge(self):
        self.charged = True
        self.animation.set_action('charging', reset=True)

    def update(self, game):
        animation_done = super().update
        level = game.game_map.level
        if animation_done and self.animation.action == 'charging':
            self.animation.set_action('charged')

        if self.charged:
            arrow_grid_pos = self.grid_pos+self.shoot_direction
            arrow = Arrow(arrow_grid_pos, 'arrow', action='idle')
            level.request_fg_place(arrow, vector_to_key(arrow_grid_pos))
            self.charged = False
            # TODO: Make level store player moved variable and use that to update arrow and Bow
