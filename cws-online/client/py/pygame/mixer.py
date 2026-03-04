"""pygame.mixer replacement — stubs for web audio."""

_init_done = False


def init(**kwargs):
    global _init_done
    _init_done = True


def get_init():
    return _init_done


def quit():
    global _init_done
    _init_done = False


def pre_init(*args, **kwargs):
    pass


class Sound:
    """Stub Sound object. Actual audio goes through web_sound.py → main thread."""

    def __init__(self, file=None, buffer=None):
        self._buffer = buffer

    def play(self, loops=0, maxtime=0):
        pass

    def stop(self):
        pass

    def get_length(self):
        return 0.0


class Channel:
    """Stub mixer channel."""

    def __init__(self, n=0):
        self._n = n

    def play(self, sound, loops=0, maxtime=0):
        pass

    def stop(self):
        pass

    def get_busy(self):
        return False
