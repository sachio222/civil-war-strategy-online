"""sound.py -- QBasic PLAY string parser + Web Audio synthesis.

Parses QBasic PLAY commands and synthesizes them as square waves using
the Web Audio API, matching the PC speaker sound of the original game.

QBasic PLAY command reference:
  O n   - Set octave (0-6)
  L n   - Set default note length (1=whole, 2=half, 4=quarter, etc.)
  T n   - Set tempo in quarter notes per minute
  MS    - Music staccato (3/4 duration)
  MN    - Music normal (7/8 duration)
  ML    - Music legato (full duration)
  MF    - Music foreground (play and wait)
  MB    - Music background (play async)
  C-B   - Play note C D E F G A B
  # +   - Sharp
  -     - Flat
  .     - Dotted (1.5x duration)
  P n   - Pause/rest
  N n   - Play note by number (0-84)

Note frequencies: C4 = 261.63 Hz (middle C is octave 4 in QBasic PLAY)
"""

import asyncio
import math
from js_bridge import get_audio_context, log

# --------------------------------------------------------------------------- #
#  Note frequency table (12-TET, A4 = 440 Hz)
# --------------------------------------------------------------------------- #
# QBasic octave 0 starts at C below piano range
# Octave 4 = middle C area
_NOTE_NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _note_freq(octave: int, semitone: int) -> float:
    """Get frequency for a note given octave (0-6) and semitone (0-11)."""
    # MIDI note: octave 4 C = MIDI 60
    midi = (octave + 1) * 12 + semitone
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


# --------------------------------------------------------------------------- #
#  NoteEvent dataclass
# --------------------------------------------------------------------------- #
class NoteEvent:
    __slots__ = ("freq_hz", "duration_sec", "articulation")

    def __init__(self, freq_hz: float, duration_sec: float, articulation: float = 0.875):
        self.freq_hz = freq_hz
        self.duration_sec = duration_sec
        self.articulation = articulation  # fraction of duration the note sounds


# --------------------------------------------------------------------------- #
#  PLAY string parser
# --------------------------------------------------------------------------- #
def parse_play(play_string: str) -> list:
    """Parse a QBasic PLAY string into a list of NoteEvent objects."""
    events = []
    i = 0
    s = play_string.upper()

    # State
    octave = 4
    default_length = 4  # quarter note
    tempo = 120  # quarter notes per minute
    articulation = 0.875  # MN = 7/8

    def beat_duration():
        return 60.0 / tempo

    def note_duration(length, dotted):
        dur = (4.0 / length) * beat_duration()
        if dotted:
            dur *= 1.5
        return dur

    while i < len(s):
        ch = s[i]
        i += 1

        # Skip whitespace
        if ch in " \t\r\n":
            continue

        # Octave
        if ch == "O":
            num, i = _parse_number(s, i)
            if num is not None:
                octave = max(0, min(6, num))
            continue

        # Octave up/down
        if ch == "<":
            octave = max(0, octave - 1)
            continue
        if ch == ">":
            octave = min(6, octave + 1)
            continue

        # Length
        if ch == "L":
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                default_length = num
            continue

        # Tempo
        if ch == "T":
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                tempo = num
            continue

        # Music style
        if ch == "M":
            if i < len(s):
                style = s[i]
                i += 1
                if style == "S":
                    articulation = 0.75
                elif style == "N":
                    articulation = 0.875
                elif style == "L":
                    articulation = 1.0
                elif style == "F":
                    pass  # foreground (default, we always wait)
                elif style == "B":
                    pass  # background (we handle async elsewhere)
            continue

        # Note (C D E F G A B)
        if ch in _NOTE_NAMES:
            semitone = _NOTE_NAMES[ch]

            # Check for sharp/flat
            if i < len(s) and s[i] in ("+", "#"):
                semitone += 1
                i += 1
            elif i < len(s) and s[i] == "-":
                semitone -= 1
                i += 1

            # Wrap semitone
            note_octave = octave
            if semitone >= 12:
                semitone -= 12
                note_octave += 1
            elif semitone < 0:
                semitone += 12
                note_octave -= 1

            # Optional length override
            length = default_length
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                length = num

            # Check for dot
            dotted = False
            if i < len(s) and s[i] == ".":
                dotted = True
                i += 1

            freq = _note_freq(note_octave, semitone)
            dur = note_duration(length, dotted)
            events.append(NoteEvent(freq, dur, articulation))
            continue

        # Pause
        if ch == "P":
            num, i = _parse_number(s, i)
            length = num if num and num > 0 else default_length
            dotted = False
            if i < len(s) and s[i] == ".":
                dotted = True
                i += 1
            dur = note_duration(length, dotted)
            events.append(NoteEvent(0, dur, 0))  # freq=0 means rest
            continue

        # Note by number
        if ch == "N":
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                # N maps note 1=C0, 13=C1, etc.
                n_octave = (num - 1) // 12
                n_semi = (num - 1) % 12
                freq = _note_freq(n_octave, n_semi)
                dur = note_duration(default_length, False)
                events.append(NoteEvent(freq, dur, articulation))
            elif num == 0:
                # N0 = rest
                dur = note_duration(default_length, False)
                events.append(NoteEvent(0, dur, 0))
            continue

    return events


