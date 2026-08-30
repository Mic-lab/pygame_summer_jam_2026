from ..entity import Entity
from ..config import TILE_SIZE
from pygame import Vector2 as Vec2
from pygame.math import lerp

def vector_to_key(vec):
    return (int(vec[0]), int(vec[1]))

class Tile(Entity):

    def __init__(self, grid_pos, name, action=None, collides=True):
        self.grid_pos = grid_pos
        pos = grid_pos[0]*TILE_SIZE[0], grid_pos[1]*TILE_SIZE[1]
        super().__init__(pos, name, action)
        self.collides = collides
        self.stepped_on = False

    def update(self, game):
        return super().update()

    def on_contact(self, level, blocking_tile):
        """When I move on a a tile that doesn\'t move.
        Returns True if fg_tiles can move to my pos"""
        return False

    def on_stepped(self, level, blocking_tile):
        self.stepped_on = True

    def on_stepped_released(self, level):
        self.stepped_on = False

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
        self.old_pos = self.pos.copy()
        self.sprite_lerp = 1

    def update(self, game):
        super().update(game)

        level = game.game_map.level
        
        move_direction = None
        for keys, looped_direction in Slime.DIRECTION_MAP.items():
            for k in keys:
                if game.inputs['pressed'].get(k):
                    move_direction = looped_direction
                    break

        if move_direction and self.sprite_lerp == 1:
            self.old_pos.xy = self.pos.xy
            desired_pos = Vec2(self.grid_pos) + move_direction
            level.request_fg_move(vector_to_key(self.grid_pos), vector_to_key(desired_pos))
            self.sprite_lerp = 0

        self.sprite_lerp += 1 / 60 * 5 #to replace with dt?
        self.sprite_lerp = min(1, self.sprite_lerp)
    
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

    def render(self, surf, offset=(0, 0)):
        surf.blit(self.img, Vec2(lerp(self.old_pos.x, self.pos.x, self.sprite_lerp), lerp(self.old_pos.y, self.pos.y, self.sprite_lerp)) + offset)

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


