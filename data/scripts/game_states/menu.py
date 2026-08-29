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

        self.img_entity = Entity((0, 0), 'test')
        self.player = PhysicsEntity(pos=(150, 30), name='side', action='idle')
        self.e_speed = 1.5
        self.timer = Timer(20, done=True)
        self.particle_gens = [ParticleGenerator.from_template((200, 200), 'angle test'),
                              ParticleGenerator.from_template((300, 200), 'color test')]
        self.text = fonts['basic'].get_surf('''[WASD] Move
[LMB] Particles
[RMB] Chromatic Aberration''', color=(0, 150, 200))
        sfx.play_custom_music(sfx.sounds['song_1.wav'])

    def sub_update(self):

        if self.inputs['pressed'].get('mouse3'):
            self.timer.reset()

        self.game_surf.fill((20, 20, 20))

        self.img_entity.real_pos = self.inputs['game_mouse_pos']
        self.img_entity.render(self.game_surf)

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

                    if pygame.display.is_fullscreen():
                        config.scale = 2
                        config.screen_size = pygame.Vector2(config.GAME_SIZE)*config.scale
                        self.handler.set_canvas_size(config.GAME_SIZE)

                        screen.create_screen()
                        shader_handler.ctx.viewport = (0, 0, *config.screen_size)
                        
                        self.buttons['scale'].enable()
                        # self.buttons['scale'].text = f'Window Scale ({config.scale}x)'

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

                        self.buttons['scale'].disable()

        self.player.vel = [0, 0]
        if self.inputs['held'].get('a'):
            self.player.vel[0] -= self.e_speed
            self.player.animation.flip[0] = True
        elif self.inputs['held'].get('d'):
            self.player.vel[0] += self.e_speed
            self.player.animation.flip[0] = False
        if self.inputs['held'].get('w'):
            self.player.vel[1] -= self.e_speed
        elif self.inputs['held'].get('s'):
            self.player.vel[1] += self.e_speed

        if any(self.player.vel):
            self.player.animation.set_action('run')
        else:
            self.player.animation.set_action('idle')

        self.player.update([btn.rect for btn in self.buttons.values()])
        self.player.render(self.game_surf)

        self.game_surf.blit(self.text, (50, 200))

        text = [f'{round(self.handler.clock.get_fps())} fps',
                f'vel = {self.player.vel}',
                # pprint.pformat(Particle.cache)
                ]

        self.game_surf.blit(fonts['basic'].get_surf('\n'.join(text)), (0, 0))

        shader_handler.vars['caTimer'] = 1-self.timer.ratio ** 0.5

        self.timer.update()
