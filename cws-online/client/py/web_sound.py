"""web_sound.py — Web Audio sound engine (replaces cws_sound.py).

Reuses the desktop's _MMLParser for MML parsing (it's pure Python).
Sound output is sent to the main thread via postMessage, which plays
it through the Web Audio API.
"""

import math
import pygame

QB64_TICKS_PER_SEC = 18.2
SAMPLE_RATE = 44100
MAX_AMPLITUDE = 24000

# Persistent MML state
_mml_octave = 4
_mml_length = 4
_mml_tempo = 120
_mml_style = 7 / 8

_initialized = False
_channel = None

# MML note frequencies for octave 4
_BASE_FREQS = {
    0: 262, 1: 277, 2: 294, 3: 311, 4: 330, 5: 349,
    6: 370, 7: 392, 8: 415, 9: 440, 10: 466, 11: 494,
}
_NOTE_MAP = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11,
}


def init_sound():
    global _initialized, _channel
    _initialized = True


_js_post_sound = None

def _init_sound_js():
    global _js_post_sound
    if _js_post_sound is not None:
        return
    try:
        try:
            from pyodide.code import run_js
        except ImportError:
            from pyodide import run_js
        _js_post_sound = run_js("""
        (function(freq, duration) {
            self.postMessage({type: "sound", freq: freq, duration: duration});
        })
        """)
    except Exception:
        _js_post_sound = lambda f, d: None

def _post_sound(freq, duration_ms):
    """Send a sound command to the main thread."""
    global _js_post_sound
    if _js_post_sound is None:
        _init_sound_js()
    try:
        _js_post_sound(freq, duration_ms)
    except Exception:
        pass


def qb_sound(freq, duration_ticks):
    """QB64 SOUND command — play tone and block for duration."""
    duration_sec = max(0.001, duration_ticks / QB64_TICKS_PER_SEC)
    duration_ms = int(duration_sec * 1000)

    if freq < 37:
        pygame.time.wait(duration_ms)
        return

    _post_sound(freq, duration_ms)
    pygame.time.wait(duration_ms)


class _MMLParser:
    """Parse QB64 PLAY MML strings into (freq, duration_sec) tuples."""

    def __init__(self, mml):
        self.mml = mml.upper()
        self.pos = 0
        self.octave = _mml_octave
        self.length = _mml_length
        self.tempo = _mml_tempo
        self.style = _mml_style
        self.foreground = True

    def _peek(self):
        if self.pos < len(self.mml):
            return self.mml[self.pos]
        return ''

    def _advance(self):
        ch = self.mml[self.pos]
        self.pos += 1
        return ch

    def _read_number(self):
        start = self.pos
        while self.pos < len(self.mml) and self.mml[self.pos].isdigit():
            self.pos += 1
        if self.pos > start:
            return int(self.mml[start:self.pos])
        return None

    def _note_duration(self, note_len):
        if note_len is None or note_len < 1:
            note_len = self.length
        quarter_sec = 60.0 / self.tempo
        return (4.0 / note_len) * quarter_sec

    def _count_dots(self):
        dots = 0
        while self.pos < len(self.mml) and self.mml[self.pos] == '.':
            dots += 1
            self.pos += 1
        return dots

    def _apply_dots(self, duration, dots):
        extra = duration
        for _ in range(dots):
            extra *= 0.5
            duration += extra
        return duration

    def parse(self):
        notes = []
        while self.pos < len(self.mml):
            ch = self._peek()
            if ch in ' \t\n':
                self._advance()
                continue
            if ch == 'M':
                self._advance()
                p = self._peek()
                if p == 'S':
                    self._advance(); self.style = 3/4
                elif p == 'N':
                    self._advance(); self.style = 7/8
                elif p == 'L':
                    self._advance(); self.style = 1.0
                elif p == 'F':
                    self._advance(); self.foreground = True
                elif p == 'B':
                    self._advance(); self.foreground = False
                continue
            if ch == 'T':
                self._advance()
                n = self._read_number()
                if n is not None:
                    self.tempo = max(32, min(255, n))
                continue
            if ch == 'O':
                self._advance()
                n = self._read_number()
                if n is not None:
                    self.octave = max(0, min(6, n))
                continue
            if ch == '>':
                self._advance()
                self.octave = min(6, self.octave + 1)
                continue
            if ch == '<':
                self._advance()
                self.octave = max(0, self.octave - 1)
                continue
            if ch == 'L':
                self._advance()
                n = self._read_number()
                if n is not None and n >= 1:
                    self.length = n
                self._count_dots()
                continue
            if ch == 'P':
                self._advance()
                n = self._read_number()
                dur = self._note_duration(n)
                dots = self._count_dots()
                dur = self._apply_dots(dur, dots)
                notes.append((0, dur))
                continue
            if ch == 'N':
                self._advance()
                n = self._read_number()
                if n is not None:
                    if n == 0:
                        dur = self._note_duration(None)
                        notes.append((0, dur))
                    else:
                        octave = (n - 1) // 12
                        semitone = (n - 1) % 12
                        freq = _BASE_FREQS[semitone] * (2 ** (octave - 4))
                        dur = self._note_duration(None)
                        dots = self._count_dots()
                        dur = self._apply_dots(dur, dots)
                        notes.append((freq, dur))
                continue
            if ch in _NOTE_MAP:
                self._advance()
                semitone = _NOTE_MAP[ch]
                if self._peek() in ('#', '+'):
                    self._advance()
                    semitone += 1
                    if semitone > 11:
                        semitone = 0
                elif self._peek() == '-':
                    self._advance()
                    semitone -= 1
                    if semitone < 0:
                        semitone = 11
                n = self._read_number()
                dur = self._note_duration(n)
                dots = self._count_dots()
                dur = self._apply_dots(dur, dots)
                freq = _BASE_FREQS[semitone] * (2 ** (self.octave - 4))
                notes.append((freq, dur))
                continue
            self._advance()
        return notes

    def save_state(self):
        global _mml_octave, _mml_length, _mml_tempo, _mml_style
        _mml_octave = self.octave
        _mml_length = self.length
        _mml_tempo = self.tempo
        _mml_style = self.style


