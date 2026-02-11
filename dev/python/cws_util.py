"""cws_util.py - Utility functions.
Direct port of cws_util.bm.

Contains:
    starfin(g, who) -> (star, fin)
    tick(g, seconds)
    bubble(g, size)
    bub2(g, limit)
    animate(g, index, flag)
    normal(xbar, vary) -> result
    stax(g, who)
"""

import math
import random
import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cws_globals import GameState


def starfin(g: 'GameState', who: int) -> tuple:
    """Return (star, fin) index range for a side's armies.

    Original: SUB starfin(star, fin, who)
        star = 1: fin = 20: IF who = 2 THEN star = 21: fin = 40
    """
    if who == 2:
        return (21, 40)
    return (1, 20)


def tick(g: 'GameState', seconds: float) -> None:
    """Delay for `seconds`, processing pygame events to stay responsive.

    Original: SUB TICK(sec!)
        start! = TIMER
        DO WHILE TIMER - start! < sec! AND INKEY$ = "": LOOP
    """
    if seconds <= 0:
        return
    g.screen.update()
    ms = int(seconds * 1000)
    start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start < ms:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                g.screen.update()
            if event.type == pygame.KEYDOWN:
                return  # any key press skips delay
        pygame.time.wait(16)  # ~60fps


def bubble(g: 'GameState', limit: int) -> None:
    """Bubble sort mtx$[1..limit] and array[1..limit] together.

    Original: SUB bubble(limit)
    Sorts mtx$ alphabetically, keeping array in sync.
    """
    swapped = True
    while swapped:
        swapped = False
        for i in range(1, limit):
            if g.mtx[i] > g.mtx[i + 1]:
                g.mtx[i], g.mtx[i + 1] = g.mtx[i + 1], g.mtx[i]
                g.array[i], g.array[i + 1] = g.array[i + 1], g.array[i]
                swapped = True


def bub2(g: 'GameState', limit: int) -> None:
    """Bubble sort brray[1..limit] numerically.

    Original: SUB bub2(limit)
    """
    swapped = True
    while swapped:
        swapped = False
        for i in range(1, limit):
            if g.brray[i] > g.brray[i + 1]:
                g.brray[i], g.brray[i + 1] = g.brray[i + 1], g.brray[i]
                swapped = True


def animate(g: 'GameState', index: int, flag: int) -> None:
    """Animate army movement between cities.

    Original: SUB animate(index, flag)
    Saves army icon, interpolates position from→to in 7 frames,
    drawing/erasing the icon at each step.
    """
    from cws_army import placearmy
    from cws_data import occupy

    s = g.screen
    from_ = g.armyloc[index]                                # L2
    to2 = g.armymove[index]
    g.armyloc[index] = 0
    x = g.cityx[from_] - 12                                # L3-4
    y = g.cityy[from_] - 11

    occupy(g, from_)                                        # L8
    if g.occupied[from_] > 0:
        placearmy(g, g.occupied[from_])

    if flag == 0:                                           # L10: IF flag > 0 GOTO already
        g._anima = s.get_image(x - 9, y - 7, x + 9, y + 6)  # L11
        if g.occupied[from_] == 0:                          # L12
            s.line(x - 9, y - 8, x + 10, y + 8, 2, "BF")
    # already:                                               L13

    anima = getattr(g, '_anima', None)
    if anima is None:
        g.armyloc[index] = from_
        return

    fx = g.cityx[from_]
    fy = g.cityy[from_]
    tx = g.cityx[to2]
    ty = g.cityy[to2]

    for i in range(2, 9):                                   # L15: FOR i = 2 TO 8
        x1 = int(0.1 * (i * tx + (10 - i) * fx))          # L16
        y1 = int(0.1 * (i * ty + (10 - i) * fy))          # L17
        image = s.get_image(x1 - 10, y1 - 10, x1 + 9, y1 + 9)  # L18
        s.put_image(x1 - 10, y1 - 10, anima)               # L19
        delay = 0.1 if g.turbo > 1 else 0.02               # L20
        tick(g, delay)
        if g.noise > 0:                                     # L21
            from cws_sound import qb_sound
            qb_sound(200, 0.1)
            qb_sound(50, 0.1)
        s.put_image(x1 - 10, y1 - 10, image)               # L22

    g.armyloc[index] = from_                                # L24


def normal(xbar: int, vary: int) -> int:
    """Generate normal-distributed random value.

    Original: SUB normal(xbar, vary, result)
    Uses sum of 12 uniforms approximation.
    """
    pct = sum(random.random() for _ in range(12)) - 5.5
    return int(xbar + pct * math.sqrt(vary))


def stax(g: 'GameState', who: int) -> None:
    """Draw small circle indicators for stacked (non-occupying) armies.

    Original: SUB stax(who)
    """
    star, fin = starfin(g, who)
    for i in range(star, fin + 1):
        if g.armysize[i] > 0 and g.occupied[g.armyloc[i]] != i:
            target = g.armyloc[i]
            if target > 0:
                x = g.cityx[target] - 12
                y = g.cityy[target] - 12
                g.screen.circle(x, y, 3, 14)
