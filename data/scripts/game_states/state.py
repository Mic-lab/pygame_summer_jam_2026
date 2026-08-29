import pygame
from .. import config
from abc import abstractmethod
from .. import screen
from .. import config
from .. import utils
from .. mgl import shader_handler

class State:

    def __init__(self, game_handler):
        self.handler = game_handler
        self.game_surf = pygame.Surface(config.GAME_SIZE)

    def update(self):
        self.inputs = self.handler.inputs | {'game_mouse_pos': -self.handler.game_pan+pygame.Vector2(self.handler.inputs['mouse_pos'])}
        self.inputs['mouse_pos'] = 'good chance you meant game_mouse_pos. If you actually want mouse_pos then delete me. Im defined in state.py'
        if self.inputs['pressed'].get('f11'):
            self.toggle_fullscreen()

        self.sub_update()

        self.handler.canvas.blit(self.game_surf, self.handler.get_game_pan())

    def toggle_fullscreen(self):
        if pygame.display.is_fullscreen():
            config.scale = 2
            config.screen_size = pygame.Vector2(config.GAME_SIZE)*config.scale
            self.handler.set_canvas_size(config.GAME_SIZE)

            screen.create_screen()
            shader_handler.ctx.viewport = (0, 0, *config.screen_size)
            
            # self.buttons['scale'].enable()
            
            return False

        else:
            # desktop_size = pygame.display.get_desktop_sizes()[0]
            # ^ There's also this but not sure how this works for dual monitor setup:
            pygame.display.toggle_fullscreen()
            desktop_size = pygame.display.get_window_size()

            resize_scale, new_canvas_size = utils.pan_game_surf(

                    self.handler.canvas.get_size(),
                    config.GAME_RATIO,
                    desktop_size,
                    desktop_size[0]/desktop_size[1])
            
            self.handler.set_canvas_size(new_canvas_size)
            config.scale = resize_scale
            config.screen_size = desktop_size
            screen.create_screen()

            pygame.display.toggle_fullscreen()
            shader_handler.ctx.viewport = (0, 0, *config.screen_size)

            # self.buttons['scale'].disable()
            return True

    @abstractmethod
    def sub_update(self):
        pass
