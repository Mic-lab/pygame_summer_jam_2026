# from .screen import screen
import pygame
import json
from glob import glob

def load_img(path, colorkey=(0, 0, 0)):
    img = pygame.image.load(path).convert()
    img.set_colorkey(colorkey)
    return img
    # return pygame.transform.scale_by(img, SCALE)

def get_files(directory):
    return glob(directory)

def read_txt(path):
    with open(path) as f:
        content = f.read()
    return content

def read_json(path):
    data = read_txt(path)
    return json.loads(data)

def swap_colors(surface, old_color, new_color):
    surface_copy = surface.copy()
    output_surface = surface.copy()
    output_surface.fill(new_color)
    surface_copy.set_colorkey(old_color)
    output_surface.blit(surface_copy, (0, 0))
    return output_surface

def pan_game_surf(current_size, current_ratio,
                  desired_size, desired_ratio):
    # Ratio is x/y

    # Vertical sides hit first
    if desired_ratio >= current_ratio:
        scale = desired_size[1] // current_size[1]

    # Horizontal sides hit first
    else:
        scale = desired_size[0] // current_size[0]

    canvas_size = (desired_size[0] // scale, desired_size[1] // scale)
    # self.update_game_pan(canvas_size)
    # self.handler.canvas = pygame.Surface(canvas_size)
    return scale, canvas_size

