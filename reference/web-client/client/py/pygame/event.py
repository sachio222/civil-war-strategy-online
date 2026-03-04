"""pygame.event replacement — event queue populated from SharedArrayBuffer."""


class Event:
    """A pygame-compatible event object."""

    def __init__(self, type, key=0, unicode="", **kwargs):
        self.type = type
        self.key = key
        self.unicode = unicode
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return f"Event(type={self.type}, key={self.key}, unicode={self.unicode!r})"


# Internal event queue
_event_queue = []


def _push(ev):
    """Push an event into the queue (called by time_mod._drain_events)."""
    _event_queue.append(ev)


def get():
    """Return and clear all pending events."""
    global _event_queue
    events = _event_queue
    _event_queue = []
    return events


def poll():
    """Return one event, or Event(0) if none."""
    if _event_queue:
        return _event_queue.pop(0)
    return Event(0)


def clear():
    """Discard all pending events."""
    global _event_queue
    _event_queue = []


def pump():
    """No-op (no OS event pump needed in Web Worker)."""
    pass


def set_allowed(types):
    """No-op stub."""
    pass


def set_blocked(types):
    """No-op stub."""
    pass
