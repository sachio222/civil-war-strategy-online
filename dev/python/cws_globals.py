"""cws_globals.py - Shared Game State
Direct port of cws_globals.bi (QB64)

Every COMMON SHARED variable becomes a field on GameState.
Every DIM SHARED array becomes a list (1-indexed, index 0 unused).
QB64's DEFINT A-Z means most vars are int; those with ! suffix are float.

This is the ONLY place game state lives. Every module function receives
a GameState reference -- no Python globals anywhere.
"""

from dataclasses import dataclass, field
from typing import List, Protocol


# ── VGA 16-color palette (SCREEN 12) ─────────────────────────────────────────
VGA_PALETTE = {
    0:  (0x00, 0x00, 0x00),  # black
    1:  (0x00, 0x00, 0xAA),  # blue
    2:  (0x00, 0xAA, 0x00),  # green
    3:  (0x00, 0xAA, 0xAA),  # cyan
    4:  (0xAA, 0x00, 0x00),  # red
    5:  (0xAA, 0x00, 0xAA),  # magenta
    6:  (0xAA, 0x55, 0x00),  # brown
    7:  (0xAA, 0xAA, 0xAA),  # light gray
    8:  (0x55, 0x55, 0x55),  # dark gray
    9:  (0x55, 0x55, 0xFF),  # light blue
    10: (0x55, 0xFF, 0x55),  # light green
    11: (0x55, 0xFF, 0xFF),  # light cyan
    12: (0xFF, 0x55, 0x55),  # light red
    13: (0xFF, 0x55, 0xFF),  # light magenta
    14: (0xFF, 0xFF, 0x55),  # yellow
    15: (0xFF, 0xFF, 0xFF),  # white
}


class Screen(Protocol):
    """Abstraction over the rendering target.

    Pygame implementation: renders to a pygame.Surface.
    Web implementation: sends draw commands over WebSocket to an HTML5 Canvas.
    Both produce pixel-identical output.
    """

    def color(self, c: int) -> None: ...
    def locate(self, row: int, col: int) -> None: ...
    def print_text(self, text: str) -> None: ...
    def line(self, x1: int, y1: int, x2: int, y2: int, c: int,
             style: str = "") -> None: ...
    def put_image(self, x: int, y: int, sprite: list) -> None: ...
    def get_image(self, x1: int, y1: int, x2: int, y2: int) -> list: ...
    def cls(self) -> None: ...


def _arr(size: int, default=0) -> list:
    """Create a 1-indexed array (index 0 is padding)."""
    return [default] * (size + 1)


def _arr2d(rows: int, cols: int, default=0) -> list:
    """Create a 2D 1-indexed array: arr[row][col]."""
    return [[default] * (cols + 1) for _ in range(rows + 1)]


