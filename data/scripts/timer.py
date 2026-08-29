class Timer:

    def __init__(self, duration, done=False, capped=True):
        self.duration = duration
        if done:
            self.frame = self.duration
            self.done = True
        else:
            self.reset()
        self.capped = capped

    def reset(self):
        self.frame = 0
        self.done = False

    def update(self):
        if self.capped and self.done: return
        self.frame += 1
        self.done = self.frame == self.duration

    def get_ease_squared(self):
        # return 1 - (1 - self.frame) ** 2
        return 1 - (1 - self.ratio) ** 2

    @property
    def ratio(self):
        return self.frame / self.duration

    def __repr__(self):
        return f'<Timer({self.frame}/{self.duration})>'

    @staticmethod
    def update_timers(timers):
        new_timers = []
        for timer in timers:
            if not timer.done:
                new_timers.append(timer)
            timer.update()
        return new_timers