def _parse_number(s: str, i: int):
    """Parse an integer starting at position i. Returns (number, new_i) or (None, i)."""
    start = i
    while i < len(s) and s[i].isdigit():
        i += 1
    if i > start:
        return int(s[start:i]), i
    return None, i


# --------------------------------------------------------------------------- #
#  All PLAY strings from CWSTRAT.BAS
# --------------------------------------------------------------------------- #

# Title screen: Battle Hymn of the Republic (CWSTRAT.BAS lines 187-197)
BATTLE_HYMN = [
    "MST170o1e8o0b8o1e8",
    "e8e4f#8g4f#8",
    "g4e8d2o0b8o1d2 ",
    "o1e8o0b8o1e8e8e4f#8g4f#8g4a8b2g8b2MLg16a16",
    "MSb4b8b8a8g8a4a8a4f#8g4g8MLg8f#8",
    "MSe8f#4f#8f#8g8a8b4.a4.g4.f#4.o0b8o1e8e8e4d8e2.",
]

# Title screen: Shenandoah (CWSTRAT.BAS SUB shen lines 3835-3843)
SHENANDOAH = [
    "T90MFMNo1c4f8f8f4.",
    "g8a8b-8o2d8c4.",
    "MLf8e8MNd4.c8d8c8o1a8o2c4.c4d8d8d4.",
    "o1a8o2c8o1a8g8f4.g4a4.f8",
    "a8o2d8c4.o1f8g8a4.f8g4f2.",
]

# Army surrender (line 2605)
SURRENDER = "MFMST220o3e4g8g2.g8g8g8o4c2"

# Commerce raiding (line 2685)
COMMERCE_RAID = "t210l8o4co3bo4l4co3ccL8gfego4co3bo4c"

# Gettysburg Address music (lines 2886-2894)
GETTYSBURG = [
    "T130MFMSO2f16f8",
    "f16f8a16a8o3c16c8o2a16a8f16f8",
    "a16a8o3c16c4o2a16a8f16f8",
    "e16e8g16g8o3c16c8o2b16b8g16g8",
    "a16a8o3c16c4",
]

# Union city capture (line 2901)
UNION_CAPTURE = "MNMFL16o2T120dd.dd.co1b.o2do3g.ab.bb.ag"

# Rebel city capture (line 2902)
REBEL_CAPTURE = "MNMFT160o2L16geL8ccL16cdefL8ggge"

# Dixie - Rebel victory (lines 3791-3799)
DIXIE = [
    "MBMS T120 O3 L16 g e",
    "c8 c8 d e f8 f g a",
    "l8 o4 c o3 a f a l16 g f",
    "l8 e c d l16 e f l8 e d",
    "c l16 o2 b o3 c l8 d e c o2 a",
    "b l16 o3 c d l8 e c o2 a",
    "l16 f g a b l2 o3 c",
    "P4",
]


