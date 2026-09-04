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
from ..mgl import shader_handler
from ..particle import ParticleGenerator
from ..entity import Entity
from ..font import fonts
import random

SOLID_TILES = {"0"}

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
    "^": parse_spike_data
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
        if tile != "0" and tile != None:
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

class Level:
    TILE_MAP = {
            '.': lambda x, y: tiles.RotatedTile((x, y), 'tile_00', collides=False),
            's': lambda x, y: tiles.Slime.init_regular_slime(x, y),
            'z': lambda x, y: tiles.Slime.init_heavy_slime(x, y),
            'p': lambda x, y: tiles.PressurePlate((x, y)),
            "#": lambda x, y: tiles.Tile((x, y), "tile_33", collides=False),
            "@": lambda x, y: tiles.RotatedTile((x, y), "tile_32", collides=False),
            "f": lambda x, y: tiles.Tile((x, y), "pot", action='idle'),
            "b": lambda x, y: tiles.Bow((x, y), "bow"),
            "x": lambda x, y: tiles.AttackTile((x, y)),
            "m": lambda x, y: tiles.Mine((x, y))
            }

    FG_TILES = ('s', 'z')

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

    def commence_win(self):
        sfx.sounds['level_complete.wav'].play()
        self.win = True
        self.win_timer.reset()
        self.shake_screen()
        y = 20
        self.add_surf(Animation.img_db['banner'], pos=(0, y), center_x=True, speed=3)
        self.add_surf(fonts['basic'].get_surf('Level complete! Press <Enter> to continue', color=(255, 100, 255)), pos=(0, y), center_x=True, speed=3)

    def shake_screen(self, intensity=2):
        if intensity > self._screen_shake:
            self._screen_shake = intensity

    @staticmethod
    def vector_to_key(vec):
        return (int(vec[0]), int(vec[1]))

    def request_fg_move(self, current_pos, desired_pos):
        desired_pos, current_pos = self.vector_to_key(desired_pos), self.vector_to_key(current_pos)
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
        self.fg_tiles[swapped_pos] = new_tile

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
        pos[0] = 0.5*config.GAME_SIZE[0]-surf.get_width()*0.5
        self.surfs.append([surf, pos, 0, speed])

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
                'pre_boss': 'Remember, hold [shift] to move quickly.\nThis may be important soon...'
                }
        
        if self.level_name in start_dialogues and not self.added_surf:
            img = fonts['basic'].get_surf(start_dialogues[self.level_name])
            self.add_surf(img, (0, 40), center_x=True)
            self.added_surf = True

        if self.pressed_pressure_plate and self.level_name == 'tutorial_0' and not self.added_surf:
            img = fonts['basic'].get_surf(f'You\'re too light to push the pressure plate.\nIf only there was a way to combine the weight of two slimes onto one tile...')
            self.add_surf(img, (0, 40), center_x=True)
            self.added_surf = True
        # -------------------------------------- #

        self.played_sounds = set()
        self.handle_requests(game)

        ParticleGenerator.update_generators(self.particle_gens)

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
            print(blocking_fg_tile)
            # Does it want to move?
            if desired_pos in self.current_to_desired_requests:
                # Try to move it
                tile_can_move = self._resolve_movement_request(desired_pos, self.current_to_desired_requests[desired_pos], visited)
            else:
                print(True)
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
            pending_placements[desired_pos] = self.fg_tiles.pop(current_pos)
        
        slime_moved = False
        for desired_pos, placed_tile in pending_placements.items():
            placed_tile.grid_pos = desired_pos
            # placed_tile.real_pos = (placed_tile.grid_pos[0]*config.TILE_SIZE[0], placed_tile.grid_pos[1]*config.TILE_SIZE[1])
            self.fg_tiles[desired_pos] = placed_tile

        if self.player_moved:
            sfx.sounds[f'step{random.randint(1, 5)}.wav'].play()

        self.current_to_desired_requests = {}
        self.desired_to_current_requests = {}

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
                        bg_tiles[(x, y)] = tiles.Bow((x, y), "bow", level_data[(x, y)])
                    elif c == "^":
                        data = level_data.get((x, y), {"state":"up", "triggers":[]})
                        bg_tiles[(x, y)] = tiles.Spikes((x, y), data["state"], data["triggers"])
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

        for surf_data in self.surfs:
            looped_surf, pos, alpha, speed = surf_data
            ratio = alpha / 255
            looped_surf.set_alpha(alpha)
            surf.blit(looped_surf, Vec2(pos) + (0, 30*(1-(min(2*ratio, 1)))**2))
            
            surf_data[2] += speed
            if surf_data[2] > 255: surf_data[2] = 255
            
        shader_handler.vars['restartTimer'] = self.restart_timer.ratio

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

        self.set_state({'idle':True}, duration=60*4)
        self.warnings = []

    def go_to(self, pos):
        self.real_pos += 0.05*((Vec2(pos) - self.animation.rect.topleft) - self.pos)

    def set_state(self, new_state, duration=None):
        self.state = new_state
        if duration is None: duration = 60
        self.state_timer = Timer(duration)
        self.first_state_frame = True

    def row_attack(self, level, attack):
        self.set_state({'attack': attack}, duration=4*60)
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
        return self.state.get('attack') and self.state_timer.ratio < 0.5

    @staticmethod
    def grid_to_px(grid_pos, level, center=True):
        if not center:
            x, y = grid_pos
        else:
            x, y = grid_pos[0]+0.5, grid_pos[1]+0.5
        return Vec2(config.TILE_SIZE[0] * x, config.TILE_SIZE[1] * y) + level.final_offset


    def update(self, level):
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
                        else: raise ValueError('Bean that isnt vertical or horizontal detected')
                        self.warnings.append(Entity(warning_pos_a, 'attack_warning', action='idle'))
                        self.warnings.append(Entity(warning_pos_b, 'attack_warning', action='idle'))

                for warning in self.warnings: warning.update()
            else:
                self.warnings = []
                for a, b in attack_data['beams']:
                    self.show_beam(a, b, level)

            if self.state_timer.done:
                attacks = ['top', 'bottom', 'left', 'right']
                attacks.remove(attack_direction)
                attack = random.choice(attacks)
                self.row_attack(level, attack)

        if initial_first_state_frame:
            self.first_state_frame = False
        self.state_timer.update()

    def render(self, surf, **kwargs):

        shader_handler.vars['beamCoords'] = self.beam_coords

        
        super().render(surf, **kwargs)
        
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game_over = False
        self.offset += Vec2(0, 32)
        boss = Boss((0, 25), 'boss', 'flying')
        center_coord = (0.5*(config.GAME_SIZE-Vec2(boss.img.get_size())))
        boss.real_pos.x = center_coord.x

        self.boss = boss
        self.boss_hp = BossBar(5_000, 5_000)
        self.bullets = []

        self.attack_tiles = {}
        for pos, bg_tile in self.bg_tiles.items():
            if isinstance(bg_tile, tiles.AttackTile):
                self.attack_tiles[pos] = bg_tile

        self.player_hp = 3
        self.timers = {
                'invincibility': Timer(3*60, done=True),
                'hit': Timer(120, done=True)
                }

    def commence_win(self): pass

    def update(self, game):
        super().update(game)
        self.screen_shake_vec = pygame.Vector2(self._screen_shake).rotate(random.randint(0, 359))
        self.final_offset = self.screen_shake_vec + self.offset

        for pos, attack_tile in self.attack_tiles.items():
            slime = self.fg_tiles.get(pos)
            if not slime: continue

            if attack_tile.attack_timer.done:
                attack_tile.attack_timer.reset()
                self.bullets.append(
                        Bullet(slime.rect.center, self.boss, self)
                        )
            # self.boss_hp.change_val(-1)

        new_bullets = []
        for bullet in self.bullets:
            bullet_output = bullet.update()
            if bullet_output.get('hit_boss'):
                self.boss_hp.change_val(-1)
            if bullet_output.get('dead'): continue
            new_bullets.append(bullet)
        self.bullets = new_bullets

        self.boss.update(game.game_map.level)

        self.detect_slime_beam_collision(game)
        
        for timer in self.timers.values():
            timer.update()

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
        self.timers['invincibility'].reset()
        self.timers['hit'].reset()

        if self.player_hp == 0:
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

        pos = v+(0.5*(config.GAME_SIZE[0] - self.boss_hp.img.get_width()), 20)
        self.boss_hp.render(surf, pos)

        for bullet in self.bullets:
            bullet.render(surf, offset=self.final_offset)

        surf.blit(fonts['regular'].get_surf(f'Player HP: {self.player_hp}'), (50, 50))
        shader_handler.vars['hitTimer'] = 1-self.timers['hit'].ratio
