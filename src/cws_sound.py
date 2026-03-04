"""cws_sound.py - Exact QB64 SOUND and PLAY command implementation.

Direct port of cws_sound.bm + all QB64 audio primitives.

QB64 audio commands:
    SOUND freq, duration   -- pure tone; duration in clock ticks (18.2/sec)
    PLAY "MML string"      -- Music Macro Language

All sounds gated by g.noise:  0=silent, 1=SFX only, 2=SFX+music

Dependencies: pygame.mixer (no numpy -- uses Python array module)
"""

import math
import array
import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cws_globals import GameState

# ── Constants ─────────────────────────────────────────────────────────────

SAMPLE_RATE = 44100
MAX_AMPLITUDE = 24000          # ~73% of 32767 to avoid clipping
QB64_TICKS_PER_SEC = 18.2     # QB64 clock tick rate

# QB64 note frequencies for octave 4 (middle octave)
# C4=262, C#4=277, D4=294, ... B4=494
_BASE_FREQS = {
    0: 262,   # C
    1: 277,   # C#
    2: 294,   # D
    3: 311,   # D#
    4: 330,   # E
    5: 349,   # F
    6: 370,   # F#
    7: 392,   # G
    8: 415,   # G#
    9: 440,   # A
    10: 466,  # A#
    11: 494,  # B
}

# Map note letters to semitone offset from C
_NOTE_MAP = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11,
}

# Mixer channel reserved for sound engine
_channel: pygame.mixer.Channel | None = None
_initialized = False

# Persistent MML state (QB64 PLAY preserves state between calls)
_mml_octave = 4
_mml_length = 4
_mml_tempo = 120
_mml_style = 7 / 8   # MN = normal


# ── Initialization ────────────────────────────────────────────────────────

def init_sound() -> None:
    """Initialize the sound engine. Call after pygame.mixer.init()."""
    global _channel, _initialized
    if _initialized:
        return
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1,
                              buffer=2048)
        _channel = pygame.mixer.Channel(0)
        _initialized = True
    except pygame.error:
        _initialized = False


# ── Tone generation ───────────────────────────────────────────────────────

def _gen_tone(freq: float, duration_sec: float,
              amplitude: int = MAX_AMPLITUDE) -> pygame.mixer.Sound:
    """Generate a square-wave tone as a pygame.mixer.Sound.

    QBasic/QB64 SOUND and PLAY produce square waves (PC speaker emulation).
    50% duty cycle, no fade envelope — hard start/stop matches the real
    PC speaker behavior (PIT 8253 timer driving the speaker cone directly).
    16-bit signed mono at SAMPLE_RATE.
    """
    n_samples = max(1, int(SAMPLE_RATE * duration_sec))

    # Round to nearest complete cycle to minimise the end-of-tone click
    if freq > 0:
        samples_per_cycle = SAMPLE_RATE / freq
        full_cycles = max(1, round(n_samples / samples_per_cycle))
        n_samples = int(round(full_cycles * samples_per_cycle))

    buf = array.array('h', [0] * n_samples)

    if freq > 0:
        pos_amp = amplitude
        neg_amp = -amplitude
        for i in range(n_samples):
            # Compute phase 0.0-1.0 independently per sample (no drift)
            phase = (freq * i / SAMPLE_RATE) % 1.0
            buf[i] = pos_amp if phase < 0.5 else neg_amp

    return pygame.mixer.Sound(buffer=buf)


# ── QB64 SOUND command ────────────────────────────────────────────────────

def qb_sound(freq: float, duration_ticks: float) -> None:
    """Exact port of QB64: SOUND freq, duration.

    freq:           frequency in Hz (37-32767; 0 = silence)
    duration_ticks: duration in clock ticks (18.2 ticks/sec)

    QB64 SOUND is blocking -- it plays for the full duration before returning.
    """
    if not _initialized:
        init_sound()
    if not _initialized or not _channel:
        return

    duration_sec = max(0.001, duration_ticks / QB64_TICKS_PER_SEC)

    if freq < 37:
        # QB64: frequencies below 37 are treated as silence/pause
        pygame.time.wait(int(duration_sec * 1000))
        return

    snd = _gen_tone(freq, duration_sec)
    duration_ms = int(duration_sec * 1000)
    _channel.play(snd)
    # Timed wait for exact duration (QB64 SOUND is synchronous).
    # Using timed wait instead of get_busy() which returns early
    # when the audio buffer drains, causing notes to be too short.
    pygame.time.wait(duration_ms)


