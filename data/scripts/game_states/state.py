import pygame
from .. import config
from abc import abstractmethod

class State:

    def __init__(self, game_handler):
        self.handler = game_handler

    def update(self):
        self.inputs = self.handler.inputs | {'game_mouse_pos': -self.handler.game_pan+pygame.Vector2(self.handler.inputs['mouse_pos'])}
        self.inputs['mouse_pos'] = 'good chance you meant game_mouse_pos. If you actually want mouse_pos then delete me. Im defined in state.py'
        self.game_surf = pygame.Surface(config.GAME_SIZE)

        self.sub_update()

        self.handler.canvas.blit(self.game_surf, self.handler.get_game_pan())

    @abstractmethod
    def sub_update(self):
        pass
