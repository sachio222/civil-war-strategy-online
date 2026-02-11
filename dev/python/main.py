"""main.py - CWS: Civil War Strategy (Python/Pygame Port)

Run:
    cd dev/python
    pip install pygame-ce
    python main.py

Controls:
    The game runs exactly as the original QB64 version:
    title screen → main menu → monthly turns → game end.

Debug mode (--debug):
    ESC     - Quit
    SPACE   - Redraw map
    F1      - Show module status
    T       - Trigger turn update
"""

import os
import sys
import pygame

# ── Imports from ported modules ──────────────────────────────────────────
from cws_globals import GameState
from cws_screen_pygame import PygameScreen, VGA


def main():
    """Launch the game."""
    debug = "--debug" in sys.argv

    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=2048)

    # ── Pixel-sharp rendering setup ──────────────────────────────────────
    # Internal render target: native 640x480 (all game drawing happens here)
    NATIVE_W, NATIVE_H = 640, 480

    # Pick a display scale: fit 3x into current monitor, fall back to 2x
    info = pygame.display.Info()
    scale = 3
    if info.current_w < NATIVE_W * 3 or info.current_h < NATIVE_H * 3 + 80:
        scale = 2
    display_w = NATIVE_W * scale
    display_h = NATIVE_H * scale

    display_surface = pygame.display.set_mode(
        (display_w, display_h), pygame.RESIZABLE)
    pygame.display.set_caption("CWS: Civil War Strategy")

    # Internal 640x480 surface — everything renders here, then gets
    # nearest-neighbor-scaled up to the display for pixel-sharp output
    render_surface = pygame.Surface((NATIVE_W, NATIVE_H))

    from cws_sound import init_sound
    init_sound()

    screen = PygameScreen(render_surface, display=display_surface)
    g = GameState(screen=screen)

    if debug:
        _run_debug(g)
    else:
        _run_game(g)

    pygame.quit()
    print("Goodbye.")


# ═══════════════════════════════════════════════════════════════════════════
#  Normal game mode — runs the full CWSTRAT.BAS game loop
# ═══════════════════════════════════════════════════════════════════════════

def _run_game(g: GameState) -> None:
    """Run the full ported game."""
    from cws_main import game_loop

    print("Starting CWS: Civil War Strategy...")
    try:
        game_loop(g)
    except Exception as e:
        print(f"Game error: {e}")
        import traceback
        traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════════
#  Debug mode — map viewer with module status overlay
# ═══════════════════════════════════════════════════════════════════════════

# Module status tracking
MODULES = {
    "cws_globals":        ("GameState, Screen protocol", True),
    "cws_screen_pygame":  ("Pygame rendering backend", True),
    "cws_data":           ("File I/O, load/save, city data", True),
    "cws_ai":             ("AI decision logic (smarts)", True),
    "cws_ui":             ("Menus, topbar, flags, scribe", True),
    "cws_util":           ("Utilities: tick, bubble, animate, stax", True),
    "cws_misc":           ("Hall of fame, capitol, newcity", True),
    "cws_sound":          ("Sound (no-ops for now)", True),
    "cws_map":            ("Map, tupdate, icon, usa (full port)", True),
    "cws_combat":         ("Battle, capture, retreat, evaluate", True),
    "cws_army":           ("Army management", True),
    "cws_navy":           ("Naval operations", True),
    "cws_railroad":       ("Railroad movement", True),
    "cws_recruit":        ("Recruitment", True),
    "cws_flow":           ("Game flow, events, victory", True),
    "cws_report":         ("Reports", True),
    "cws_main":           ("Main game loop (CWSTRAT.BAS)", True),
}