# ── MML Parser for QB64 PLAY command ─────────────────────────────────────

class _MMLParser:
    """Parse and play a QB64 PLAY string (Music Macro Language).

    Supports: notes A-G with #/+/-, O (octave), L (length), T (tempo),
    P (pause), . (dotted), > < (octave shift), MS/MN/ML, MF/MB, N (note#)
    """

    def __init__(self, mml: str):
        self.mml = mml.upper()
        self.pos = 0
        # Restore persistent state from module globals (QB64 preserves between calls)
        self.octave = _mml_octave
        self.length = _mml_length
        self.tempo = _mml_tempo
        self.style = _mml_style
        self.foreground = True    # MF = blocking

    def _peek(self) -> str:
        if self.pos < len(self.mml):
            return self.mml[self.pos]
        return ''

    def _advance(self) -> str:
        ch = self.mml[self.pos]
        self.pos += 1
        return ch

    def _read_number(self) -> int | None:
        """Read an integer from current position, or None if not a digit."""
        start = self.pos
        while self.pos < len(self.mml) and self.mml[self.pos].isdigit():
            self.pos += 1
        if self.pos > start:
            return int(self.mml[start:self.pos])
        return None

    def _note_duration(self, note_len: int | None) -> float:
        """Calculate note duration in seconds from a note length value."""
        if note_len is None or note_len < 1:
            note_len = self.length
        # Quarter note duration from tempo
        quarter_sec = 60.0 / self.tempo
        # Whole note = 4 quarters
        return (4.0 / note_len) * quarter_sec

    def _count_dots(self) -> int:
        """Count and consume any dots after a note/rest."""
        dots = 0
        while self.pos < len(self.mml) and self.mml[self.pos] == '.':
            dots += 1
            self.pos += 1
        return dots

    def _apply_dots(self, duration: float, dots: int) -> float:
        """Apply dotted note lengthening."""
        extra = duration
        for _ in range(dots):
            extra *= 0.5
            duration += extra
        return duration

    def parse(self) -> list:
        """Parse the MML string into a list of (freq, duration_sec) tuples."""
        notes = []

        while self.pos < len(self.mml):
            ch = self._peek()

            # Skip whitespace
            if ch in ' \t\n':
                self._advance()
                continue

            # M commands: MS, MN, ML, MF, MB
            if ch == 'M':
                self._advance()
                if self._peek() == 'S':
                    self._advance()
                    self.style = 3 / 4      # staccato
                elif self._peek() == 'N':
                    self._advance()
                    self.style = 7 / 8      # normal
                elif self._peek() == 'L':
                    self._advance()
                    self.style = 1.0        # legato
                elif self._peek() == 'F':
                    self._advance()
                    self.foreground = True   # foreground
                elif self._peek() == 'B':
                    self._advance()
                    self.foreground = False  # background
                continue

            # Tempo
            if ch == 'T':
                self._advance()
                n = self._read_number()
                if n is not None:
                    self.tempo = max(32, min(255, n))
                continue

            # Octave
            if ch == 'O':
                self._advance()
                n = self._read_number()
                if n is not None:
                    self.octave = max(0, min(6, n))
                continue

            # Octave shift
            if ch == '>':
                self._advance()
                self.octave = min(6, self.octave + 1)
                continue
            if ch == '<':
                self._advance()
                self.octave = max(0, self.octave - 1)
                continue

            # Default length
            if ch == 'L':
                self._advance()
                n = self._read_number()
                if n is not None and n >= 1:
                    self.length = n
                # Check for dots on the L command itself
                self._count_dots()
                continue

            # Pause / Rest
            if ch == 'P':
                self._advance()
                n = self._read_number()
                dur = self._note_duration(n)
                dots = self._count_dots()
                dur = self._apply_dots(dur, dots)
                notes.append((0, dur))
                continue

            # Note by number: N0-N84
            if ch == 'N':
                self._advance()
                n = self._read_number()
                if n is not None:
                    if n == 0:
                        dur = self._note_duration(None)
                        notes.append((0, dur))
                    else:
                        # N maps: 1=C0, 2=C#0, ... 12=B0, 13=C1, ...
                        octave = (n - 1) // 12
                        semitone = (n - 1) % 12
                        freq = _BASE_FREQS[semitone] * (2 ** (octave - 4))
                        dur = self._note_duration(None)
                        dots = self._count_dots()
                        dur = self._apply_dots(dur, dots)
                        notes.append((freq, dur))
                continue

            # Notes A-G
            if ch in _NOTE_MAP:
                self._advance()
                semitone = _NOTE_MAP[ch]

                # Sharp / flat
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

                # Note length override
                n = self._read_number()
                dur = self._note_duration(n)

                # Dots
                dots = self._count_dots()
                dur = self._apply_dots(dur, dots)

                # Frequency
                freq = _BASE_FREQS[semitone] * (2 ** (self.octave - 4))
                notes.append((freq, dur))
                continue

            # Unknown character -- skip
            self._advance()

        return notes

    def save_state(self) -> None:
        """Save parser state back to module globals for next qb_play call."""
        global _mml_octave, _mml_length, _mml_tempo, _mml_style
        _mml_octave = self.octave
        _mml_length = self.length
        _mml_tempo = self.tempo
        _mml_style = self.style


