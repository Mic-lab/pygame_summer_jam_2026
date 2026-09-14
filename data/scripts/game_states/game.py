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
            # 'bow_test',

            'tutorial_0',
            'tutorial_2',
            'tutorial_1',
            'level_0',
            'level_1',
            # 'level_2',
            'level_3',

            'bow_0',

            'conveyor_0',
            'conveyor_1',  # Includes bow

            'tutorial_3',
            'mine_1',
            'mine_2',

            'spikes_0',
            'wide_lava_level',

            'boss_prep_0',
            'boss_prep_1',

            'pre_boss',
            'boss',
            'end'


            )

    def __init__(self):
        self.level_index = 0
        self.transition_timer = Timer(20, done=True)
        pygame.mixer_music.set_volume(0.3)
        sfx.play_music('song.wav', loops=-1)
        self.boss_deaths = 0

    def load_level(self, level_name):
        if level_name == 'boss':
            self.level = BossLevel('boss')
            self.text_surf = None
        else:
            self.level = Level(level_name)
            self.text_surf = fonts['basic'].get_surf(f'Level {self.level_index+1}/{len(self.LEVEL_NAMES)}')

    def load_level_from_index(self, game):
        print(f'loading_level {self.level_index}')
        self.load_level(self.LEVEL_NAMES[self.level_index])
        self.level.update(game)


    def update(self, game):
        if self.transition_timer.done:
            skip = False
            if hasattr(self.level, 'skip'):
                skip = self.level.skip
            if (game.inputs['pressed'].get('return') and self.level.win) or skip:
                if not self.level.level_name == 'end':
                    sfx.sounds['transition.wav'].play()
                    self.transition_timer.duration = 20
                    self.transition_timer.reset()
                    self.completed_transition = False
            self.level.update(game)
        else:
            if self.transition_timer.ratio >= 0.5 and not self.completed_transition:
                self.level_index += 1
                self.load_level_from_index(game)
                self.completed_transition = True

            shader_handler.vars['levelTransitionTimer'] = self.transition_timer.ratio
            self.transition_timer.update()

    def render(self, surf):
        if self.text_surf: 
            surf.blit(self.text_surf, Vec2(0.5*config.GAME_SIZE[0], 4) - (0.5*self.text_surf.get_width(), 0))


        shader_handler.vars['beamCoords'] = []
        shader_handler.vars['hitTimer'] = -1

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
