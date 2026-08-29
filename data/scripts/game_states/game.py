import pygame
from .state import State
# from .menu import Menu
from ..button import Button
from ..font import fonts

class Game(State):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        rects = [pygame.Rect(30, 30+i*30, 80, 20) for i in range(4)]
        self.buttons = {
            'menu': Button(rects[0], 'back', 'basic'),
        }

    def sub_update(self):
        self.game_surf.fill((20, 20, 20))

        # Update Buttons
        for key, btn in self.buttons.items():
            btn.update(self.inputs)
            btn.render(self.game_surf)

            if btn.clicked:
                if key == 'menu':
                    self.handler.transition_to(self.handler.states.Menu)
