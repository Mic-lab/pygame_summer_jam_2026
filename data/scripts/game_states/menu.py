from .state import State
from ..mgl import shader_handler
from ..import utils
from ..button import Button
from ..font import fonts
from ..animation import Animation
from ..entity import Entity, PhysicsEntity
from ..timer import Timer
from ..particle import Particle, ParticleGenerator
from .. import sfx
from .. import screen, config
from .. import colors
import pygame

class Menu(State):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        w = 150
        def get_rect(i):
            return pygame.Rect(0.5*(config.GAME_SIZE[0]-w), 30+i*30, w, 20) 

        self.buttons = {
            'game': Button(get_rect(5), 'Play', 'basic'),
            'scale': Button(get_rect(6), f'Window Scale', 'basic'),
            'fullscreen': Button(get_rect(7), f'Fullscreen', 'basic')
        }

        pygame.mixer_music.set_volume(0.2)
        sfx.play_music('menu_ambience.wav', loops=-1)

    def sub_update(self):
        self.game_surf.fill(colors.BLACK)
        self.game_surf.blit(
                Animation.img_db['title'],
                (0.5*(config.GAME_SIZE[0]-Animation.img_db['title'].get_width()), 40)
                )

        # Update Buttons
        for key, btn in self.buttons.items():
            btn.update(self.inputs)
            btn.render(self.game_surf)

            if btn.clicked:
                if key == 'game':
                    self.handler.transition_to(self.handler.states.Game)
                    pygame.mixer.music.fadeout(500)
                elif key == 'scale':
                    config.scale = (config.scale + 1) % 5
                    if config.scale == 0: config.scale = 1
                    config.screen_size = config.scale*config.GAME_SIZE[0], config.scale*config.GAME_SIZE[1]
                    screen.create_screen()
                    shader_handler.ctx.viewport = (0, 0, config.screen_size[0], config.screen_size[1])
                    # btn.text = f'Window Scale ({config.scale}x)'
                elif key == 'fullscreen':
                    fullscreen = self.toggle_fullscreen()

                    if fullscreen:
                        self.buttons['scale'].disable()
                    else:
                        self.buttons['scale'].enable()
