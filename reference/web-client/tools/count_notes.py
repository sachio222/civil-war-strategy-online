#!/usr/bin/env python3
"""Count notes from PLAY strings - no js_bridge dependency."""

_NOTE_NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _parse_number(s: str, i: int):
    start = i
    while i < len(s) and s[i].isdigit():
        i += 1
    if i > start:
        return int(s[start:i]), i
    return None, i


def parse_play(play_string: str) -> list:
    events = []
    i = 0
    s = play_string.upper()
    octave = 4
    default_length = 4
    tempo = 120
    articulation = 0.875

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
        if ch in " \t\r\n":
            continue
        if ch == "O":
            num, i = _parse_number(s, i)
            if num is not None:
                octave = max(0, min(6, num))
            continue
        if ch == "<":
            octave = max(0, octave - 1)
            continue
        if ch == ">":
            octave = min(6, octave + 1)
            continue
        if ch == "L":
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                default_length = num
            continue
        if ch == "T":
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                tempo = num
            continue
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
            continue
        if ch in _NOTE_NAMES:
            semitone = _NOTE_NAMES[ch]
            if i < len(s) and s[i] in ("+", "#"):
                semitone += 1
                i += 1
            elif i < len(s) and s[i] == "-":
                semitone -= 1
                i += 1
            note_octave = octave
            if semitone >= 12:
                semitone -= 12
                note_octave += 1
            elif semitone < 0:
                semitone += 12
                note_octave -= 1
            length = default_length
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                length = num
            dotted = False
            if i < len(s) and s[i] == ".":
                dotted = True
                i += 1
            events.append(("note", 0))  # placeholder
            continue
        if ch == "P":
            num, i = _parse_number(s, i)
            length = num if num and num > 0 else default_length
            dotted = False
            if i < len(s) and s[i] == ".":
                dotted = True
                i += 1
            events.append(("rest", 0))
            continue
        if ch == "N":
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                events.append(("note", 0))
            elif num == 0:
                events.append(("rest", 0))
            continue

    return events


BATTLE_HYMN = [
    "MST170o1e8o0b8o1e8",
    "e8e4f#8g4f#8",
    "g4e8d2o0b8o1d2 ",
    "o1e8o0b8o1e8e8e4f#8g4f#8g4a8b2g8b2MLg16a16",
    "MSb4b8b8a8g8a4a8a4f#8g4g8MLg8f#8",
    "MSe8f#4f#8f#8g8a8b4.a4.g4.f#4.o0b8o1e8e8e4d8e2.",
]

SHENANDOAH = [
    "T90MFMNo1c4f8f8f4.",
    "g8a8b-8o2d8c4.",
    "MLf8e8MNd4.c8d8c8o1a8o2c4.c4d8d8d4.",
    "o1a8o2c8o1a8g8f4.g4a4.f8",
    "a8o2d8c4.o1f8g8a4.f8g4f2.",
]

# QBasic: precise manual count from PLAY strings (token-by-token)


def qb_count_battle_hymn():
    # 1: MST170o1e8 o0b8 o1e8 -> e,b,e = 3
    # 2: e8 e4 f#8 g4 f#8 = 5
    # 3: g4 e8 d2 o0b8 o1d2 -> g,e,d,b,d = 5
    # 4: o1e8 o0b8 o1e8 e8 e4 f#8 g4 f#8 g4 a8 b2 g8 b2 ML g16 a16 = 15
    # 5: MS b4 b8 b8 a8 g8 a4 a8 a4 f#8 g4 g8 ML g8 f#8 = 13
    # 6: MS e8 f#4 f#8 f#8 g8 a8 b4. a4. g4. f#4. o0b8 o1e8 e8 e4 d8 e2. = 16
    return 3 + 5 + 5 + 15 + 13 + 16  # 57


