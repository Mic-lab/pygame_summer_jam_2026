import os
import pygame

pygame.mixer.init()
pygame.mixer.set_num_channels(8)

SOUNDS_DIR = os.path.join('data/sfx/sounds')
MUSIC_DIR = os.path.join('data/sfx/music')

def play_music(file_name, *args, **kwargs):
    # Program freezes when there's music.fadeout
    # So for the music to forcefully play, the fadout must be stopped. 
    pygame.mixer.music.stop()
    pygame.mixer.music.load(os.path.join(MUSIC_DIR, file_name))
    pygame.mixer.music.play(*args, **kwargs)

def load_sounds():
    print('Loading sounds...')
    sounds = {}
    for file in os.listdir(SOUNDS_DIR):
        full_file = os.path.join(SOUNDS_DIR, file)
        sound = pygame.mixer.Sound(full_file)
        print(f'Loading {file}')

        v = 0.5
        if file.startswith('step'):
            v = 0.2
        elif file.startswith('boss_hit'):
            v = 0.3
        elif file.startswith('laser'):
            v = 0.4

        sound.set_volume(v)


        sounds[file] = sound
    return sounds

pygame.mixer.set_reserved(0)

sounds = load_sounds()


