"""cws_data.py - Data I/O and city occupation.
Direct port of cws_data.bm (QB64) to Python.

Original file: cws_data.bm (119 lines)
Contains:
    SUB filer(switch)   ->  filer(g, switch)   [load/save game data]
    SUB occupy(x)       ->  occupy(g, x)       [recalculate city occupant]

Also contains (extracted from CWSTRAT.BAS main program lines 93-102):
    load_cities(g)      [load cities.grd]

QB64's INPUT #1 is a streaming tokenizer that consumes comma-separated
values across line boundaries. We replicate this with _QBStream.

Dependencies:
    cws_util:     starfin(g, who), bubble(g, limit)
    cws_ui:       menu(g, switch), clrbot(g), clrrite(g)
    cws_map:      usa(g)
    cws_railroad: tinytrain(g, who, flag)
"""

import csv
import os
from typing import TYPE_CHECKING

from cws_globals import UNION, CONFEDERATE
from cws_paths import data_path as _data_path, save_path, save_path_write

if TYPE_CHECKING:
    from cws_globals import GameState


class _QBStream:
    """Emulates QB64's sequential INPUT #1 file reading.

    QB64's INPUT #1 reads comma-separated values from a file stream,
    consuming tokens across line boundaries. Quoted strings are unquoted.
    This class reads the entire file, tokenizes it, and provides
    read_int(), read_float(), read_str() to consume values in order.
    """

    def __init__(self, filepath: str):
        with open(filepath, "r") as f:
            self._text = f.read()
        self._tokens = []
        self._pos = 0
        self._tokenize()

    def _tokenize(self):
        """Parse entire file into a flat list of string tokens."""
        # Use csv.reader to handle quoted strings properly
        # Treat the whole file as one big CSV stream
        reader = csv.reader(self._text.splitlines())
        for row in reader:
            for val in row:
                v = val.strip()
                # QB64 INPUT #1 strips surrounding quotes from strings.
                # csv.reader only strips quotes when the field starts with
                # a quote, but CITIES.GRD has spaces before quotes like
                #   1,265,290, "Atlanta",2,25,...
                # so csv.reader leaves the quotes intact.  Strip them here.
                if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                    v = v[1:-1]
                self._tokens.append(v)

    def read_str(self) -> str:
        """Consume and return next token as string."""
        if self._pos >= len(self._tokens):
            return ""
        val = self._tokens[self._pos]
        self._pos += 1
        return val

    def read_int(self) -> int:
        """Consume and return next token as int."""
        s = self.read_str()
        try:
            return int(float(s))  # handle "1.0" -> 1
        except (ValueError, TypeError):
            return 0

    def read_float(self) -> float:
        """Consume and return next token as float."""
        s = self.read_str()
        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0


class _QBWriter:
    """Emulates QB64's WRITE #1 for saving game data.

    WRITE #1 outputs comma-separated values with strings double-quoted.
    Each WRITE statement ends with a newline.
    """

    def __init__(self, filepath: str):
        self._f = open(filepath, "w")

    def write(self, *values):
        """Write a line of comma-separated values (WRITE #1, ...)."""
        parts = []
        for v in values:
            if isinstance(v, str):
                parts.append(f'"{v}"')
            elif isinstance(v, float):
                parts.append(str(v))
            else:
                parts.append(str(int(v)))
        self._f.write(",".join(parts) + "\n")

    def close(self):
        self._f.close()


# ─────────────────────────────────────────────────────────────────────────────
# SUB filer(switch)  -- lines 1-111
# ─────────────────────────────────────────────────────────────────────────────

def filer(g: 'GameState', switch: int) -> None:
    """Load or save game data.

    Original: SUB filer(switch) -- lines 1-111
    switch=1: Load initial data (cwslead.dat + cws.ini + cws.cfg)
    switch=2: Load saved game (.sav file)
    switch=3: Save game (.sav file)
    """
    if switch == 1:
        _filer_case1(g)
    elif switch == 2:
        _filer_case2(g)
    elif switch == 3:
        _filer_case3(g)