def _show_status(g: GameState) -> None:
    """Show porting status overlay."""
    s = g.screen
    s.line(40, 60, 600, 420, 1, "BF")
    s.line(40, 60, 600, 420, 15, "B")

    s.color(14)
    s.locate(5, 15)
    s.print_text("CWS: Civil War Strategy - Python Port Status")
    s.locate(6, 15)
    s.print_text("=" * 46)

    row = 8
    ported = 0
    total = len(MODULES)
    for name, (desc, done) in MODULES.items():
        s.color(10 if done else 12)
        marker = "[OK]" if done else "[..]"
        s.locate(row, 8)
        s.print_text(f"{marker} {name:22s} {desc[:40]}")
        row += 1
        if done:
            ported += 1

    s.color(15)
    s.locate(row + 1, 15)
    s.print_text(f"Progress: {ported}/{total} modules ported")
    s.locate(row + 2, 15)
    s.print_text(f"Press any key to return to map...")
    s.update()


def _draw_game(g: GameState) -> None:
    """Draw the full game screen (debug mode)."""
    from cws_map import usa, showcity
    from cws_ui import topbar
    from cws_util import stax

    g.screen.cls()

    try:
        usa(g)
    except Exception as e:
        print(f"[map] usa() error: {e}")
        g.screen.line(1, 16, 527, 440, 10, "B")
        g.screen.line(2, 17, 526, 439, 2, "BF")
        showcity(g)

    try:
        topbar(g)
    except Exception as e:
        print(f"[ui] topbar() error: {e}")
        g.screen.color(14)
        g.screen.locate(1, 2)
        g.screen.print_text(
            f"CWS: Civil War Strategy  |  {g.month_names[g.month]} {g.year}")

    try:
        for k in range(1, 3):
            stax(g, k)
    except Exception as e:
        print(f"[util] stax() error: {e}")

    g.screen.color(13)
    g.screen.locate(28, 2)
    g.screen.print_text("ESC=Quit  SPACE=Redraw  F1=Status  T=TurnUpdate")

    g.screen.update()


def _run_debug(g: GameState) -> None:
    """Run in debug/map-viewer mode."""
    from cws_data import load_cities, filer
    from cws_map import tupdate

    print("Loading city data...")
    try:
        load_cities(g)
        print(f"  Loaded {sum(1 for i in range(1,41) if g.city[i])} cities")
    except Exception as e:
        print(f"  ERROR loading cities: {e}")
        print(
            f"  Make sure data files exist in: "
            f"{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))}")
        sys.exit(1)

    print("Loading initial game data...")
    try:
        filer(g, 1)
        print(f"  Side: {g.force[g.side] if g.side else '?'}")
        print(f"  Date: {g.month_names[g.month]} {g.year}")
        print(
            f"  Armies loaded: "
            f"{sum(1 for i in range(1,41) if g.armyloc[i] > 0)}")
    except Exception as e:
        print(f"  ERROR loading game data: {e}")
        import traceback
        traceback.print_exc()
        print("  Continuing with partial data...")

    if not g.force[1]:
        g.force[1] = "Confederate"
    if not g.force[2]:
        g.force[2] = "Union"
    if not g.month_names[1]:
        g.month_names = [""] + [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

    print("Drawing map...")
    _draw_game(g)
    print("Ready. ESC to quit, SPACE to redraw, F1 for status.")

    clock = pygame.time.Clock()
    running = True
    showing_status = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                # Window resized — redraw at new size
                g.screen.update()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_SPACE:
                    _draw_game(g)

                elif event.key == pygame.K_F1:
                    if not showing_status:
                        _show_status(g)
                        showing_status = True
                    else:
                        _draw_game(g)
                        showing_status = False

                elif event.key == pygame.K_t:
                    print("Running tupdate()...")
                    try:
                        tupdate(g)
                        _draw_game(g)
                    except Exception as e:
                        print(f"  tupdate error: {e}")
                        import traceback
                        traceback.print_exc()
                        _draw_game(g)

                elif showing_status:
                    _draw_game(g)
                    showing_status = False

        clock.tick(30)


if __name__ == "__main__":
    main()