def _reset_mml_state() -> None:
    """Reset persistent MML state to QB64 defaults."""
    global _mml_octave, _mml_length, _mml_tempo, _mml_style
    _mml_octave = 4
    _mml_length = 4
    _mml_tempo = 120
    _mml_style = 7 / 8


# ── QB64 PLAY command ─────────────────────────────────────────────────────

def qb_play(mml_string: str) -> None:
    """Exact port of QB64: PLAY "MML string".

    Parses the MML string and plays each note sequentially (foreground mode).
    State (octave, length, tempo, style) persists between calls, matching QB64.
    """
    if not _initialized:
        init_sound()
    if not _initialized or not _channel:
        return

    parser = _MMLParser(mml_string)
    notes = parser.parse()
    parser.save_state()

    for freq, dur in notes:
        if freq <= 0:
            pygame.time.wait(int(dur * 1000))
        else:
            # Tone fills the full note duration.  QB64's PC speaker just
            # switches frequency instantly — no audible silence gap between
            # notes.  Articulation comes from the channel stopping when the
            # next note starts.
            snd = _gen_tone(freq, dur)
            _channel.play(snd)
            pygame.time.wait(int(dur * 1000))


def qb_play_interruptible(mml_string: str) -> bool:
    """Play MML but return True immediately if any key is pressed."""
    if not _initialized:
        init_sound()
    if not _initialized or not _channel:
        return _check_key()

    parser = _MMLParser(mml_string)
    notes = parser.parse()
    parser.save_state()

    for freq, dur in notes:
        if _check_key():
            _channel.stop()
            return True

        if freq <= 0:
            end_time = pygame.time.get_ticks() + int(dur * 1000)
            while pygame.time.get_ticks() < end_time:
                if _check_key():
                    return True
                pygame.time.wait(5)
        else:
            snd = _gen_tone(freq, dur)
            _channel.play(snd)
            end_time = pygame.time.get_ticks() + int(dur * 1000)
            while pygame.time.get_ticks() < end_time:
                if _check_key():
                    _channel.stop()
                    return True
                pygame.time.wait(5)

    return False


def _check_key() -> bool:
    """Check if any key has been pressed (non-blocking). Mimics INKEY$<>""."""
    from cws_screen_pygame import flip as _flip
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            raise SystemExit
        if event.type == pygame.VIDEORESIZE:
            _flip()
        if event.type == pygame.KEYDOWN:
            return True
    return False


# ── SUB shen -- Shenandoah (cws_sound.bm L1-15) ─────────────────────────

def shen(g: 'GameState') -> None:
    """Play Shenandoah tune. Interruptible between phrases.

    Original: SUB shen -- cws_sound.bm lines 1-15
    """
    if g.noise != 2:
        return

    phrases = [
        "T90MFMNo1c4f8f8f4.",                       # L5
        "g8a8b-8o2d8c4.",                            # L7
        "MLf8e8MNd4.c8d8c8o1a8o2c4.c4d8d8d4.",      # L9
        "o1a8o2c8o1a8g8f4.g4a4.f8",                 # L11
        "a8o2d8c4.o1f8g8a4.f8g4f2.",                 # L13
    ]

    for phrase in phrases:
        if _check_key():
            g.choose = 1
            return
        if qb_play_interruptible(phrase):
            g.choose = 1
            return