def _filer_case1(g: 'GameState') -> None:
    """Load initial game data: leaders, ini, config.

    Original: filer CASE 1 -- lines 3-33
    """
    # ── L4-6: Load leader names and ratings ───────────────────────
    s = _QBStream(_data_path("cwslead.dat"))
    for i in range(1, 41):                                           # L5
        g.lname[i] = s.read_str()
        g.rating[i] = s.read_int()

    # ── L7-29: Load cws.ini ──────────────────────────────────────
    s = _QBStream(_data_path("cws.ini"))

    for i in range(0, 3):                                            # L8
        g.force[i] = s.read_str()

    for i in range(1, 13):                                           # L9
        g.month_names[i] = s.read_str()

    g.month = s.read_int()                                           # L10
    g.year = s.read_int()

    # Victory conditions                                             # L12
    for i in range(1, 7):
        g.vicflag[i] = s.read_int()
    g.vicflag[3] = int(0.4 * g.vicflag[3])                          # L13

    # Union armies                                                   # L14-17
    a = s.read_int()                                                 # number of Yankee armies
    for i in range(1, a + 1):                                        # L15-17
        g.armyloc[i] = s.read_int()
        g.armysize[i] = s.read_int()
        g.armyexper[i] = s.read_int()
        g.supply[i] = s.read_int()
        if g.armyloc[i] > 0:
            g.occupied[g.armyloc[i]] = i
        g.armyname[i] = g.lname[i]
        g.armylead[i] = g.rating[i]
        g.lname[i] = ""

    # Rebel armies                                                   # L18-22
    a = s.read_int()                                                 # number of Rebel armies
    for i in range(21, 21 + a):                                      # L19-22
        g.armyloc[i] = s.read_int()
        g.armysize[i] = s.read_int()
        g.armyexper[i] = s.read_int()
        g.supply[i] = s.read_int()
        if g.armyloc[i] > 0:
            g.occupied[g.armyloc[i]] = i
        g.armyname[i] = g.lname[i]
        g.armylead[i] = g.rating[i]
        g.lname[i] = ""

    # Cash                                                           # L23
    for i in range(1, 3):
        g.cash[i] = s.read_int()

    # Attack/defense factors                                         # L24
    g.atkfac = s.read_int()
    g.defac = s.read_int()
    g.tcr = s.read_int()

    # Fleets and navy locations                                      # L25
    g.fleet[1] = s.read_str()
    g.navyloc[1] = s.read_int()
    g.fleet[2] = s.read_str()
    g.navyloc[2] = s.read_int()
    for k in range(1, 3):                                            # L26
        g.navysize[k] = len(g.fleet[k])

    # Capital cities                                                 # L27
    g.capcity[1] = s.read_int()
    g.capcity[2] = s.read_int()

    # Star locations on flag                                         # L29
    for i in range(1, 9):
        g.starx[i] = s.read_int()
        g.stary[i] = s.read_int()

    # ── L31-33: Load cws.cfg ─────────────────────────────────────
    _load_cfg(g)


