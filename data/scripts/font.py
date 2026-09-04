from . import utils
from . import colors
import pygame
import os

pygame.init()

class Font:

    FONTS_DIR = 'data/imgs/fonts'

    def __init__(self, file, size, color, antialias=False):
        self.obj = pygame.font.Font(f'{Font.FONTS_DIR}/{file}.ttf', size)
        self.color = color
        self.antialias = antialias

    def get_surf(self, text, color=None):
        if not color:
            color = self.color

        surf = pygame.Font.render(self.obj, text, self.antialias, color)
        return surf

fonts = {
    'regular': Font('ProggyClean', 16, (240, 240, 240)),
    'basic': Font('Minecraftia', 8, (240, 240, 240)),
    'big': Font('m6x11', 16, colors.WHITE)
}
