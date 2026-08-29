import pygame
from pygame import Vector2 as Vec2
from pathlib import Path
from .state import State
from ..button import Button
from ..font import fonts
from ..entity import Entity
from .. import colors

TILE_SIZE = (24, 24)

class Tile(Entity):
    
    def __init__(self, grid_pos, name, action=None):
        self.grid_pos = grid_pos
        pos = grid_pos[0]*TILE_SIZE[0], grid_pos[1]*TILE_SIZE[1]
        super().__init__(pos, name, action)

    # def update(self, game):
    #     return super().update()

class RegularSlime(Tile):

    DIRECTION_MAP = {
            ('w', 'up'): (0, -1),
            ('s', 'down'): (0, 1),
            ('d', 'right'): (1, 0),
            ('a', 'left'): (-1, 0),
            }

    def update(self, game):
        super().update()

        level = game.game_map.level
        
        move_direction = None
        for keys, looped_direction in RegularSlime.DIRECTION_MAP.items():
            for k in keys:
                if game.inputs['pressed'].get(k):
                    move_direction = looped_direction
                    break

        if move_direction:
            desired_pos = Vec2(self.grid_pos) + move_direction
            return {'desired_pos': desired_pos}

        
    def can_move(self, move_direction, level):
        return True

class Level:

    TILE_MAP = {
            '.': lambda x, y: Tile((x, y), 'ground'),
            '0': lambda x, y: Tile((x, y), 'wall'),
            's': lambda x, y: RegularSlime((x, y), 'regular_slime', action='idle'),
            }

    FG_TILES = ('s')

    def __init__(self, level_name):
        self.bg_tiles, self.fg_tiles, self.level_size = self.load_level(level_name)
        self.fg_movement_requests = {}

    def request_fg_move(self, current_pos, desired_pos):
        self.fg_movement_requests.setdefault(desired_pos, [])
        self.fg_movement_requests[desired_pos].append(current_pos)

    def _move_fg(self, current_pos, desired_pos):
        """Blindly moves foreground. No verification done to see if it's legal"""
        current_pos = tuple(current_pos)
        desired_pos = tuple(desired_pos)
        moved_tile = self.fg_tiles.pop(current_pos)
        moved_tile.grid_pos = desired_pos
        moved_tile.real_pos = (moved_tile.grid_pos[0]*TILE_SIZE[0], moved_tile.grid_pos[1]*TILE_SIZE[1])
        self.fg_tiles[desired_pos] = moved_tile

    def update(self, game):
        # for tile in self.bg_tiles:
        #     tile.update()
        for tile in self.fg_tiles:
            tile.update(game)

        for desired_pos, current_positions in self.fg_movement_requests:
            # Multiple fg tiles want to move to the same tile
            if len(current_positions): continue
            self._move_fg(current_positions[0], desired_pos)
        self.fg_movement_requests = []






        # I must get fg_tiles first because we may modify the keys while looping
        # fg_tiles = list(self.fg_tiles.values())
        #
        # tile_requests = []
        # for fg_tile in fg_tiles:
        #     tile_requests.append(fg_tile.update(game)

    def load_level(self, level_name):
        bg_tiles = {}
        fg_tiles = {}

        file_content = '''
000000000000000000000
0...................0
0...0.........ss....0
0...0........sss....0
0...00000.....ss....0
0...................0
0...................0
0...................0
0...................0
0...................0
000000000000000000000
        '''
        y = 0
        for line in file_content.split('\n'):
            if not line: continue

            x = 0
            for c in line:
                if c == ' ': continue

                tile = Level.TILE_MAP[c](x, y)

                if c in Level.FG_TILES:
                    fg_tiles[(x, y)] = [tile]
                    bg_tiles[(x, y)] = [Level.TILE_MAP['.'](x, y)]
                else:
                    bg_tiles[(x, y)] = [tile]

                x += 1

            y += 1
        
        level_size = (x, y)
        return bg_tiles, fg_tiles, level_size

    def render(self, surf):
        for tile_pos, tile in self.bg_tiles.items():
            tile.render(surf)

        for tile_pos, tile in self.fg_tiles.items():
            tile.render(surf)

class GameMap:

    def __init__(self):
        pass

    def load_level(self, level_name):
        self.level = Level(level_name)

    def update(self, game):
        self.level.update(game)

    def render(self, surf):
        
        self.level.render(surf)


class Game(State):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.game_map = GameMap()
        self.game_map.load_level('lol')


    def sub_update(self):
        self.game_surf.fill(colors.BLACK)

        self.game_map.update(self)
        self.game_map.render(self.game_surf)

