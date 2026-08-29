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
from ..mgl import shader_handler

from ..map_system.level import Level


class GameMap:

    LEVEL_NAMES = (
            'tutorial_0',
            'level_0',
            'level_1',
            'level_2',
            )

    def __init__(self):
        self.level_index = 0

    def load_level(self, level_name):
        self.text_surf = fonts['basic'].get_surf(f'Level {self.level_index+1}/{len(self.LEVEL_NAMES)}')
        self.level = Level(level_name)

    def update(self, game):
        if game.inputs['pressed'].get('return'):
            self.level_index += 1
            self.load_level(self.LEVEL_NAMES[self.level_index])
        self.level.update(game)

    def render(self, surf):
        surf.blit(self.text_surf, Vec2(0.5*config.GAME_SIZE[0], 4) - (0.5*self.text_surf.get_width(), 0))
        self.level.render(surf)


class Game(State):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.game_map = GameMap()
        self.game_map.load_level(GameMap.LEVEL_NAMES[self.game_map.level_index])


    def sub_update(self):
        self.game_surf.fill(colors.BLACK)

        self.game_map.update(self)
        self.game_map.render(self.game_surf)

        text = [f'{round(self.handler.clock.get_fps())} fps',
                ]

        self.game_surf.blit(fonts['basic'].get_surf('\n'.join(text)), (0, 0))

        shader_handler.vars['caTimer'] = 1-self.game_map.level.win_timer.ratio
        shader_handler.vars['flashTimer'] = 1-self.game_map.level.win_timer.ratio
