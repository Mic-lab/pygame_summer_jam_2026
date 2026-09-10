from .state import State
from ..mgl import shader_handler
from ..import utils
from ..button import Button
from ..font import fonts
from ..import animation
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

        def get_rect(i):
            return pygame.Rect(30, 30+i*30, 110, 20) 
        self.buttons = {
            'game': Button(get_rect(3), 'Play', 'basic'),
            'scale': Button(get_rect(4), f'Window Scale', 'basic'),
            'fullscreen': Button(get_rect(5), f'Fullscreen', 'basic')
        }

    def sub_update(self):
        self.game_surf.fill(colors.BLACK)

        # Update Buttons
        for key, btn in self.buttons.items():
            btn.update(self.inputs)
            btn.render(self.game_surf)

            if btn.clicked:
                if key == 'game':
                    self.handler.transition_to(self.handler.states.Game)
                elif key == 'music 1':
                    sfx.play_music('song_1.wav', -1)
                elif key == 'music 2':
                    sfx.play_music('song_2.wav')
                elif key == 'stop':
                    pygame.mixer.music.fadeout(1000)
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