# --------------------------------------------------------------------------- #
#  Web Audio synthesis
# --------------------------------------------------------------------------- #
async def play_notes(events: list, volume: float = 0.15):
    """Play a list of NoteEvents using Web Audio square wave synthesis."""
    audio_ctx = get_audio_context()
    if audio_ctx is None:
        return

    current_time = audio_ctx.currentTime

    for event in events:
        if event.freq_hz > 0:
            osc = audio_ctx.createOscillator()
            gain = audio_ctx.createGain()

            osc.type = "square"
            osc.frequency.setValueAtTime(event.freq_hz, current_time)

            gain.gain.setValueAtTime(volume, current_time)

            # Articulation: note sounds for articulation fraction, then silence
            note_on_dur = event.duration_sec * event.articulation
            gain.gain.setValueAtTime(volume, current_time + note_on_dur * 0.95)
            gain.gain.linearRampToValueAtTime(0, current_time + note_on_dur)

            osc.connect(gain)
            gain.connect(audio_ctx.destination)

            osc.start(current_time)
            osc.stop(current_time + event.duration_sec)

        current_time += event.duration_sec


async def play_string(play_string: str, volume: float = 0.15):
    """Parse and play a single PLAY string."""
    events = parse_play(play_string)
    await play_notes(events, volume)


async def play_strings(play_strings: list, volume: float = 0.15):
    """Parse and play a sequence of PLAY strings. State (tempo, octave, etc.)
    persists across strings, so we must parse as one combined string."""
    combined = " ".join(play_strings)
    events = parse_play(combined)
    await play_notes(events, volume)


async def play_battle_hymn(volume: float = 0.15):
    """Play Battle Hymn of the Republic (title screen, Union)."""
    await play_strings(BATTLE_HYMN, volume)


async def play_shenandoah(volume: float = 0.15):
    """Play Shenandoah (title screen, Confederate)."""
    await play_strings(SHENANDOAH, volume)


async def play_surrender(volume: float = 0.15):
    """Play the surrender fanfare."""
    await play_string(SURRENDER, volume)


async def play_commerce_raid(volume: float = 0.15):
    """Play the commerce raiding tune."""
    await play_string(COMMERCE_RAID, volume)


async def play_gettysburg(volume: float = 0.15):
    """Play the Gettysburg Address music."""
    await play_strings(GETTYSBURG, volume)


async def play_union_capture(volume: float = 0.15):
    """Play the Union city capture tune."""
    await play_string(UNION_CAPTURE, volume)


async def play_rebel_capture(volume: float = 0.15):
    """Play the Rebel city capture tune."""
    await play_string(REBEL_CAPTURE, volume)


async def play_dixie(volume: float = 0.15):
    """Play Dixie (Rebel victory)."""
    await play_strings(DIXIE, volume)


def qb_sound(freq: float, ticks: float, volume: float = 0.15):
    """QBasic SOUND statement: freq in Hz, duration in clock ticks (18.2 ticks = 1 sec).

    Fire-and-forget square wave, matching the PC speaker output of the original game.
    """
    audio_ctx = get_audio_context()
    if audio_ctx is None:
        return
    duration = ticks / 18.2
    t = audio_ctx.currentTime
    osc = audio_ctx.createOscillator()
    gain = audio_ctx.createGain()
    osc.type = "square"
    osc.frequency.setValueAtTime(freq, t)
    gain.gain.setValueAtTime(volume, t)
    gain.gain.setValueAtTime(volume, t + duration * 0.9)
    gain.gain.linearRampToValueAtTime(0, t + duration)
    osc.connect(gain)
    gain.connect(audio_ctx.destination)
    osc.start(t)
    osc.stop(t + duration + 0.01)


def qb_sound_seq(tones: list, volume: float = 0.15):
    """Play sequential (freq, ticks) pairs, matching QBasic multi-SOUND lines."""
    audio_ctx = get_audio_context()
    if audio_ctx is None:
        return
    t = audio_ctx.currentTime
    for freq, ticks in tones:
        duration = ticks / 18.2
        if freq > 0:
            osc = audio_ctx.createOscillator()
            g = audio_ctx.createGain()
            osc.type = "square"
            osc.frequency.setValueAtTime(freq, t)
            g.gain.setValueAtTime(volume, t)
            g.gain.setValueAtTime(volume, t + duration * 0.9)
            g.gain.linearRampToValueAtTime(0, t + duration)
            osc.connect(g)
            g.connect(audio_ctx.destination)
            osc.start(t)
            osc.stop(t + duration + 0.01)
        t += duration


