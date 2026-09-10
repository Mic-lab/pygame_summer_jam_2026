import pygame
import colorsys
from copy import deepcopy
from .font import fonts
from . import colors
from . import sfx

class Button:
    
    presets = {
        'basic': {
            'colors': {'border': [23, 25, 27], 
                       'fill': [74, 138, 99], 
                       'text': [127, 235, 144]}
        },
        'basic': {
            'colors': {'border': colors.PURPLE_2, 
                       'fill': colors.PURPLE_1, 
                       'text': colors.WHITE }
        },
    }
    
    def __init__(self, rect: pygame.Rect, text, preset):
        self.rect = rect
        self.text = text
        self.preset = preset
        self.selected = False
        self.clicked = False
        self.released = False
        self.disabled = False
        self.generate_surf()

    @property
    def state(self):
        if self.disabled: return 3
        elif self.clicked: return 2
        elif self.selected: return 1
        else: return 0
        
    @property
    def colors(self):
        if self.disabled:
            colors = self.presets[self.preset]['colors'].copy()
            colors['fill'] = colors['border']
            return colors
        if not self.selected:
            return self.presets[self.preset]['colors']
        else:
            if self.clicked:
                change = 2
            else:
                change = 1

            modes = deepcopy(self.presets[self.preset]['colors'])
                        
            for key, color in modes.items():    
                color = self.rgb_to_hsv(color)
                color[0] += change * 0.04
                color[1] += change * 0.06
                color[2] += change * 0.08

                if color[2] > 1:
                    color[2] = 1
                if color[1] > 1:
                    color[1] = 1
                color[0] = color[0] % 1
                color = self.hsv_to_rgb(color)
                modes[key] = color
            return modes

    def disable(self):
        self.disabled = True
        self.generate_surf()

    def enable(self):
        self.disabled = False
        self.generate_surf()

    def generate_surf(self):
        self.surf = pygame.Surface(self.rect.size)
        self.surf.set_colorkey((0, 0, 0))
        rect = pygame.Rect(0, 0, *self.rect.size)
        pygame.draw.rect(self.surf, self.colors['border'], rect, border_radius=2)
        x, y, w, h = rect
        x += 1
        y += 1
        w -= 2
        h -= 3
        pygame.draw.rect(self.surf, self.colors['fill'], (x, y, w, h), border_radius=2)
        # pygame.draw.aaline(self.surf, self.colors['text'], (x, y), (x, y + h - 2))
        # pygame.draw.aaline(self.surf, self.colors['text'], (x, y), (x + w - 1, y))
        text_img = fonts[self.presets[self.preset].get('font', 'basic')].get_surf(self.text, color=self.colors['text'])
        self.surf.blit(text_img, (rect.centerx - text_img.get_width()*0.5,
                             rect.centery - text_img.get_height()*0.5 - 1))
        
    def update(self, inputs, select_sound='select.wav', click_sound='click.wav'):
        if self.disabled: return
        old_state = self.state

        self.clicked = False
        if self.rect.collidepoint(inputs.get('game_mouse_pos')):
            if not self.selected:
                sfx.sounds[select_sound].play()
            self.selected = True
            if inputs['pressed'].get('mouse1'):
                self.clicked = True
                sfx.sounds[click_sound].play()
        else:
            self.selected = False

        if self.state != old_state:
            self.generate_surf()
                
    def render(self, surf):
        surf.blit(self.surf, self.rect.topleft)
    
    @staticmethod
    def rgb_to_hsv(rgb):
        small_rgb = [i/255 for i in rgb]
        return list(colorsys.rgb_to_hsv(*small_rgb))
    
    @staticmethod
    def hsv_to_rgb(hsv):
        hsv = list(colorsys.hsv_to_rgb(*hsv))
        return [i*255 for i in hsv]