def _reset_mml_state():
    global _mml_octave, _mml_length, _mml_tempo, _mml_style
    _mml_octave = 4
    _mml_length = 4
    _mml_tempo = 120
    _mml_style = 7 / 8


def qb_play(mml_string):
    """Play MML string — each note posted to main thread + blocking wait."""
    parser = _MMLParser(mml_string)
    notes = parser.parse()
    parser.save_state()

    for freq, dur in notes:
        if freq <= 0:
            pygame.time.wait(int(dur * 1000))
        else:
            _post_sound(freq, int(dur * 1000))
            pygame.time.wait(int(dur * 1000))


def qb_play_interruptible(mml_string):
    """Play MML but return True if a key is pressed."""
    parser = _MMLParser(mml_string)
    notes = parser.parse()
    parser.save_state()

    for freq, dur in notes:
        if _check_key():
            return True
        if freq <= 0:
            end_time = pygame.time.get_ticks() + int(dur * 1000)
            while pygame.time.get_ticks() < end_time:
                if _check_key():
                    return True
                pygame.time.wait(5)
        else:
            _post_sound(freq, int(dur * 1000))
            end_time = pygame.time.get_ticks() + int(dur * 1000)
            while pygame.time.get_ticks() < end_time:
                if _check_key():
                    return True
                pygame.time.wait(5)
    return False


def _check_key():
    """Check if any key has been pressed."""
    from cws_screen_pygame import flip as _flip
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            raise SystemExit
        if event.type == pygame.VIDEORESIZE:
            _flip()
        if event.type == pygame.KEYDOWN:
            return True
    return False


def shen(g):
    """Play Shenandoah tune. Interruptible between phrases."""
    if g.noise != 2:
        return

    phrases = [
        "T90MFMNo1c4f8f8f4.",
        "g8a8b-8o2d8c4.",
        "MLf8e8MNd4.c8d8c8o1a8o2c4.c4d8d8d4.",
        "o1a8o2c8o1a8g8f4.g4a4.f8",
        "a8o2d8c4.o1f8g8a4.f8g4f2.",
    ]

    for phrase in phrases:
        if _check_key():
            g.choose = 1
            return
        if qb_play_interruptible(phrase):
            g.choose = 1
            return
