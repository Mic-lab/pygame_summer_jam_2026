import pygame
import copy
from pygame import Vector2 as Vec2
from pathlib import Path

from .. import config
from .state import State
from ..button import Button
from ..font import fonts
from ..entity import Entity
from .. import colors

TILE_SIZE = (24, 24)

def vector_to_key(vec):
    return (int(vec[0]), int(vec[1]))

class Tile(Entity):

    def __init__(self, grid_pos, name, action=None, collides=True):
        self.grid_pos = grid_pos
        pos = grid_pos[0]*TILE_SIZE[0], grid_pos[1]*TILE_SIZE[1]
        super().__init__(pos, name, action)
        self.collides = collides

    def on_contact(self, level, blocking_tile):
        return False

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

    def update(self, game):
        super().update()

        level = game.game_map.level
        
        move_direction = None
        for keys, looped_direction in Slime.DIRECTION_MAP.items():
            for k in keys:
                if game.inputs['pressed'].get(k):
                    move_direction = looped_direction
                    break

        if move_direction:
            desired_pos = Vec2(self.grid_pos) + move_direction
            level.request_fg_move(vector_to_key(self.grid_pos), vector_to_key(desired_pos))
        
    def on_contact(self, level, blocking_tile):
        level.request_delete(self.grid_pos)
        level.request_swap(blocking_tile.grid_pos, Slime.init_heavy_slime(*blocking_tile.grid_pos))
        return True  # The guy behind me can go

SOLID_TILE_MAPPINGS = [
    ("tile_16", set()),
    ("tile_02", {(0, 1)}),
    ("tile_03", {(-1, 0)}),
    ("tile_04", {(0, -1)}),
    ("tile_05", {(1, 0)}),
    ("tile_06", {(0, 1), (1, 0)}),
    ("tile_07", {(0, 1), (-1, 0)}),
    ("tile_08", {(0, -1), (-1, 0)}),
    ("tile_09", {(0, -1), (1, 0)}),
    ("tile_10", {(1, 0), (-1, 0)}),
    ("tile_11", {(0, -1), (0, 1)}),
    ("tile_12", {(1, 0), (-1, 0), (0, 1)}),
    ("tile_13", {(0, -1), (0, 1), (1, 0)}),
    ("tile_14", {(1, 0), (-1, 0), (0, -1)}),
    ("tile_15", {(0, -1), (0, 1), (-1, 0)})
]

WATER_TILE_MAPPINGS = [
    ("tile_31", set()),
    ("tile_17", {(-1, 0)}),
    ("tile_18", {(0, 1)}),
    ("tile_19", {(1, 0)}),
    ("tile_20", {(0, -1)}),
    ("tile_21", {(0, -1), (1, 0)}),
    ("tile_22", {(0, -1), (-1, 0)}),
    ("tile_23", {(0, 1), (1, 0)}),
    ("tile_24", {(0, 1), (-1, 0)}),
    ("tile_25", {(1, 0), (-1, 0)}),
    ("tile_26", {(0, -1), (0, 1)}),
    ("tile_27", {(0, -1), (0, 1), (1, 0)}),
    ("tile_28", {(0, -1), (1, 0), (-1, 0)}),
    ("tile_29", {(0, -1), (0, 1), (-1, 0)}),
    ("tile_30", {(0, 1), (1, 0), (-1, 0)})
]

def try_get_for_mapping(x:int, y:int, level:list[list]):
    try:
        return level[y][x]
    except IndexError:
        return None

def map_solid_tile(x:int, y:int, level:list[list]):
    neighbours = set()
    for x_offset, y_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        tile = try_get_for_mapping(x + x_offset, y + y_offset, level)
        if tile != "0" and tile != None:
            neighbours.add((x_offset, y_offset))

    for tile_name, neighbour_map in SOLID_TILE_MAPPINGS:
        if neighbour_map == neighbours:
            return Tile((x, y), tile_name)

    return Tile((x, y), "tile_00")

def map_water_tile(x:int, y:int, level:list[list]):
    neighbours = set()
    for x_offset, y_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        tile = try_get_for_mapping(x + x_offset, y + y_offset, level)
        if tile != "w" and tile != None:
            neighbours.add((x_offset, y_offset))

    for tile_name, neighbour_map in WATER_TILE_MAPPINGS:
        if neighbour_map == neighbours:
            return Tile((x, y), tile_name)

    return Tile((x, y), "tile_00")