def _filer_case2(g: 'GameState') -> None:
    """Load a saved game from .sav file.

    Original: filer CASE 2 -- lines 35-81
    """
    from cws_util import starfin, bubble
    from cws_ui import menu, clrbot, clrrite
    from cws_map import usa
    from cws_railroad import tinytrain

    # L36: Check if any .sav files exist
    sav_files = []
    for k in range(1, 10):
        t = f"cws{k}.sav"
        if os.path.exists(save_path(t)):
            sav_files.append(k)

    if not sav_files:                                                # L36
        g.choose = -1
        return

    # Build menu of available save files                             # L37-44
    g.mtx[0] = "Load"
    g.size = 0
    for k in range(1, 10):                                           # L39-44
        t = f"cws{k}.sav"
        if os.path.exists(save_path(t)):
            g.size += 1
            g.mtx[g.size] = t
            g.array[g.size] = k

    bubble(g, g.size)                                                # L45
    g.tlx = 67                                                       # L46
    g.tly = int(14 - 0.5 * g.size)
    menu(g, 0)                                                       # L47
    clrrite(g)                                                       # L48

    if g.choose < 1:                                                 # L49
        return

    # Load the selected save file                                    # L50
    sav_path = save_path(f"cws{g.array[g.choose]}.sav")
    s = _QBStream(sav_path)

    g.screen.color(11)                                               # L51
    clrbot(g)
    g.screen.print_text("Loading")

    g.month = s.read_int()                                           # L52
    g.year = s.read_int()
    g.usadv = s.read_int()
    a = s.read_int()                                                 # saved side value

    # Load all 40 army slots                                         # L53-65
    for i in range(1, 41):
        g.armyname[i] = s.read_str()                                # L53
        g.armysize[i] = s.read_int()
        g.armylead[i] = s.read_int()
        g.armyloc[i] = s.read_int()
        g.armyexper[i] = s.read_int()
        g.supply[i] = s.read_int()
        g.armymove[i] = s.read_int()

        if g.armyloc[i] > 0:                                        # L54
            if g.armyname[i] == g.lname[i]:                          # L55
                g.lname[i] = ""                                      # L56
            else:                                                    # L57
                who = UNION                                          # L58
                if i > 20:
                    who = CONFEDERATE
                star, fin = starfin(g, who)                          # L59
                for k in range(star, fin + 1):                       # L60-62
                    if g.armyname[i] == g.lname[k]:
                        g.lname[k] = ""
                        break

    # Load city state                                                # L66
    for i in range(1, 41):
        g.occupied[i] = s.read_int()
        g.cityp[i] = s.read_int()
        g.fort[i] = s.read_int()
        g.screen.print_text(".")

    # Load side state                                                # L67-70
    for i in range(1, 3):
        g.cash[i] = s.read_int()                                    # L67
        g.control[i] = s.read_int()
        g.income[i] = s.read_int()
        g.victory[i] = s.read_int()
        g.capcity[i] = s.read_int()
        g.fleet[i] = s.read_str()                                   # L68
        g.navyloc[i] = s.read_int()
        g.navymove[i] = s.read_int()
        g.rr[i] = s.read_int()
        g.tracks[i] = s.read_int()
        g.navysize[i] = len(g.fleet[i])                             # L69

    # Reload config                                                  # L73-75
    _load_cfg(g)

    # Redraw                                                         # L76-80
    g.screen.cls()                                                   # L76
    usa(g)                                                           # L77
    clrbot(g)
    for k in range(1, 3):                                            # L78-80
        if g.rr[k] > 0:
            tinytrain(g, k, 1)

    g.side = a                                                       # L81


def _filer_case3(g: 'GameState') -> None:
    """Save game to .sav file.

    Original: filer CASE 3 -- lines 83-109
    """
    from cws_ui import menu, clrbot, clrrite
    from cws_map import usa

    # Build menu of save slots                                       # L84-88
    g.mtx[0] = "Save Game"
    for k in range(1, 10):                                           # L85-88
        g.mtx[k] = f"cws{k}.sav"
        if os.path.exists(save_path(g.mtx[k])):
            g.mtx[k] = g.mtx[k] + " +"

    g.tlx = 67                                                       # L89
    g.size = 9
    menu(g, 0)                                                       # L90
    if g.choose < 1:                                                 # L91
        clrrite(g)
        return

    g.screen.color(11)                                               # L92
    clrbot(g)
    g.screen.print_text("Saving")

    # Write save file                                                # L94-102
    sav_path = save_path_write(f"cws{g.choose}.sav")
    w = _QBWriter(sav_path)

    w.write(g.month, g.year, g.usadv, g.side)                       # L95

    for i in range(1, 41):                                           # L96-97
        w.write(g.armyname[i], g.armysize[i], g.armylead[i],
                g.armyloc[i], g.armyexper[i], g.supply[i], g.armymove[i])

    for i in range(1, 41):                                           # L98
        w.write(g.occupied[i], g.cityp[i], g.fort[i])
        g.screen.print_text(".")

    for i in range(1, 3):                                            # L99-101
        w.write(g.cash[i], g.control[i], g.income[i],
                g.victory[i], g.capcity[i])
        w.write(g.fleet[i], g.navyloc[i], g.navymove[i],
                g.rr[i], g.tracks[i])

    w.close()                                                        # L102

    # Save config                                                    # L104-108
    myside = g.side                                                  # L104
    if myside not in (UNION, CONFEDERATE):                            # L105
        myside = UNION
    _save_cfg(g, myside)

    g.screen.cls()                                                   # L109
    usa(g)