# --------------------------------------------------------------------------- #
#  Named sound effects -- exact ports of QBasic SOUND calls in CWSTRAT.BAS
# --------------------------------------------------------------------------- #

def snd_menu_confirm():
    """SOUND 700, .5 -- menu Enter/confirm (line 4905)."""
    qb_sound(700, 0.5)


def snd_recruit():
    """SOUND 2222, .5 -- recruit troops (line 1949)."""
    qb_sound(2222, 0.5)


def snd_move_order():
    """SOUND 2200, .5: SOUND 2900, .7 -- army move confirmed (line 886)."""
    qb_sound_seq([(2200, 0.5), (2900, 0.7)])


def snd_cancel():
    """SOUND 2999, .5 -- cancel move order (line 2791)."""
    qb_sound(2999, 0.5)


def snd_railroad_depart():
    """SOUND 2222, 1 -- railroad departure (line 2076)."""
    qb_sound(2222, 1)


def snd_railroad_arrive():
    """SOUND 1200, 2 -- train arrived at destination (line 2093)."""
    qb_sound(1200, 2)


def snd_combat():
    """SOUND 77, .5: SOUND 59, .5 -- combat exchange / naval hit (lines 1022, 1641, 1826)."""
    qb_sound_seq([(77, 0.5), (59, 0.5)])


def snd_fortify():
    """SOUND 3999, .3 -- fortification built (line 1403)."""
    qb_sound(3999, 0.3)


def snd_supply():
    """SOUND 4500, .5 -- resupply complete (line 3692)."""
    qb_sound(4500, 0.5)


def snd_fleet():
    """SOUND 3000, 1 -- fleet build / fleet action (lines 1603, 1611)."""
    qb_sound(3000, 1)


def snd_city_event():
    """SOUND 4000, .7 -- city conquest / supply event (line 1181)."""
    qb_sound(4000, 0.7)


def snd_drill():
    """SOUND 2222, 1 -- drill army (line 482)."""
    qb_sound(2222, 1)


def snd_detach():
    """SOUND 2222, 1 -- detach unit (line 469)."""
    qb_sound(2222, 1)


def snd_reinforce():
    """SOUND 2222, 1 -- army reinforcement (line 2189)."""
    qb_sound(2222, 1)


def snd_setting_change():
    """SOUND 999, 1 -- utility setting change (lines 536, 546, 578)."""
    qb_sound(999, 1)


def snd_graphics_change():
    """SOUND 2700, 1 -- graphics mode change (line 562)."""
    qb_sound(2700, 1)


def snd_raider_loss():
    """SOUND 590, .5: SOUND 999, .5: SOUND 1999, .5 -- commerce raider lost ship (line 2692)."""
    qb_sound_seq([(590, 0.5), (999, 0.5), (1999, 0.5)])


def snd_ironclad_event():
    """FOR k=1 TO 5: SOUND 140,1: SOUND 37,1: NEXT k -- ironclad development (line 3126)."""
    tones = []
    for _ in range(5):
        tones.append((140, 1))
        tones.append((37, 1))
    qb_sound_seq(tones)


def snd_destruction(volume: float = 0.15):
    """SOUND 37+50*RND, .03 -- army destruction fire effect (line 1384). Call in a loop."""
    import random
    qb_sound(37 + 50 * random.random(), 0.03, volume)


def snd_animate_step():
    """SOUND 200, .1: SOUND 50, .1 -- army movement animation step (line 860)."""
    qb_sound_seq([(200, 0.1), (50, 0.1)])


# Backwards-compat aliases
def menu_tick():
    """No-op. QBasic had no arrow-key navigation sound."""
    pass


def menu_confirm():
    """SOUND 700, .5 -- exact QBasic menu confirm."""
    snd_menu_confirm()


def stop_all():
    """Stop all currently playing audio by closing and recreating the AudioContext."""
    from js import window  # type: ignore
    audio_ctx = get_audio_context()
    if audio_ctx is None:
        return
    try:
        audio_ctx.close()
    except Exception:
        pass
    # Clear the cached context so a new one is created on next use
    try:
        window._cwsAudioCtx = None
    except Exception:
        pass
