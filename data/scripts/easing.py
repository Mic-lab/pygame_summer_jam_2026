import math
from .utils import lerp

C1 = 1.70158;
C3 = C1 + 1;
C4 = (2 * math.pi) / 3

def ease(f):
    def wrapper(x, clamp=False):
        if clamp: x = min(max(x, 0), 1)
        return f(x)
    return wrapper

@ease
def get_ease_squared(x):
    return 1 - (1 - x) ** 2

@ease
def ease_out_elastic(x):
    if x in (0, 1): return x
    return (2 ** (-10 * x)) * math.sin((x * 10 - 0.75) * C4) + 1

@ease
def ease_out_circ(x):
    return (1 - (x - 1) ** 2) ** 0.5
    
@ease
def ease_out_back(x):
    return 1 + C3 * (x-1)**3 + C1 * (x-1)**2