def _load_cfg(g: 'GameState') -> None:
    """Load cws.cfg configuration file.

    Original: lines 31-33 and 73-75 of cws_data.bm
    """
    try:
        s = _QBStream(save_path("cws.cfg"))
        g.side = s.read_int()                                        # L32
        g.graf = s.read_int()
        g.noise = s.read_int()
        g.difficult = s.read_int()
        g.player = s.read_int()
        g.turbo = s.read_float()
        g.randbal = s.read_int()
        g.train[1] = s.read_int()
        g.train[2] = s.read_int()
        g.jancam = s.read_int()
        g.realism = s.read_int()
        g.batwon[1] = s.read_int()
        g.batwon[2] = s.read_int()
        g.casualty[1] = s.read_int()
        g.casualty[2] = s.read_int()
        g.history = s.read_int()
        g.bold = s.read_int()
    except FileNotFoundError:
        # Defaults if no config file
        g.side = UNION
        g.graf = 1              # 1 = ROADS shown by default
        g.difficult = 3
        g.player = 1
        g.turbo = 2.0


def _save_cfg(g: 'GameState', myside: int) -> None:
    """Save cws.cfg configuration file.

    Original: lines 106-108 of cws_data.bm
    """
    cfg_path = save_path_write("cws.cfg")
    w = _QBWriter(cfg_path)
    w.write(myside, g.graf, g.noise, g.difficult, g.player,         # L107
            g.turbo, g.randbal, g.train[1], g.train[2],
            g.jancam, g.realism, g.batwon[1], g.batwon[2],
            g.casualty[1], g.casualty[2], g.history, g.bold)
    w.close()


# ─────────────────────────────────────────────────────────────────────────────
# SUB occupy(x)  -- lines 112-118
# ─────────────────────────────────────────────────────────────────────────────

def occupy(g: 'GameState', x: int) -> None:
    """Recalculate which army occupies city x.

    Sets occupied(x) to the first army found at location x, or 0.

    Original: SUB occupy(x) -- lines 112-118
    """
    g.occupied[x] = 0                                                # L113
    for i in range(1, 41):                                           # L114
        if g.armyloc[i] == x:                                        # L115
            g.occupied[x] = i
            return  # GOTO holdup                                    # L115


# ─────────────────────────────────────────────────────────────────────────────
# load_cities(g)  -- extracted from CWSTRAT.BAS lines 93-102
#
# Not in cws_data.bm but logically belongs here. Reads cities.grd which
# defines the map topology: city positions, ownership, values, adjacency
# matrix, and fortifications.
# ─────────────────────────────────────────────────────────────────────────────

def load_cities(g: 'GameState') -> None:
    """Load city data from cities.grd.

    Original: CWSTRAT.BAS lines 93-102
    """
    g.city[0] = "NONE"                                               # L92
    g.vptotal = g.usadv + 200                                        # L94

    s = _QBStream(_data_path("cities.grd"))

    for i in range(1, 41):                                           # L95
        _ = s.read_int()        # city number (== i)
        g.cityx[i] = s.read_int()
        g.cityy[i] = s.read_int()
        g.city[i] = s.read_str()
        g.cityp[i] = s.read_int()
        g.cityv[i] = s.read_int()
        for j in range(1, 8):                                        # L98
            g.matrix[i][j] = s.read_int()
        g.fort[i] = s.read_int()

        g.cityo[i] = g.cityp[i]                                     # L96
        occupy(g, i)                                                 # L97
        if g.cityp[i] > 0:                                           # L99
            x = g.cityp[i]
            g.control[x] += 1
            g.victory[x] += g.cityv[i]
            g.cash[x] += g.cityv[i]                                  # L100
        g.vptotal += g.cityv[i]                                      # L101
