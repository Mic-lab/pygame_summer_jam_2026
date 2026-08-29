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
            'game': Button(get_rect(0), 'harloo', 'basic'),
            'music 1': Button(get_rect(1), 'music 1', 'basic'),
            'music 2': Button(get_rect(2), 'music 2', 'basic'),
            'stop': Button(get_rect(3), 'stop', 'basic'),
            'scale': Button(get_rect(4), f'Window Scale', 'basic'),
            'fullscreen': Button(get_rect(5), f'Fullscreen', 'basic')
        }

        self.timer = Timer(20, done=True)
        self.particle_gens = [ParticleGenerator.from_template((200, 200), 'angle test'),
                              ParticleGenerator.from_template((300, 200), 'color test')]
        self.text = fonts['basic'].get_surf('''[WASD] Move
[LMB] Particles
[RMB] Chromatic Aberration''', color=(0, 150, 200))

    def sub_update(self):

        if self.inputs['pressed'].get('mouse3'):
            self.timer.reset()

        self.game_surf.fill(colors.BLACK)

        if self.inputs['pressed'].get('mouse1'):
            self.particle_gens.append(ParticleGenerator.from_template(self.inputs['game_mouse_pos'], 'smoke'))

        self.particle_gens = ParticleGenerator.update_generators(self.particle_gens)
        for particle_gen in self.particle_gens:
            particle_gen.render(self.game_surf)

        self.game_surf.set_at(self.inputs['game_mouse_pos'], ( 255, 0, 0))

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

        self.game_surf.blit(self.text, (50, 200))

        text = [f'{round(self.handler.clock.get_fps())} fps',
                # pprint.pformat(Particle.cache)
                ]

        self.game_surf.blit(fonts['basic'].get_surf('\n'.join(text)), (0, 0))

        shader_handler.vars['caTimer'] = 1-self.timer.ratio ** 0.5

        self.timer.update()
