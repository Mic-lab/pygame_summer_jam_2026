import sys
import pygame
from data.scripts import config
from data.scripts import utils
from data.scripts.mgl import shader_handler
from data.scripts import game_states
from data.scripts.screen import create_screen
from data.scripts.transition import Transition, TransitionState
from data.scripts.animation import Animation
from data.scripts import sfx

class GameHandler:

    def __init__(self):

        create_screen()
        shader_handler.post_screen_init()
        shader_handler.surfs["perlinNoise"] = pygame.image.load("data/imgs/animations/perlin_noise.png").convert_alpha()
        shader_handler.surf_data["perlinNoise"] = {"repeat":True}
        Animation.load_db()
        sfx.init_custom_music()

        self.states = game_states
        self.set_canvas_size(config.GAME_SIZE)
        self.clock = pygame.time.Clock()
        self.inputs = {'pressed': {}, 'released': {}, 'held': {}}
        # self.set_state(self.states.Menu)
        self.set_state(self.states.Game)
        self.transition = Transition()

    def set_canvas_size(self, size):
        self.canvas = pygame.Surface(size)
        self.game_pan = self.get_game_pan()

    def set_state(self, state):
        self.state = state(self)

    def transition_to(self, state):
        self.next_state = state
        self.transition.start()

    def handle_transition(self):
        switch = self.transition.update()
        if switch:
            self.set_state(self.next_state)
        shader_handler.vars['transitionTimer'] = self.transition.timer.get_ease_squared()
        shader_handler.vars['transitionState'] = self.transition.state

    def get_game_pan(self):
        game_pan = 0.5*(pygame.Vector2(self.canvas.get_size()) - (pygame.Vector2(config.GAME_SIZE)))
        game_pan.x, game_pan.y = int(game_pan.x), int(game_pan.y)
        return game_pan

    def handle_input(self):
        for key in self.inputs['pressed']:
            self.inputs['pressed'][key] = self.inputs['released'][key] = False

        mx, my = pygame.mouse.get_pos()
        self.inputs['mouse_pos'] = (mx // config.scale, my // config.scale)
        self.inputs['unscaled_mouse_pos'] = mx, my

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                self.inputs['pressed'][f'mouse{event.button}'] = True
                self.inputs['held'][f'mouse{event.button}'] = True

            if event.type == pygame.MOUSEBUTTONUP:
                self.inputs['released'][f'mouse{event.button}'] = True
                self.inputs['held'][f'mouse{event.button}'] = False

            if event.type == pygame.KEYDOWN:
                key_name = pygame.key.name(event.key)
                self.inputs['pressed'][key_name] = True
                self.inputs['held'][key_name] = True

            if event.type == pygame.KEYUP:
                key_name = pygame.key.name(event.key)
                self.inputs['released'][key_name] = True
                self.inputs['held'][key_name] = False

    def run(self):
        self.running = True
        self.shader_time = 0

        while self.running:
            self.handle_input()

            # Commented out cause this makes the transitions go black
            # instead of keeping the after image of the previous state's
            # render
            # self.canvas.fill((0, 0, 0))
            if self.transition.state != TransitionState.STARTING:
                self.state.update()

            self.handle_transition()

            shader_handler.surfs['canvasTex'] = self.canvas
            shader_handler.vars["time"] = self.shader_time
            shader_handler.render()
            pygame.display.flip()
            shader_handler.release_textures()
            self.shader_time += self.clock.tick(config.fps)

        pygame.quit()
        sys.exit()

GameHandler().run()
