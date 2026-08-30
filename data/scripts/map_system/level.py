import pygame
from pathlib import Path
from pygame import Vector2 as Vec2
from . import tiles
import copy
from .. import config
from ..timer import Timer
from ..font import fonts
from .. import sfx
from ..animation import Animation
import random

SOLID_TILES = {"0", "1"}

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

ANIMATED_WATER_TILES = {"tile_20", "tile_21", "tile_22", "tile_26", "tile_27", "tile_28", "tile_29"}

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
            return tiles.Tile((x, y), tile_name)

    return tiles.Tile((x, y), "tile_00")

def map_water_tile(x:int, y:int, level:list[list]):
    neighbours = set()
    for x_offset, y_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        tile = try_get_for_mapping(x + x_offset, y + y_offset, level)
        if tile != "w" and tile != None:
            neighbours.add((x_offset, y_offset))

    for tile_name, neighbour_map in WATER_TILE_MAPPINGS:
        if neighbour_map == neighbours:
            if tile_name in ANIMATED_WATER_TILES:
                return tiles.Tile((x, y), tile_name, "idle")
            else:
                return tiles.Tile((x, y), tile_name)

    return tiles.Tile((x, y), "tile_00")



class Level:
    TILE_MAP = {
            '.': lambda x, y: tiles.Tile((x, y), 'tile_00', collides=False),
            's': lambda x, y: tiles.Slime.init_regular_slime(x, y),
            'p': lambda x, y: tiles.PressurePlate((x, y)),
            "#": lambda x, y: tiles.Tile((x, y), "tile_33", collides=False),
            "@": lambda x, y: tiles.Tile((x, y), "tile_32", collides=False),
            "1": lambda x, y: tiles.Tile((x, y), "tile_34")
            }

    FG_TILES = ('s')

    def __init__(self, level_name):
        self.level_name = level_name
        self.bg_tiles, self.fg_tiles, self.level_size = self.load_level(level_name)
        self.offset = 0.5*(Vec2(config.GAME_SIZE) - (config.TILE_SIZE[0]*self.level_size[0], config.TILE_SIZE[1]*self.level_size[1]))
        self.surfs = []

        self.win = False

        self.desired_to_current_requests = {}
        self.current_to_desired_requests = {}
        self.delete_requests = set()

        self.added_surf = False
        self.pressed_pressure_plate = False

        self.win_timer = Timer(120, done=True)
        self._screen_shake = 0

    def commence_win(self):
        self.win = True
        self.win_timer.reset()
        self.shake_screen()
        y = 30
        self.add_surf(Animation.img_db['banner'], pos=(0, y), center_x=True, speed=3)
        self.add_surf(fonts['basic'].get_surf('Level complete! Press <Enter> to continue', color=(255, 100, 255)), pos=(0, y), center_x=True, speed=3)

    def shake_screen(self, intensity=2):
        if intensity > self._screen_shake:
            self._screen_shake = intensity

    def request_fg_move(self, current_pos, desired_pos):
        desired_pos, current_pos = tuple(desired_pos), tuple(current_pos)
        self.desired_to_current_requests.setdefault(desired_pos, [])
        self.desired_to_current_requests[desired_pos].append(current_pos)
        self.current_to_desired_requests[current_pos] = desired_pos

    def request_delete(self, current_pos):
        self.delete_requests.add(current_pos)

    def request_swap(self, swapped_pos, new_tile):
        # NOTE: Swap happens after resolve_movement_requests
        self.fg_tiles[swapped_pos] = new_tile

    def add_surf(self, surf, pos, center_x=False, speed=1):
        pos = list(pos)
        pos[0] = 0.5*config.GAME_SIZE[0]-surf.get_width()*0.5
        self.surfs.append([surf, pos, 0, speed])

    def update(self, game):

        win = True
        for tile_coord, tile in self.bg_tiles.items():
            tile.update(game)
            if stepping_tile := self.fg_tiles.get(tile_coord):
                tile.on_stepped(self, stepping_tile)
                if not tile.stepped_on and isinstance(tile, tiles.PressurePlate): self.pressed_pressure_plate = True
            else:
                if tile.stepped_on:
                    tile.on_stepped_released(self)

            if isinstance(tile, tiles.PressurePlate):
                if not tile.stepped_on:
                    win = False

        if win:
            if not self.win:
                self.commence_win()


        if self.pressed_pressure_plate and self.level_name == 'tutorial_0' and not self.added_surf:
            img = fonts['basic'].get_surf(f'You\'re too light to push the pressure plate.\nIf only there was a way to combine the weight of two slimes onto one tile...')
            self.add_surf(img, (0, 60), center_x=True)
            self.added_surf = True
            

        for tile in self.fg_tiles.values():
            tile.update(game)

        self.handle_requests(game)

        self._screen_shake *= 0.9
        if self._screen_shake < 0.3: self._screen_shake = 0
        self.win_timer.update()


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
        blocking_bg_tile = self.bg_tiles.get(desired_pos)
        if blocking_bg_tile.collides:
            return False

        # There's a fg tile on where I want to go
        if blocking_fg_tile := self.fg_tiles.get(desired_pos):
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
                if desired_pos in self.delete_requests:
                    return True

                return tile.on_contact(self, blocking_fg_tile)

        # Empty tile and no one wants to go to it.
        else:
            return True

    def handle_requests(self, game):
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
        
        slime_moved = False
        for desired_pos, placed_tile in pending_placements.items():
            placed_tile.grid_pos = desired_pos
            placed_tile.real_pos = (placed_tile.grid_pos[0]*config.TILE_SIZE[0], placed_tile.grid_pos[1]*config.TILE_SIZE[1])
            self.fg_tiles[desired_pos] = placed_tile
            slime_moved = True

        if slime_moved:
            sfx.sounds[f'step{random.randint(1, 5)}.wav'].play()

        self.current_to_desired_requests = {}
        self.desired_to_current_requests = {}


    def load_level(self, level_name):
        bg_tiles = {}
        fg_tiles = {}

        with open(Path(f'data/levels/{level_name}.txt')) as f:
            file_content = f.read()

        # Simple level layout used for autotiling
        level = []
        for line in file_content.split("\n"):
            if line:
                line_list = []
                while " " in line_list:
                    line_list.remove(" ")
                level.append(list(line))

        # Initialize the tile objects but don't handle autotile objects
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
                    elif c == ' ':
                        continue
                    else:
                        tile = Level.TILE_MAP[c](x, y)
                        bg_tiles[(x, y)] = tile

        level_size = (x, y)

        # Create the autotile objects
        level_copy = copy.deepcopy(level)
        for x, y in solid_tiles.copy():
            tile = try_get_for_mapping(x, y + 1, level)
            if tile not in SOLID_TILES and tile != None:
                bg_tiles[(x, y)] = tiles.Tile((x, y), "tile_01")
                level_copy[y][x] = "."
                solid_tiles.remove((x, y))

        for x, y in solid_tiles:
            bg_tiles[(x, y)] = map_solid_tile(x, y, level_copy)

        return bg_tiles, fg_tiles, level_size

    def render(self, surf):
        v = pygame.Vector2(self._screen_shake).rotate(random.randint(0, 359))
        final_offset = self.offset + v


        for tile_pos, tile in self.bg_tiles.items():
            tile.render(surf, final_offset)

        for tile_pos, tile in self.fg_tiles.items():
            tile.render(surf, final_offset)

        for surf_data in self.surfs:
            looped_surf, pos, alpha, speed = surf_data
            ratio = alpha / 255
            looped_surf.set_alpha(alpha)
            surf.blit(looped_surf, Vec2(pos) + (0, 50*(1-(min(2*ratio, 1)))**2))
            
            surf_data[2] += speed
            if surf_data[2] > 255: surf_data[2] = 255
