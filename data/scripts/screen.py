import pygame
from . import config

def create_screen():
    return pygame.display.set_mode(config.screen_size,  pygame.OPENGL | pygame.DOUBLEBUF)


