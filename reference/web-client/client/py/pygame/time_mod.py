"""pygame.time replacement — uses Atomics.wait for blocking in Web Worker."""

import time as _time

# JS interop — set by _setup()
_key_buffer = None     # JS Int32Array over SharedArrayBuffer
_atomics_wait = None   # JS function: Atomics.wait(arr, idx, val, timeout)
_atomics_exchange = None


def _setup(key_buffer_js):
    """Called by web_main.py to pass the SharedArrayBuffer reference."""
    global _key_buffer, _atomics_wait, _atomics_exchange
    _key_buffer = key_buffer_js
    try:
        try:
            from pyodide.code import run_js
        except ImportError:
            from pyodide import run_js
        _atomics_wait = run_js("""
        (function(arr, idx, val, timeout) {
            return Atomics.wait(arr, idx, val, timeout);
        })
        """)
        _atomics_exchange = run_js("""
        (function(arr, idx, val) {
            return Atomics.exchange(arr, idx, val);
        })
        """)
    except Exception as e:
        print(f"Atomics setup error: {e}")


def _drain_events():
    """Check SharedArrayBuffer for pending keyboard events and push to queue."""
    if _key_buffer is None or _atomics_exchange is None:
        return

    from pygame.event import Event, _push

    # Read and reset the signal atomically
    signal = int(_atomics_exchange(_key_buffer, 0, 0))
    if signal:
        event_type = int(_key_buffer[1])
        key_code = int(_key_buffer[2])
        char_code = int(_key_buffer[3])
        unicode_str = chr(char_code) if char_code > 0 else ""
        _push(Event(event_type, key=key_code, unicode=unicode_str))


def get_ticks():
    """Return milliseconds since start (monotonic)."""
    return int(_time.monotonic() * 1000)


def wait(ms):
    """Block for ms milliseconds, draining keyboard events periodically."""
    if ms <= 0:
        _drain_events()
        return

    if _key_buffer is not None and _atomics_wait is not None:
        end = _time.monotonic() + ms / 1000.0
        while True:
            remaining = end - _time.monotonic()
            if remaining <= 0:
                break
            chunk = min(remaining * 1000, 16)
            _atomics_wait(_key_buffer, 0, 0, chunk)
            _drain_events()
    else:
        _time.sleep(ms / 1000.0)


class Clock:
    """Minimal pygame.time.Clock replacement."""

    def __init__(self):
        self._last = _time.monotonic()

    def tick(self, fps=0):
        now = _time.monotonic()
        elapsed = now - self._last
        if fps > 0:
            target = 1.0 / fps
            delay = target - elapsed
            if delay > 0:
                wait(int(delay * 1000))
        self._last = _time.monotonic()
        return int(elapsed * 1000)