@dataclass
class GameState:
    """All COMMON SHARED and DIM SHARED variables from cws_globals.bi.

    QB64 originals shown in comments. Arrays are 1-indexed (index 0 unused).
    """

    # ── Screen / rendering ────────────────────────────────────────────────
    screen: Screen = None  # injected at startup (Pygame or Web canvas)

    # ── Scalar state ──────────────────────────────────────────────────────
    # COMMON SHARED choose%, tlx%, tly%, size%, wtype%, colour%, hilite%
    choose: int = 0
    tlx: int = 0
    tly: int = 0
    size: int = 0
    wtype: int = 0
    colour: int = 0
    hilite: int = 0

    # COMMON SHARED filel, player, side, month, year, mflag
    filel: int = 1
    player: int = 1
    side: int = 1
    month: int = 0
    year: int = 1861
    mflag: int = 0

    # COMMON SHARED bold, aggress!, turbo!, graf, noise, difficult, usadv, bw
    bold: int = 0
    aggress: float = 0.0     # aggress! in QB64
    turbo: float = 2.0       # turbo! in QB64
    graf: int = 0
    noise: int = 0
    difficult: int = 3
    usadv: int = 0
    bw: int = 0

    # COMMON SHARED vptotal, ATKFAC, DEFAC, TCR, rflag, nflag
    vptotal: int = 0
    atkfac: int = 0
    defac: int = 0
    tcr: int = 0
    rflag: int = 0
    nflag: int = 0

    # COMMON SHARED pcode, history, thrill, commerce, raider, grudge
    pcode: int = 0
    history: int = 0
    thrill: int = 0
    commerce: int = 0
    raider: int = 0
    grudge: int = 0

    # COMMON SHARED jancam, randbal, realism, emancipate
    jancam: int = 0
    randbal: int = 7
    realism: int = 0
    emancipate: int = 0

    # ── Arrays (1-indexed) ────────────────────────────────────────────────
    # DIM SHARED cityx(40), cityy(40), cityv(40), cityp(40), city$(40)
    cityx:    List[int] = field(default_factory=lambda: _arr(40))
    cityy:    List[int] = field(default_factory=lambda: _arr(40))
    cityv:    List[int] = field(default_factory=lambda: _arr(40))
    cityp:    List[int] = field(default_factory=lambda: _arr(40))
    city:     List[str] = field(default_factory=lambda: _arr(40, ""))

    # DIM SHARED lname$(40), rcity(5)
    lname:    List[str] = field(default_factory=lambda: _arr(40, ""))
    rcity:    List[int] = field(default_factory=lambda: _arr(5))

    # DIM SHARED cash(2), control(2), income(2)
    cash:     List[int] = field(default_factory=lambda: _arr(2))
    control:  List[int] = field(default_factory=lambda: _arr(2))
    income:   List[int] = field(default_factory=lambda: _arr(2))

    # DIM SHARED matrix(40, 7)  -- adjacency: matrix[city][1..6] = neighbor cities
    matrix:   list = field(default_factory=lambda: _arr2d(40, 7))

    # DIM SHARED anima(300), image(300), rating(40)
    anima:    List[int] = field(default_factory=lambda: _arr(300))
    image:    List[int] = field(default_factory=lambda: _arr(300))
    rating:   List[int] = field(default_factory=lambda: _arr(40))

    # DIM SHARED force$(2)
    force:    List[str] = field(default_factory=lambda: ["", "Confederate", "Union"])

    # DIM SHARED armyloc(40) .. armymove(40), occupied(40), fort(40)
    armyloc:  List[int] = field(default_factory=lambda: _arr(40))
    armyname: List[str] = field(default_factory=lambda: _arr(40, ""))
    armysize: List[int] = field(default_factory=lambda: _arr(40))
    armylead: List[int] = field(default_factory=lambda: _arr(40))
    armyexper:List[int] = field(default_factory=lambda: _arr(40))
    supply:   List[int] = field(default_factory=lambda: _arr(40))
    armymove: List[int] = field(default_factory=lambda: _arr(40))
    occupied: List[int] = field(default_factory=lambda: _arr(40))
    fort:     List[int] = field(default_factory=lambda: _arr(40))

    # DIM SHARED navyloc(2), navysize(2), navymove(2)
    navyloc:  List[int] = field(default_factory=lambda: _arr(2))
    navysize: List[int] = field(default_factory=lambda: _arr(2))
    navymove: List[int] = field(default_factory=lambda: _arr(2))

    # DIM SHARED victory(2), capcity(2), rr(2), tracks(2), train(2), rrfrom(2)
    victory:  List[int] = field(default_factory=lambda: _arr(2))
    capcity:  List[int] = field(default_factory=lambda: _arr(2))
    rr:       List[int] = field(default_factory=lambda: _arr(2))
    tracks:   List[int] = field(default_factory=lambda: _arr(2))
    train:    List[int] = field(default_factory=lambda: _arr(2))
    rrfrom:   List[int] = field(default_factory=lambda: _arr(2))

    # DIM SHARED vicflag(6), price(3)
    vicflag:  List[int] = field(default_factory=lambda: _arr(6))
    price:    List[int] = field(default_factory=lambda: _arr(3))

    # DIM SHARED array(40), brray(40), cityo(40), batwon(2), casualty&(2)
    array:    List[int] = field(default_factory=lambda: _arr(40))
    brray:    List[int] = field(default_factory=lambda: _arr(40))
    cityo:    List[int] = field(default_factory=lambda: _arr(40))
    batwon:   List[int] = field(default_factory=lambda: _arr(2))
    casualty: List[int] = field(default_factory=lambda: _arr(2))  # casualty& (LONG)

    # DIM SHARED month$(12), mtx$(21), font$(26), fleet$(2)
    month_names: List[str] = field(default_factory=lambda: _arr(12, ""))
    mtx:      List[str] = field(default_factory=lambda: _arr(21, ""))
    font:     List[str] = field(default_factory=lambda: _arr(26, ""))
    fleet:    List[str] = field(default_factory=lambda: ["", "", ""])

    # DIM SHARED starx(8), stary(8)
    starx:    List[int] = field(default_factory=lambda: _arr(8))
    stary:    List[int] = field(default_factory=lambda: _arr(8))

    # DIM SHARED mtn(1 TO 1564), graphic(1 TO 1564), graft(1 TO 1564)
    mtn:      List[int] = field(default_factory=lambda: [0] * 1565)
    graphic:  List[int] = field(default_factory=lambda: [0] * 1565)
    graft:    List[int] = field(default_factory=lambda: [0] * 1565)

    # DIM SHARED Ncap(60)
    ncap:     List[int] = field(default_factory=lambda: _arr(60))
