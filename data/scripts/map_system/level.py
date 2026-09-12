import pygame
import math
from pathlib import Path
from pygame import Vector2 as Vec2
from . import tiles
import copy
from .. import utils
from ..utils import lerp
from .. import config
from ..timer import Timer
from ..font import fonts
from .. import sfx
from ..animation import Animation
from ..mgl import shader_handler
from ..particle import ParticleGenerator
from ..entity import Entity
from ..font import fonts
from .. import colors
import random

SOLID_TILES = {"0", "b"}

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

LAVA_TILE_MAPPINGS = [
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

CABLE_TILE_MAPPINGS = [
    ("tile_34", {(0, -1), (0, 1)}),
    ("tile_34", {(0, -1)}),
    ("tile_34", {(0, 1)}),
    ("tile_35", {(1, 0), (-1, 0)}),
    ("tile_35", {(1, 0)}),
    ("tile_35", {(-1, 0)}),
    ("tile_36", {(0, 1), (1, 0)}),
    ("tile_37", {(0, -1), (1, 0)}),
    ("tile_38", {(0, -1), (-1, 0)}),
    ("tile_39", {(0, 1), (-1, 0)}),
    ("tile_40", {(-1, 0), (1, 0), (0, 1)}),
    ("tile_41", {(0, -1), (0, 1), (1, 0)}),
    ("tile_42", {(-1, 0), (1, 0), (0, -1)}),
    ("tile_43", {(0, -1), (0, 1), (-1, 0)}),
    ("tile_44", {(0, 1), (0, -1), (1, 0), (-1, 0)})
]

ANIMATED_LAVA_TILES = {"tile_20", "tile_21", "tile_22", "tile_26", "tile_27", "tile_28", "tile_29"}

def parse_spike_data(data:str):
    data_elements = data.split("/")
    return {"state":data_elements[0], "triggers":[(tuple(map(int, element.split(",")))) for element in data_elements[1:]]}

LEVEL_DATA_PARSER_DISPATCH = {
    "b": lambda x: Vec2(*map(int, x.split(","))),
    "^": parse_spike_data,
    "c": lambda x: x.split(',')[-1],
    "p": lambda x: [(tuple(map(int, element.split(",")))) for element in x.split("/")]
}

def try_get_for_mapping(x:int, y:int, level:list[list]):
    try:
        return level[y][x]
    except IndexError:
        return None

def map_solid_tile(x:int, y:int, level:list[list]):
    neighbours = set()
    for x_offset, y_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        tile = try_get_for_mapping(x + x_offset, y + y_offset, level)
        if tile not in SOLID_TILES and tile != None:
            neighbours.add((x_offset, y_offset))

    for tile_name, neighbour_map in SOLID_TILE_MAPPINGS:
        if neighbour_map == neighbours:
            return tiles.Tile((x, y), tile_name)

    return tiles.Tile((x, y), "tile_00")

def map_lava_tile(x:int, y:int, level:list[list]):
    neighbours = set()
    for x_offset, y_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        tile = try_get_for_mapping(x + x_offset, y + y_offset, level)
        if tile != "w" and tile != None:
            neighbours.add((x_offset, y_offset))

    for tile_name, neighbour_map in LAVA_TILE_MAPPINGS:
        if neighbour_map == neighbours:
            if tile_name in ANIMATED_LAVA_TILES:
                return tiles.Tile((x, y), tile_name, "idle")
            else:
                return tiles.Tile((x, y), tile_name)

    return tiles.Tile((x, y), "tile_00")

def map_cable_tiles(x:int, y:int, level:list[list]):
    neighbours = set()
    for x_offset, y_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        tile = try_get_for_mapping(x + x_offset, y + y_offset, level)
        if tile == "=" and tile != None:
            neighbours.add((x_offset, y_offset))

    for tile_name, neighbour_map in CABLE_TILE_MAPPINGS:
        if neighbour_map == neighbours:
            return tiles.Tile((x, y), tile_name, collides=False)

def parse_level_data(data_file_contents:str):
    parsed_data = {}
    for line in data_file_contents.splitlines():
        if not line:
            continue
        target_tile, data_type, data = line.split(">>")
        parsed_data[tuple(map(int, target_tile.split(",")))] = LEVEL_DATA_PARSER_DISPATCH[data_type](data)
    return parsed_data

class VerletPoint:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.px, self.py = x, y
        self.ax, self.ay = 0, 0

    def update(self):
        vx = self.x - self.px
        vy = self.y - self.py

        self.px, self.py = self.x, self.y

        self.x += vx * 0.99 + self.ax
        self.y += vy * 0.99 + self.ay

        self.ax, self.ay = 0, 0.1

def resolve_distance(point_1, point_2, target_distance):
    dx = point_2.x - point_1.x
    dy = point_2.y - point_1.y
    
    dist = max(math.hypot(dx, dy), 0.0000000000000000000000001)
    ux = dx / dist
    uy = dy / dist
    difference = dist - target_distance

    offset_x = ux * difference * 0.5
    offset_y = uy * difference * 0.5

    point_1.x += offset_x
    point_1.y += offset_y

    point_2.x -= offset_x
    point_2.y -= offset_y

class Constraint:
    def __init__(self, point_1, point_2, type, data):
        self.point_1 = point_1
        self.point_2 = point_2
        self.type = type
        self.data = data

    def update(self):
        if self.type == "pin":
            self.point_1.x, self.point_1.y = self.data["pin"]
        elif self.type == "distance":
            resolve_distance(self.point_1, self.point_2, self.data["distance"])

class Level:
    TILE_MAP = {
            '.': lambda x, y: tiles.RotatedTile((x, y), 'tile_00', collides=False),
            's': lambda x, y: tiles.Slime.init_regular_slime(x, y),
            'z': lambda x, y: tiles.Slime.init_heavy_slime(x, y),
            "#": lambda x, y: tiles.Tile((x, y), "tile_33", collides=False),
            "@": lambda x, y: tiles.RotatedTile((x, y), "tile_32", collides=False),
            "f": lambda x, y: tiles.Tile((x, y), "pot", action='idle'),
            "b": lambda x, y: tiles.Bow((x, y), "dispenser_tile"),
            "x": lambda x, y: tiles.AttackTile((x, y)),
            "m": lambda x, y: tiles.Mine((x, y)),
            "c": lambda x, y: tiles.Conveyor((x, y), 'right'),
            "+": lambda x, y: tiles.Tile((x, y), 'statue', action='idle'),
            }

    FG_TILES = ('s', 'z', '+')

    def __init__(self, level_name):
        self.level_name = level_name
        self.bg_tiles, self.fg_tiles, self.level_size = self.load_level(level_name)
        self.offset = 0.5*(Vec2(config.GAME_SIZE) - (config.TILE_SIZE[0]*self.level_size[0], config.TILE_SIZE[1]*self.level_size[1]))
        self.particle_gens = []
        self.surfs = []

        self.win = False

        self.desired_to_current_requests = {}
        self.current_to_desired_requests = {}
        self.delete_requests = set()
        self.fg_place_requests = {}
        self.player_moved = False
        self.played_sounds = set()

        self.added_surf = False
        self.pressed_pressure_plate = False

        self.win_timer = Timer(120, done=True)
        self.restart_timer = Timer(30)
        self.restarting = False
        self.allow_restart = True
        self._screen_shake = 0

        self.verlet_points = [VerletPoint(25, i * 5) for i in range(10)]
        self.constraints = [Constraint(self.verlet_points[0], None, "pin", {"pin":(25, 0)})]
        for i in range(len(self.verlet_points) - 1):
            self.constraints.append(Constraint(self.verlet_points[i], self.verlet_points[i + 1], "distance", {"distance":5}))
        
        self.GUY_POS = (25, 53)
        self.guy = Entity(self.GUY_POS, 'guy', action='idle')
        self.start_timer = Timer(1000)
        self.dialogue_timer = Timer(1)
        self.dialogue_played = None
        self.dialogue_played_max = None

    def commence_win(self):
        if self.level_name == 'end': return
        sfx.sounds['level_complete.wav'].play()
        self.win = True
        self.win_timer.reset()
        self.shake_screen()
        y = 18
        self.add_surf(Animation.img_db['banner'], pos=(0, y), center_x=True, speed=3)
        self.add_surf(fonts['basic'].get_surf('Level complete! Press [Enter] to continue', color=(255, 100, 255)), pos=(0, y), center_x=True, speed=3)

    def shake_screen(self, intensity=2):
        if intensity > self._screen_shake:
            self._screen_shake = intensity

    @staticmethod
    def vector_to_key(vec):
        return (int(vec[0]), int(vec[1]))

    def request_fg_move(self, current_pos, desired_pos):
        desired_pos, current_pos = self.vector_to_key(desired_pos), self.vector_to_key(current_pos)
        if current_pos in self.current_to_desired_requests: return
        self.desired_to_current_requests.setdefault(desired_pos, [])
        self.desired_to_current_requests[desired_pos].append(current_pos)
        self.current_to_desired_requests[current_pos] = desired_pos

    def request_fg_place(self, tile, grid_pos):
        grid_pos = self.vector_to_key(grid_pos)
        self.fg_place_requests.setdefault(grid_pos, [])
        self.fg_place_requests[grid_pos].append(tile)

    def request_fg_delete(self, current_pos):
        current_pos = self.vector_to_key(current_pos)
        self.delete_requests.add(current_pos)

    def request_swap(self, swapped_pos, new_tile):
        # NOTE: Swap happens after resolve_movement_requests
        swapped_pos  = self.vector_to_key(swapped_pos)
        new_tile.grid_pos = swapped_pos
        self.fg_tiles[swapped_pos] = new_tile
        self.bg_tiles[swapped_pos].on_stepped(self, new_tile)


    def request_bg_set(self, current_pos, tile):
        current_pos = self.vector_to_key(current_pos)
        self.bg_tiles[current_pos] = tile
        # self.bg_tiles[current_pos] = self.TILE_MAP['.'](*current_pos)

    def play_sound(self, sound_name, suffix=None):
        if sound_name not in self.played_sounds:
            self.played_sounds.add(sound_name)
            if suffix: sound_name += suffix
            sfx.sounds[sound_name].play()

    def notify_player_moved(self):
        self.player_moved = True

    def add_surf(self, surf, pos, center_x=False, speed=1):
        pos = list(pos)
        if center_x: pos[0] = 0.5*config.GAME_SIZE[0]-surf.get_width()*0.5
        self.surfs.append([surf, pos, 0, speed])

    def add_dialogue(self, text,pos=(70, 50)):
        img = fonts['basic'].get_surf(text)
        self.add_surf(img, pos, speed=3)

        self.dialogue_timer.reset()
        self.dialogue_played = 0
        self.dialogue_played_max = len(text.split())

    def get_player_tiles(self):
        # NOTE: Can be optimized
        return [tile for tile in self.fg_tiles.values() if isinstance(tile, tiles.Slime)]
            
    def update(self, game):
        self.player_moved = False

        # Player must be updated before other tiles that way they know if
        # player moved
        player_tiles = self.get_player_tiles()
        for player_tile in player_tiles:
            player_tile.update(game)

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

        for tile in self.fg_tiles.values():
            if tile in player_tiles: continue
            tile.update(game)

        # Handle dialogue ---------------------- #
        start_dialogues = {
                'tutorial_1': 'This\'ll be a bit difficult...',
                'level_0': 'Hold [r] to restart',
                'level_3': 'Good luck!',
                'pre_boss': 'Remember, hold [shift] to move quickly.\nThis may be important soon...',
                }
        
        if self.level_name in start_dialogues and not self.added_surf and self.start_timer.frame > 30:
            # img = fonts['basic'].get_surf(start_dialogues[self.level_name])
            # self.add_surf(img, (0, 40), center_x=True)
            self.add_dialogue(start_dialogues[self.level_name])
            self.added_surf = True

        if self.pressed_pressure_plate and self.level_name == 'tutorial_0' and not self.added_surf:
            # img = fonts['basic'].get_surf(f'You\'re too light to push the pressure plate.\nIf only there was a way to combine the weight of two slimes onto one tile...')
            # self.add_surf(img, (0, 40), center_x=True)
            self.add_dialogue(f'You\'re too light to push the pressure plate.\nIf only there was a way to combine the weight of two slimes onto one tile...')
            self.added_surf = True

        if self.level_name == 'end':

            if self.start_timer.frame > 50:
                end = config.GAME_SIZE[0]*0.5 - 0.5*(self.guy.rect.w)

                self.constraints[0].data["pin"] = (lerp(25, config.GAME_SIZE[0]*0.5 - 0.5*(self.guy.rect.w), ease_in_out_cubic(min((self.start_timer.frame-50)/120, 1))), 0)
                # self.guy.real_pos[0] +=   0.04*()

            if not self.added_surf and self.start_timer.frame > 250:
                self.add_dialogue('Thanks for playing!', pos=(config.GAME_SIZE[0]*0.5+10, 50))
                self.added_surf = True
                self.win_timer.reset()
                pygame.mixer_music.set_volume(0.8)
                sfx.play_music('end_song.wav', loops=-1)

        # -------------------------------------- #

        self.played_sounds = set()
        self.handle_requests(game)

        ParticleGenerator.update_generators(self.particle_gens)

        for point in self.verlet_points:
            point.update()
        for constraint in self.constraints:
            constraint.update()
        point = self.verlet_points[-1]
        mouse_pos = game.inputs.get('game_mouse_pos')
        if (dist := math.dist((point.x, point.y), mouse_pos)) < 20:
            point.ax = math.atan2(point.y - mouse_pos[1], point.x - mouse_pos[0]) * (1 - (dist / 20))
            point.ay = math.atan2(point.y - mouse_pos[1], point.x - mouse_pos[0]) * (1 - (dist / 20))
        self.guy.real_pos.xy = (self.verlet_points[-1].x, self.verlet_points[-1].y)
        self.guy.update()

        if self.dialogue_played_max is not None:
            if self.dialogue_played < self.dialogue_played_max:
                self.guy.animation.set_action('talking')
                if self.dialogue_timer.done:
                    self.dialogue_timer = Timer(random.randint(5, 10))
                    self.dialogue_played += 1
                    if self.guy.pos[0] > 200:
                        sfx.sounds['talk.wav'].play()
                    else:
                        sfx.sounds['talk_left.wav'].play()

            else:
                self.guy.animation.set_action('idle')

        self.start_timer.update()
        self.dialogue_timer.update()

        self._screen_shake *= 0.9
        if self._screen_shake < 0.3: self._screen_shake = 0
        self.win_timer.update()


        # To prevent second restart from starting
        if game.inputs['released'].get('r'):
            self.allow_restart = True
        self.restarting = game.inputs['held'].get('r') and self.allow_restart

        if self.restarting:
            if self.restart_timer.ratio < 1: self.restart_timer.frame += 1
        elif self.restart_timer.frame > 0:
            self.restart_timer.frame -= 1
        if self.restart_timer.ratio == 1:
            # self.restart_timer.reset()
            self.restart()

    def restart(self):
        self.play_sound('restart.wav')
        self.bg_tiles, self.fg_tiles, self.level_size = self.load_level(self.level_name)
        self.allow_restart = False

    def _resolve_movement_request(self, current_pos, desired_pos, visited):
        """
        Returns True if it gives permission for other tiles to go to current_pos.
        """
        # NOTE: Can be optimized by keeping track of the tiles that I went through
        tile = self.fg_tiles[current_pos]

        # Found a loop.
        # Head to head loops are specifically later in the function, so they will never happen:
        # o -> <- o
        # Example of other detected loops: 
        # o -> o
        # ^    v
        # o <- o
        # The tiles won't be able to move if this happens to be safe
        if current_pos in visited: return False
        visited.add(current_pos)

        # Multiple fg tiles want to move to the same tile
        moving_tiles = self.desired_to_current_requests[desired_pos]
        if len(moving_tiles) != 1:
            return tile.on_fg_move_collision(self, moving_tiles, desired_pos)

        # There's a bg tile on where I want to go
        blocking_bg_tile = self.bg_tiles.get(desired_pos)
        if blocking_bg_tile.collides:
            return tile.on_bg_contact(self, blocking_bg_tile)

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

                return tile.on_fg_contact(self, blocking_fg_tile)

        # Empty tile and no one wants to go to it.
        else:
            return True

    def handle_requests(self, game):
        # Handle movement
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
            self.bg_tiles[current_pos].on_stepped_released(self)
            pending_placements[desired_pos] = self.fg_tiles.pop(current_pos)
        
        slime_moved = False
        for desired_pos, placed_tile in pending_placements.items():
            placed_tile.grid_pos = desired_pos
            # placed_tile.real_pos = (placed_tile.grid_pos[0]*config.TILE_SIZE[0], placed_tile.grid_pos[1]*config.TILE_SIZE[1])
            self.fg_tiles[desired_pos] = placed_tile
            self.bg_tiles[desired_pos].on_stepped(self, placed_tile)

        if self.player_moved:
            sfx.sounds[f'step{random.randint(1, 5)}.wav'].play()

        self.current_to_desired_requests = {}
        self.desired_to_current_requests = {}

        # Handle placement (arrow for example)
        for place_pos, tiles in self.fg_place_requests.items():
            if len(tiles) > 1:
                placed_tile = max([(tile, tile.placement_priority) for tile in tiles])[0]
            else:
                placed_tile = tiles[0]
            if blocking_tile := self.fg_tiles.get(place_pos):
                replace_blocking_tile = placed_tile.on_fg_place_collision(self, blocking_tile)
                if replace_blocking_tile:
                    self.fg_tiles[place_pos] = placed_tile
            else:
                self.fg_tiles[place_pos] = placed_tile
        self.fg_place_requests = {}

    def load_level(self, level_name):
        bg_tiles = {}
        fg_tiles = {}

        with open(Path(f'data/levels/{level_name}.txt')) as f:
            level_file_content = f.read()
        
        level_data_path = Path(f"data/levels/{level_name}_data.txt")
        if level_data_path.exists():
            with open(level_data_path) as f:
                level_data = parse_level_data(f.read())
        else:
            level_data = {}

        # Simple level layout used for autotiling
        level = []
        for line in level_file_content.split("\n"):
            if line.startswith('!!!'): break
            if line:
                line_list = []
                while " " in line_list:
                    line_list.remove(" ")
                level.append(list(line))

        # Initialize the tile objects but don't handle autotile objects
        max_x = -1
        max_y = -1
        solid_tiles = []
        for y, row in enumerate(level):
            if y > max_y: max_y = y
            for x, c in enumerate(row):
                og_c = c
                c = c.lower()
                if x > max_x: max_x = x
                if c in Level.FG_TILES:
                    tile = Level.TILE_MAP[c](x, y)
                    fg_tiles[(x, y)] = tile
                    if og_c == c:
                        bg_tiles[(x, y)] = Level.TILE_MAP['.'](x, y)
                    else:
                        bg_tiles[(x, y)] = Level.TILE_MAP['@'](x, y)
                else:
                    if c == "0":
                        solid_tiles.append((x, y))
                    elif c == "w":
                        bg_tiles[(x, y)] = map_lava_tile(x, y, level)
                    elif c == "=":
                        bg_tiles[(x, y)] = map_cable_tiles(x, y, level)
                    elif c == "b":
                        fg_tiles[(x, y)] = tiles.Bow((x, y), "dispenser_tile", level_data[(x, y)])
                        solid_tiles.append((x, y))
                    elif c == "^":
                        data = level_data.get((x, y), {"state":"up", "triggers":[]})
                        bg_tiles[(x, y)] = tiles.Spikes((x, y), data["state"], data["triggers"])
                    elif c == 'c':
                        direction = level_data.get((x, y))
                        if direction is None:
                            print(f'[WARNING] Could\'t find direction for conveyor at {(x, y)}')
                            direction = 'right'
                        bg_tiles[(x, y)] = tiles.Conveyor((x, y), direction=direction)
                    elif c == 'p':
                        bg_tiles[(x, y)] = tiles.PressurePlate((x, y), level_data.get((x, y), []))
                    elif c == ' ':
                        continue
                    else:
                        tile = Level.TILE_MAP[c](x, y)
                        bg_tiles[(x, y)] = tile

        level_size = (max_x+1, max_y+1)

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

        for tile_pos, tile in sorted(self.fg_tiles.items()):
            tile.render(surf, final_offset)

        for gen in self.particle_gens:
            gen.render(surf, offset=final_offset)

        pygame.draw.lines(surf, (99, 7, 100), False, [(p.x, p.y) for p in self.verlet_points], 1)
        self.guy.render(surf, offset=(-12, 0))

        for surf_data in self.surfs:
            looped_surf, pos, alpha, speed = surf_data
            ratio = alpha / 255
            looped_surf.set_alpha(alpha)
            if pos[0] > 100:
                surf.blit(looped_surf, Vec2(pos) + (0, 30*(1-(min(2*ratio, 1)))**2))
            else:
                surf.blit(looped_surf, Vec2(pos) + (-30*(1-(min(2*ratio, 1)))**2, 0))
            
            surf_data[2] += speed
            if surf_data[2] > 255: surf_data[2] = 255
            
        shader_handler.vars['restartTimer'] = self.restart_timer.ratio
        shader_handler.vars['dmgBoostTimer'] = 0
        shader_handler.vars['hitTimer'] = 0

        if self.restarting:
            shader_handler.vars['caTimer'] = self.restart_timer.ratio*3
        else:
            shader_handler.vars['caTimer'] = 1-self.win_timer.ratio

# Boss stuff ---------------------------------------------------------------- #

class Boss(Entity):

    def __init__(self, pos, name, action=None):
        super().__init__(pos, name, action)

        self.IDLE_POS = self.pos
        w = 15
        h = 13
        right_edge = 40  # random big number to make the beam go offscreen
        bottom_edge = 40

        self.ATTACKS = {
                'left': {
                    'pos': (3, 0),
                    'beams': (
                        ((2, 1), (2, bottom_edge)),
                        ((3, 1), (3, bottom_edge)),
                        ((4, 1), (4, bottom_edge)),
                        ((5, 1), (5, bottom_edge)),
                        ((6, 1), (6, bottom_edge)),
                        ((7, 1), (7, bottom_edge)),
                        )
                    },
                'right': {
                    'pos': (w-3, 0),
                    'beams': (
                        ((w-2, 1), (w-2, bottom_edge)),
                        ((w-3, 1), (w-3, bottom_edge)),
                        ((w-4, 1), (w-4, bottom_edge)),
                        ((w-5, 1), (w-5, bottom_edge)),
                        ((w-6, 1), (w-6, bottom_edge)),
                        ((w-7, 1), (w-7, bottom_edge)),
                        )
                    },
                
                'top': {
                    'pos': (0, 3),
                    'beams': (
                        ((1, 2), (right_edge, 2)),
                        ((1, 3), (right_edge, 3)),
                        ((1, 4), (right_edge, 4)),
                        ((1, 5), (right_edge, 5)),
                        ((1, 6), (right_edge, 6)),
                        ((1, 7), (right_edge, 7)),
                        )
                    },

                'top_hard': {
                    'pos': (0, 3),
                    'beams': (
                        ((1, 2), (right_edge, 2)),
                        ((1, 3), (right_edge, 3)),
                        ((1, 4), (right_edge, 4)),
                        ((1, 5), (right_edge, 5)),
                        ((1, 6), (right_edge, 6)),
                        ((1, 7), (right_edge, 7)),
                        ((1, 9), (right_edge, 9)),
                        )
                    },

                'bottom': {
                    'pos': (0, 8),
                    'beams': (
                        ((1, 10), (right_edge, 10)),
                        ((1, 9), (right_edge, 9)),
                        ((1, 8), (right_edge, 8)),
                        ((1, 7), (right_edge, 7)),
                        ((1, 6), (right_edge, 6)),
                        ((1, 5), (right_edge, 5)),
                        ((1, 4), (right_edge, 4)),
                        )
                    },

                }

        self.set_state({'idle':True}, duration=60*3)
        self.warnings = []

        self.hit = False

        self.explosions = []
        self.dead = False

    def go_to(self, pos):
        self.real_pos += 0.05*((Vec2(pos) - self.animation.rect.topleft) - self.pos)

    def set_state(self, new_state, duration=None):
        self.state = new_state
        if duration is None: duration = 60
        self.state_timer = Timer(duration)
        self.first_state_frame = True

    def row_attack(self, level, attack):
        self.set_state({'attack': attack}, duration=6*60)
        # return
        # attacked_row = None
        # slime_positions = random.sample(list(level.fg_tiles.keys()), len(level.fg_tiles))
        # for pos in slime_positions:
        #     if pos[1] in self.ATTACK_ROWS:
        #         attacked_row = pos[1]
        #         break
        #
        # # None of the slimes are in the usual spots
        # if attacked_row is None:
        #     attacked_row = random.choice(list(self.ATTACK_ROWS.keys()))
        #
        # print(f'{attacked_row=}')
        # self.set_state({'move': attacked_row}, duration=8*60)

    def show_beam(self, a, b, level):
        self.beam_grid_coords.extend((a, b))
        a = self.grid_to_px(a, level)
        b = self.grid_to_px(b, level)
        self.beam_coords.extend((a, b))

    @property
    def is_pre_attack(self):
        return self.state.get('attack') and self.state_timer.ratio < 0.4

    @property
    def is_attacking(self):
        r = self.state_timer.ratio
        return self.state.get('attack') and (0.4 <= r < 0.9)

    @staticmethod
    def grid_to_px(grid_pos, level, center=True):
        if not center:
            x, y = grid_pos
        else:
            x, y = grid_pos[0]+0.5, grid_pos[1]+0.5
        return Vec2(config.TILE_SIZE[0] * x, config.TILE_SIZE[1] * y) + level.final_offset

    @property
    def img(self):
        img = super().img
        if self.hit:
            mask_surf = pygame.mask.from_surface(img).to_surface()
            mask_surf = utils.swap_colors(mask_surf, (255, 255, 255), colors.RED)
            mask_surf.set_colorkey((0,0,0))
            return mask_surf
        return img

    def update(self, level):
        if self.dead: return
        if not (self.state.get('dying') and self.state_timer.ratio < 0.7):
            super().update()

        initial_first_state_frame = self.first_state_frame

        self.beam_coords = []
        self.beam_grid_coords = []

        if self.state.get('idle'):
            
            if self.state_timer.done:
                attack = random.choice(('top', 'bottom', 'left', 'right'))
                # attack = random.choice(('left', 'right'))
                
                # attack = random.choice(('top_hard',))
                self.row_attack(level, attack)

        elif self.state.get('dying'):
            if self.state_timer.ratio > 0.7:
                self.animation.set_action("fleeing")
                self.real_pos.y -= 20
            else:
                level.shake_screen(4)
            #     if self.state_timer.frame % 5 == 0:
            #         v = pygame.Vector2(random.randint(0, 30)).rotate(random.randint(0, 359))
            #         explosion = Entity((0,0), 'boss_boom', action='idle')
            #         explosion.real_pos = self.rect.center + v - 0.5*Vec2(explosion.rect.size)
            #         self.explosions.append(explosion)
            #         sfx.sounds['small_boom.wav'].play()
            # if self.state_timer.done:
            #     did_big_boom = self.state.get('did_big_boom')
            #     pygame.mixer_music.fadeout(1000)
            #     if not did_big_boom:
            #         sfx.sounds['boom.wav'].set_volume(1)
            #         sfx.sounds['boom.wav'].play()
            #         self.state['did_big_boom'] = True
            #         level.shake_screen(5)
            #         for i in range(6):
            #             v = pygame.Vector2(random.randint(0, 30)).rotate(random.randint(0, 359))
            #             explosion = Entity((0,0), 'boss_boom', action='idle')
            #             explosion.real_pos = self.rect.center + v - 0.5*Vec2(explosion.rect.size)
            #             self.explosions.append(explosion)

            self.dead = self.state_timer.done
            
        elif attack_direction := self.state.get('attack'):
            attack_data = self.ATTACKS[attack_direction]
            self.go_to(self.grid_to_px(attack_data['pos'], level, center=False))

            if self.is_pre_attack:
                if self.first_state_frame:
                    for a, b in attack_data['beams']:
                        if a[1] == b[1]:
                            warning_pos_a = self.grid_to_px((a[0]-1, a[1]), level, center=False)
                            warning_pos_b = self.grid_to_px((b[0]+1, b[1]), level, center=False)
                        elif a[0] == b[0]:
                            warning_pos_a = self.grid_to_px((a[0], a[1]-1), level, center=False)
                            warning_pos_b = self.grid_to_px((b[0], b[1]+1), level, center=False)
                        else: raise ValueError('Beam that isnt vertical or horizontal detected')
                        self.warnings.append(Entity(warning_pos_a, 'attack_warning', action='idle'))
                        self.warnings.append(Entity(warning_pos_b, 'attack_warning', action='idle'))

                for warning in self.warnings: warning.update()

                self.first_attack_frame = True

            elif self.is_attacking:
                if self.first_attack_frame:
                    print('playing laser sound')
                    pygame.Channel(0).play(sfx.sounds['laser.wav'])
                    self.first_attack_frame = False
                self.warnings = []
                for a, b in attack_data['beams']:
                    self.show_beam(a, b, level)
            else:
                print('stopping')
                pygame.Channel(0).fadeout(100)
                # sfx.sounds['laser.wav'].set_volume(0)

            if self.state_timer.done:
                attacks = ['top', 'bottom', 'left', 'right']
                attacks.remove(attack_direction)
                attack = random.choice(attacks)
                self.row_attack(level, attack)

        self.hit = level.boss_hit

        if initial_first_state_frame:
            self.first_state_frame = False
        self.state_timer.update()

        new_explosions = []
        for explosion in self.explosions:
            done = explosion.update()
            if done: continue
            new_explosions.append(explosion)
        self.explosions = new_explosions

    def start_dying(self):
        if 'dying' not in self.state:
            pygame.Channel(0).fadeout(100)
            self.set_state({'dying': True}, duration=120)
            pygame.mixer_music.fadeout(100)

    def render(self, surf, **kwargs):
        if self.dead: return

        shader_handler.vars['beamCoords'] = self.beam_coords

        
        super().render(surf, **kwargs)

        for explosion in self.explosions:
            explosion.render(surf)
        
        for warning in self.warnings:
            warning.render(surf)

class BossBar:

    FG_PAN = Vec2(1, 0)

    def __init__(self, val, max_val) -> None:
        self._val = val
        self.max_val = max_val
        self.bg_img = Animation.img_db['boss_bar_bg']
        self.fg_img_complete = Animation.img_db['boss_bar_fg']
        self.update_img()

    @property
    def ratio(self):
        return self._val / self.max_val

    def update_img(self):
        sample_rect = pygame.Rect(0, 0, self.fg_img_complete.get_width() * self.ratio, self.fg_img_complete.get_height())
        self.fg_img = self.fg_img_complete.subsurface(sample_rect)
        self.img = pygame.Surface(self.bg_img.get_size())
        self.img.blit(self.bg_img)
        self.img.blit(self.fg_img, self.FG_PAN)

    def change_val(self, val_change):
        self._val += val_change
        self._val = max(0, self._val)
        self.update_img()

    @property
    def val(self):
        return self._val

    def render(self, surf, pos):
        surf.blit(self.img, pos)

class Bullet:

    INITIAL_VEL = 5
    VEL_CHANGE = 1
    VEL_CAP = 5

    def __init__(self, pos, target, level) -> None:
        self.pos = Vec2(pos)
        self.target = target
        self.level = level

        self.vel = self.get_dist_vec()
        self.vel.scale_to_length(self.INITIAL_VEL)

    def get_dist_vec(self):
        return (self.target.rect.center - self.pos - self.level.offset)

    def update(self):
        output = {}
        self.pos += self.vel

        dist = self.get_dist_vec()
        if dist.length() < 24:
            # These are seperated to allow you to play an animation before dying
            output['hit_boss'] = True
            output['dead'] = True

        acceleration = dist
        acceleration.scale_to_length(self.VEL_CHANGE)
        self.vel += acceleration
        if self.vel.length() > self.VEL_CAP:
            self.vel.scale_to_length(self.VEL_CAP)

        return output

    # tmp
    @property
    def img(self):
        s = pygame.Surface((4, 4))
        s.fill((0, 200, 200))
        return s

    def render(self, surf, offset):
        surf.blit(self.img, self.pos+offset)

class BossLevel(Level):

    NUM_SLIMES = 8

    def restart(self):
        super().restart()
        self.sub_init()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game_over = False
        self.offset += Vec2(0, 32)

        s1 = fonts['big'].get_surf('ALL SLIMES ATTACKING')
        s2 = fonts['big'].get_surf('2x Damage boost!', colors.RED)
        self.dmg_boost_surf = pygame.Surface((150, 50))
        self.dmg_boost_surf.set_colorkey((0, 0, 0))
        self.dmg_boost_surf.blit(s1, (0, 0))
        self.dmg_boost_surf.blit(s2, (20, 20))
        
        self.end_timer = Timer(60, done=False)
        self.sub_init()

    def sub_init(self):
        pygame.mixer.stop()

        pygame.mixer_music.set_volume(0.6)
        sfx.play_music('boss_intro.wav')

        boss = Boss((0, 35), 'boss', 'flying')
        center_coord = (0.5*(config.GAME_SIZE-Vec2(boss.img.get_size())))
        boss.real_pos.x = center_coord.x

        self.boss = boss
        self.boss_hp = BossBar(100, 1200)
        self.bullets = []

        self.attack_tiles = {}
        for pos, bg_tile in self.bg_tiles.items():
            if isinstance(bg_tile, tiles.AttackTile):
                self.attack_tiles[pos] = bg_tile

        self.player_hp = 3
        self.hp_entities = []
        for i in range(3):
            self.hp_entities.append(Entity((config.GAME_SIZE[0]-110+i*32, 10), 'heart', action='full'))

        self.timers = {
                'invincibility': Timer(3*60, done=True),
                'hit': Timer(120, done=True),
                'just_toggled_dmg_boost': Timer(60, done=True)
                }

        self.dmg_boost_timer = 0
        self.dmg_boost = False

    def commence_win(self): pass

    def update(self, game):
        super().update(game)

        if not pygame.mixer.music.get_busy() and not 'dying' in self.boss.state:
            sfx.play_music('boss_loop.wav', loops=-1)

        self.screen_shake_vec = pygame.Vector2(self._screen_shake).rotate(random.randint(0, 359))
        self.final_offset = self.screen_shake_vec + self.offset

        slime_count = 0
        for pos, attack_tile in self.attack_tiles.items():
            slime = self.fg_tiles.get(pos)
            if not slime: continue
            slime_count += 1

            if attack_tile.attack_timer.done and not self.boss.dead:
                attack_tile.attack_timer.reset()
                self.bullets.append(
                        Bullet(slime.rect.center, self.boss, self)
                        )

        old_dmg_boost = self.dmg_boost
        self.dmg_boost = slime_count >= self.NUM_SLIMES
        if not old_dmg_boost and self.dmg_boost:
            self.timers['just_toggled_dmg_boost'].reset()
            self.play_sound('powerup.wav')

        self.boss_hit = False
        new_bullets = []
        for bullet in self.bullets:
            bullet_output = bullet.update()
            if bullet_output.get('hit_boss'):
                self.play_sound('boss_hit.wav')
                dmg = -2 if self.dmg_boost else -1
                self.boss_hp.change_val(dmg)
                self.boss_hit = True
            if bullet_output.get('dead'): continue
            new_bullets.append(bullet)
        self.bullets = new_bullets

        self.boss_hp.change_val(-1)
        if self.boss_hp.val <= 0:
            self.boss.start_dying()

        self.boss.update(game.game_map.level)
        if self.boss.dead:
            if self.end_timer.done and not self.win:
                super().commence_win()
            self.end_timer.update()

        self.detect_slime_beam_collision(game)

        for hp in self.hp_entities:
            hp.update()
        
        for timer in self.timers.values():
            timer.update()
        if self.dmg_boost:
            self.dmg_boost_timer += 0.1
            self.dmg_boost_timer = min(self.dmg_boost_timer, 1)
        else:
            self.dmg_boost_timer -= 0.1
            self.dmg_boost_timer = max(self.dmg_boost_timer, 0)

    def detect_slime_beam_collision(self, game):
        beam_on_slime = False
        for i in range(0, len(self.boss.beam_grid_coords), 2):
            a = self.boss.beam_grid_coords[i]
            b = self.boss.beam_grid_coords[i+1]
            if a[0] == b[0]:
                x = a[0]
                y_min = max(min(a[1], b[1]), 0)
                y_max = min(max(a[1], b[1])+1, self.level_size[1]-1)
                for y in range(y_min, y_max):
                    if self.fg_tiles.get((x, y)):
                        beam_on_slime = True
                        break
            elif a[1] == b[1]:
                y = a[1]
                x_min = max(min(a[0], b[0]), 0)
                x_max = min(max(a[0], b[0])+1, self.level_size[0]-1)
                for x in range(x_min, x_max):
                    if self.fg_tiles.get((x, y)):
                        beam_on_slime = True
                        break
            else:
                raise ValueError('found beam that\'s not horizontal or vertical')

            if beam_on_slime: break

        if beam_on_slime and not self.game_over:
            self.take_dmg(game)

    def take_dmg(self, game):
        if not self.timers['invincibility'].done: return
        sfx.sounds['hit.wav'].play()
        self.player_hp -= 1
        self.hp_entities[self.player_hp].animation.set_action('empty')
        self.timers['invincibility'].reset()
        self.timers['hit'].reset()

        if self.player_hp <= 0:
            pygame.Channel(0).stop()
            pygame.mixer_music.fadeout(1000)
            self.game_over = True
            game_map = game.game_map
            game_map.level_index -= 2  # -2 cause the game map will do do +1, so the level would only go 1 back
            sfx.sounds['transition.wav'].play()
            self.update(game)  # Just so u can see the slime move towards the beam
            game_map.transition_timer.duration = 100
            game_map.transition_timer.reset()
            game_map.completed_transition = False

            

    def render(self, surf):
        v = self.screen_shake_vec
        # final_offset = self.offset + v

        super().render(surf)
        self.boss.render(surf, offset=v)

        pos = (0.5*(config.GAME_SIZE[0] - self.boss_hp.img.get_width()), 40)
        self.boss_hp.render(surf, pos)

        for bullet in self.bullets:
            bullet.render(surf, offset=self.final_offset)

        for hp in self.hp_entities:
            hp.render(surf)

        if self.dmg_boost:
            center = Vec2(config.GAME_SIZE[0]-70, 120)
            x = utils.ease_out_elastic(self.timers['just_toggled_dmg_boost'].ratio)
            scale_x = lerp(2, 1, x)
            scale_y = lerp(0.5, 1, x)
            dmg_boost_surf = pygame.transform.scale(self.dmg_boost_surf, (self.dmg_boost_surf.get_width()*scale_x, self.dmg_boost_surf.get_height()*scale_y))
            angle = lerp(90, 0, x)
            dmg_boost_surf = pygame.transform.rotate(dmg_boost_surf, angle)
            surf.blit(dmg_boost_surf, center - 0.5*Vec2(dmg_boost_surf.get_size()))

        if self.restarting:
            shader_handler.vars['caTimer'] = self.restart_timer.ratio*3
        else:
        #     shader_handler.vars['caTimer'] = 1-self.win_timer.ratio
            shader_handler.vars['caTimer'] = self.dmg_boost_timer*1
            shader_handler.vars['dmgBoostTimer'] = self.dmg_boost_timer*0.5

        shader_handler.vars['hitTimer'] = 1-self.timers['hit'].ratio

def ease_in_out_cubic(x):
    return 4 * x**3 if x < 0.5 else 1 - ((-2 * x + 2) ** 3) / 2
