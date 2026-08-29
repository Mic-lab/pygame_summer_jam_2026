from .timer import Timer
from enum import IntEnum

class TransitionState(IntEnum):
    NONE = 0
    STARTING = 1
    ENDING = -1

class Transition:

    DURATION = 30
    
    def __init__(self):
        self.timer = Timer(Transition.DURATION)
        self.state = TransitionState.NONE

    def start(self):
        self.timer.reset()  # In case start called mid transition
        self.state = TransitionState.STARTING

    def update(self):
        switch = False
        if self.state:
            self.timer.update()
            if self.timer.done:
                if self.state == TransitionState.STARTING:
                    self.state = TransitionState.ENDING
                    switch = True
                elif self.state == TransitionState.ENDING:
                    self.state = TransitionState.NONE
                self.timer.reset()
        return switch

