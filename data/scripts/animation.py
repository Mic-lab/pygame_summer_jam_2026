import pygame
import os
from . import utils
from pprint import pprint

class Animation:

    ANIMATIONS_DIR = 'data/imgs/animations'

    PINGPING_ANIMATIONS = {('heart', 'full'),}
    STOP_ANIMATIONS = {('heart', 'empty'),}

    @staticmethod
    def load_spritesheet(config, spritesheet: pygame.Surface):
        frames_data = {}

        offset = None

        for frame in config['frames']:

            if offset is None:
                offset = (frame['spriteSourceSize']['x'], frame['spriteSourceSize']['y'])
            else:
                if (frame['spriteSourceSize']['x'], frame['spriteSourceSize']['y']) != offset:
                    raise ValueError('The sprite size is inconsistent. Probably have the wrong export option')


            # filename is action
            if not frame['filename']:  # Untagged
                continue

            if frame['filename'] not in frames_data:
                frames_data[frame['filename']] = []
                                                      
            frame_rect = pygame.Rect(
                frame['frame']['x'],
                frame['frame']['y'],
                frame['frame']['w'],
                frame['frame']['h'],
            )

            frame_img = spritesheet.subsurface(frame_rect)
            frames_data[frame['filename']].append(
                {'img': frame_img,
                 'duration': frame['duration'] // (100/6)}  # convert ms to frames at 60 FPS
            )

        if len(config['meta']['slices']) > 1:
            print(f'[Warning] for {config["meta"]["image"]}, has several slices ({len(config["meta"]["slices"])})')
        for slice in config['meta']['slices']:
            if slice['name'] == 'rect':
                # There should only be one frame, but aseprite is a bit buggy
                dict_rect = slice['keys'][0]['bounds']
                rect_data = pygame.Rect(dict_rect['x'],
                                        dict_rect['y'],
                                        dict_rect['w'],
                                        dict_rect['h'])
                rect_data.x -= offset[0]
                rect_data.y -= offset[1]
                break
        else:
            if 'idle' in frames_data:
                default_action = 'idle'
            else:
                default_action = next(iter(frames_data))
            default_img = frames_data[default_action][0]['img']
            print(f'[Warning] No slice for {config["meta"]["image"]}; Generating rect with {default_action}')
            rect_data = default_img.get_bounding_rect()



        spritesheet_data = {
            'frames': frames_data,
            'rect': rect_data,
            'size': frame_img.get_size()  # Assumes all frames has same size
        }

        return spritesheet_data

    @classmethod
    def load_db(cls):
        cls.animation_db = {}
        cls.img_db = {}

        directory = cls.ANIMATIONS_DIR
            
        for file in os.listdir(directory):
            file_name = os.fsdecode(file)
            if file_name.endswith('.png'): 
                animation_name = file_name.split('.')[0]
                config_location = os.path.join(directory, animation_name + '.json')
                try:
                    animation_config = utils.read_json(config_location)
                except FileNotFoundError:
                    # No json file means it's a static image
                    img = utils.load_img(os.path.join(directory, file_name))
                    cls.animation_db[animation_name] = {
                        None: img,
                        'size': img.get_size()
                    }  
                    # So that Animation can find it easily
                    # For ease of access outside of the class
                    cls.img_db[animation_name] = img
                else:
                    spritesheet = utils.load_img(os.path.join(directory, file_name))
                    spritesheet_data = cls.load_spritesheet(animation_config, spritesheet)
                    cls.animation_db[animation_name] = spritesheet_data
            else:
                continue

        print(f'{" Animation DB ":{"-"}^80}')
        pprint(cls.animation_db)
        print('_'*80)

    def __init__(self, name, action, flip=None):
        self.name = name
        self.size = Animation.animation_db[self.name]['size']
        self.action = None
        self.reverse = False
        self.set_action(action, reset=True)
        if flip is None:
            flip = [False, False]
        self.flip = flip

    @property
    def rect(self) -> pygame.Rect:
        base_rect = Animation.animation_db[self.name]['rect'].copy()
        if any(self.flip):
            for i, flip in enumerate(self.flip):
                if flip:
                    base_rect[i] = self.img.get_size()[i] - base_rect[i] - base_rect[i + 2]
        return base_rect
 
    @property
    def img(self):

        if self.action is None:
            base_img = Animation.img_db[self.name]
        else:
            base_img = self.frame['img']

        if any(self.flip):
            base_img = pygame.transform.flip(base_img, *self.flip)
        return base_img

    @property
    def frames(self):
        return Animation.animation_db[self.name]['frames'][self.action]

    @property
    def frame(self):
        return self.frames[self.animation_frame]

    def update(self):
        if self.action is None:
            return

        self.game_frame += 1
        if self.game_frame > self.frame['duration']:
            self.game_frame = 0

            if self.reverse:
                self.animation_frame -= 1
            else:
                self.animation_frame += 1

            if self.reverse:
                if self.animation_frame < 0:
                    if (self.name, self.action) in self.PINGPING_ANIMATIONS:
                        self.reverse = False
                        self.animation_frame += 2

            if self.animation_frame >= len(self.frames):
                if (self.name, self.action) in self.STOP_ANIMATIONS:
                    self.animation_frame -= 1
                    return True
                if (self.name, self.action) in self.PINGPING_ANIMATIONS:
                    self.reverse = True
                    self.animation_frame -= 2
                    return True
                else:
                    self.animation_frame = 0
                    return True

    def set_action(self, new_action, reset=False):
        if self.action and new_action == self.action and not reset:
            return
        self.reverse = False
        self.action = new_action
        self.animation_frame = 0
        self.game_frame = 0