def qb_count_shenandoah():
    # 1: T90MFMN o1c4 f8 f8 f4. -> c,f,f,f = 4
    # 2: g8 a8 b-8 o2d8 c4. -> g,a,b-,d,c = 5
    # 3: ML f8 e8 MN d4. c8 d8 c8 o1a8 o2c4. c4 d8 d8 d4. -> f,e,d,c,d,c,a,c,c,d,d,d = 12
    # 4: o1a8 o2c8 o1a8 g8 f4. g4 a4. f8 -> a,c,a,g, f,g,a,f = 8
    # 5: a8 o2d8 c4. o1f8 g8 a4. f8 g4 f2. -> a,d,c,f,g,a,f,g,f = 9
    return 4 + 5 + 12 + 8 + 9  # 38


def parse_play_verbose(play_string: str) -> list:
    """Same as parse_play but returns (note/rest, note_name) for debugging."""
    events = []
    i = 0
    s = play_string.upper()
    octave = 4
    default_length = 4
    tempo = 120
    articulation = 0.875
    note_names = ["C", "C#", "D", "D#", "E",
                  "F", "F#", "G", "G#", "A", "A#", "B"]

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
        if ch in " \t\r\n":
            continue
        if ch == "O":
            num, i = _parse_number(s, i)
            if num is not None:
                octave = max(0, min(6, num))
            continue
        if ch == "<":
            octave = max(0, octave - 1)
            continue
        if ch == ">":
            octave = min(6, octave + 1)
            continue
        if ch == "L":
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                default_length = num
            continue
        if ch == "T":
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                tempo = num
            continue
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
            continue
        if ch in _NOTE_NAMES:
            semitone = _NOTE_NAMES[ch]
            if i < len(s) and s[i] in ("+", "#"):
                semitone += 1
                i += 1
            elif i < len(s) and s[i] == "-":
                semitone -= 1
                i += 1
            note_octave = octave
            if semitone >= 12:
                semitone -= 12
                note_octave += 1
            elif semitone < 0:
                semitone += 12
                note_octave -= 1
            length = default_length
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                length = num
            dotted = False
            if i < len(s) and s[i] == ".":
                dotted = True
                i += 1
            name = note_names[semitone] if semitone < 12 else "?"
            events.append(("note", f"O{note_octave}{name}"))
            continue
        if ch == "P":
            num, i = _parse_number(s, i)
            dotted = False
            if i < len(s) and s[i] == ".":
                dotted = True
                i += 1
            events.append(("rest", "P"))
            continue
        if ch == "N":
            num, i = _parse_number(s, i)
            if num is not None and num > 0:
                events.append(("note", f"N{num}"))
            elif num == 0:
                events.append(("rest", "N0"))
            continue

    return events


if __name__ == "__main__":
    bh = parse_play(" ".join(BATTLE_HYMN))
    sh = parse_play(" ".join(SHENANDOAH))
    bh_notes = sum(1 for e in bh if e[0] == "note")
    sh_notes = sum(1 for e in sh if e[0] == "note")

    bh_v = parse_play_verbose(" ".join(BATTLE_HYMN))
    print("BATTLE_HYMN notes (Python):")
    for i, (t, n) in enumerate(bh_v):
        if t == "note":
            print(f"  {i+1:2}: {n}")

    sh_v = parse_play_verbose(" ".join(SHENANDOAH))
    print("SHENANDOAH notes (Python):")
    for i, (t, n) in enumerate(sh_v):
        if t == "note":
            print(f"  {i+1:2}: {n}")

    print()
    print("Python parser output:")
    print(f"  BATTLE_HYMN: {bh_notes} notes")
    print(f"  SHENANDOAH:  {sh_notes} notes")
    print()
    print("QBasic expected (manual count):")
    qb_bh = qb_count_battle_hymn()
    qb_sh = qb_count_shenandoah()
    print(f"  BATTLE_HYMN: {qb_bh} notes")
    print(f"  SHENANDOAH:  {qb_sh} notes")
    print()
    print("EQUAL?", bh_notes == qb_bh and sh_notes == qb_sh)
