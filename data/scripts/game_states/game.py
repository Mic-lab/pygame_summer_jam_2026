import random
import pygame
import copy
from pygame import Vector2 as Vec2
from pathlib import Path
from ..timer import Timer
from .. import config
from .. import sfx
from .state import State
from ..button import Button
from ..font import fonts
from ..entity import Entity
from .. import colors
from ..mgl import shader_handler

from ..map_system.level import Level, BossLevel


class GameMap:

    LEVEL_NAMES = (
            'boss',
            'bow_test',

            'tutorial_0',
            'tutorial_1',
            'level_0',
            'island_level',
            'level_2',
            'level_3',
            )

    def __init__(self):
        self.level_index = 0
        self.transition_timer = Timer(20, done=True)
        # pygame.mixer_music.set_volume(0.4)
        pygame.mixer_music.set_volume(0.0)
        sfx.play_music('song.wav', loops=-1)

    def load_level(self, level_name):
        if level_name == 'boss':
            self.level = BossLevel('boss')
            # self.text_surf = fonts['basic'].get_surf(f'Level {self.level_index+1}/{len(self.LEVEL_NAMES)}')
            self.text_surf = fonts['basic'].get_surf(f'Boss')
        else:
            self.level = Level(level_name)
            self.text_surf = fonts['basic'].get_surf(f'Level {self.level_index+1}/{len(self.LEVEL_NAMES)}')

    def update(self, game):
        if self.transition_timer.done:
            if game.inputs['pressed'].get('return'):
                sfx.sounds['transition.wav'].play()
                self.transition_timer.reset()
                self.completed_transition = False
            self.level.update(game)
        else:
            if self.transition_timer.ratio >= 0.5 and not self.completed_transition:
                self.level_index += 1
                self.load_level(self.LEVEL_NAMES[self.level_index])
                self.completed_transition = True

            shader_handler.vars['levelTransitionTimer'] = self.transition_timer.ratio
            self.transition_timer.update()

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

        shader_handler.vars['flashTimer'] = 1-self.game_map.level.win_timer.ratio
