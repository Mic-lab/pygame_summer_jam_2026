import random
import pygame
import copy
from pygame import Vector2 as Vec2
from pathlib import Path

from .. import config
from .. import sfx
from .state import State
from ..button import Button
from ..font import fonts
from ..entity import Entity
from .. import colors

from ..map_system.level import Level
from ..map_system.tiles import Tile, Slime, PressurePlate


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
        self.game_map.load_level('level_0')


    def sub_update(self):
        self.game_surf.fill(colors.BLACK)

        self.game_map.update(self)
        self.game_map.render(self.game_surf)

        text = [f'{round(self.handler.clock.get_fps())} fps',
                ]

        self.game_surf.blit(fonts['basic'].get_surf('\n'.join(text)), (0, 0))