class Level:
    TILE_MAP = {
            '.': lambda x, y: Tile((x, y), 'tile_00', collides=False),
            's': lambda x, y: Slime.init_regular_slime(x, y),
            }

    FG_TILES = ('s')

    def __init__(self, level_name):
        self.bg_tiles, self.fg_tiles, self.level_size = self.load_level(level_name)
        self.offset = 0.5*(Vec2(config.GAME_SIZE) - (TILE_SIZE[0]*self.level_size[0], TILE_SIZE[1]*self.level_size[1]))

        self.desired_to_current_requests = {}
        self.current_to_desired_requests = {}
        self.delete_requests = set()

    def request_fg_move(self, current_pos, desired_pos):
        desired_pos, current_pos = tuple(desired_pos), tuple(current_pos)
        self.desired_to_current_requests.setdefault(desired_pos, [])
        self.desired_to_current_requests[desired_pos].append(current_pos)
        self.current_to_desired_requests[current_pos] = desired_pos

    def request_delete(self, current_pos):
        self.delete_requests.add(current_pos)

    def request_swap(self, swapped_pos, new_tile):
        # NOTE: Swap happens after collisions after resolve_movement_requests
        self.fg_tiles[swapped_pos] = new_tile

    def _resolve_movement_request(self, current_pos, desired_pos, visited):
        """
        Returns True if it gives permission for other tiles to go to current_pos.
        """
        # NOTE: Can be optimized by keeping track of the tiles that I went through
        tile = self.fg_tiles[current_pos]

        # Found a loop. NOTE: not all loops are bad.
        # Acceptable loop: 
        # o -> o
        # ^    v
        # o <- o
        # Bad loop:
        # o -> <- o
        # These will probably never happen so not gonna bother checking if it's resolvable or not.
        # Just return False to be safe.
        if current_pos in visited: return False
        visited.add(current_pos)

        # Multiple fg tiles want to move to the same tile
        if len(self.desired_to_current_requests[desired_pos]) != 1: return False

        # There's a bg tile on where I want to go
        if blocking_tile := self.bg_tiles.get(desired_pos):
            if blocking_tile.collides:
                return False

        # There's a fg tile on where I want to go
        if blocking_tile := self.fg_tiles.get(desired_pos):
            # Does it want to move?
            if desired_pos in self.current_to_desired_requests:
                # Try to move it
                tile_can_move = self._resolve_movement_request(desired_pos, self.current_to_desired_requests[desired_pos], visited)
            else:
                # It doesn't want to move
                tile_can_move = False
            # If the other tile is able to move, then I can move
            if tile_can_move:
                return True

            # Otherwise, have the tile handle merging into it
            else:
                return tile.on_contact(self, blocking_tile)

        # Empty tile and no one wants to go to it.
        else:
            return True

    def update(self, game):
        for tile in self.fg_tiles.values():
            tile.update(game)

        accepted_movement_requests = {}
        
        for current_pos, desired_pos in self.current_to_desired_requests.items():
            if self._resolve_movement_request(current_pos, desired_pos, set()):
                # delete_requests gets updated after resolving
                if current_pos not in self.delete_requests:
                    accepted_movement_requests[current_pos] = desired_pos

        for delete_request in self.delete_requests:
            self.fg_tiles.pop(delete_request)
        self.delete_requests = set()

        # Remove all of front tiles then put them where I want them to be (to
        # prevent one tile from deleting the other when it moves to its
        # position)
        pending_placements = {}
        for current_pos, desired_pos in accepted_movement_requests.items():
            pending_placements[desired_pos] = self.fg_tiles.pop(current_pos)
        for desired_pos, placed_tile in pending_placements.items():
            placed_tile.grid_pos = desired_pos
            placed_tile.real_pos = (placed_tile.grid_pos[0]*TILE_SIZE[0], placed_tile.grid_pos[1]*TILE_SIZE[1])
            self.fg_tiles[desired_pos] = placed_tile

        self.current_to_desired_requests = {}
        self.desired_to_current_requests = {}

    def load_level(self, level_name):
        bg_tiles = {}
        fg_tiles = {}

        file_content = '''
000000000000000000000
000000000000000000000
0.........s....000000
0......s..s.........0
0......s..s.........0
0...................0
0......0000.........0
0.ssss..............0
0.ssss......wwwww...0
0.ssss.......www....0
0.ssss........w.....0
000000000000000000000
'''

        level = []
        for line in file_content.split("\n"):
            if line:
                line_list = []
                while " " in line_list:
                    line_list.remove(" ")
                level.append(list(line))

        solid_tiles = []

        for y, row in enumerate(level):
            for x, c in enumerate(row):
                if c in Level.FG_TILES:
                    tile = Level.TILE_MAP[c](x, y)
                    fg_tiles[(x, y)] = tile
                    bg_tiles[(x, y)] = Level.TILE_MAP['.'](x, y)
                else:
                    if c == "0":
                        solid_tiles.append((x, y))
                    elif c == "w":
                        bg_tiles[(x, y)] = map_water_tile(x, y, level)
                    else:
                        tile = Level.TILE_MAP[c](x, y)
                        bg_tiles[(x, y)] = tile

        level_size = (x, y)

        level_copy = copy.deepcopy(level)

        for x, y in solid_tiles.copy():
            tile = try_get_for_mapping(x, y + 1, level)
            if tile != '0' and tile != None:
                bg_tiles[(x, y)] = Tile((x, y), "tile_01")
                level_copy[y][x] = "."
                solid_tiles.remove((x, y))

        for x, y in solid_tiles:
            bg_tiles[(x, y)] = map_solid_tile(x, y, level_copy)

        return bg_tiles, fg_tiles, level_size

    def render(self, surf):
        for tile_pos, tile in self.bg_tiles.items():
            tile.render(surf, self.offset)

        for tile_pos, tile in self.fg_tiles.items():
            tile.render(surf, self.offset)

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

        text = [f'{round(self.handler.clock.get_fps())} fps',
                ]

        self.game_surf.blit(fonts['basic'].get_surf('\n'.join(text)), (0, 0))
