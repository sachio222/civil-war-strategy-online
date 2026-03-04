"""web_main.py — Entry point for the CWS web client.

Injects web module replacements into sys.modules before any game imports,
then starts the game loop. This runs inside a Pyodide Web Worker.
"""

import sys


def run():
    """Bootstrap and run the game."""
    print("[web_main] Starting CWS web client...")

    # ── 1. The pygame shim is already importable (it's in /game/pygame/) ──
    import pygame
    print(f"[web_main] pygame shim loaded: {pygame}")

    # ── 2. Set up the SharedArrayBuffer for keyboard input ────────────────
    import js
    from pygame.time_mod import _setup as _time_setup

    # worker.js sets self.keyBuffer before running Python.
    # In Pyodide's Web Worker, `js` module exposes the worker global scope.
    key_buffer = None
    try:
        key_buffer = js.keyBuffer
    except AttributeError:
        try:
            key_buffer = js.self.keyBuffer
        except Exception:
            pass

    if key_buffer is not None:
        _time_setup(key_buffer)
        print("[web_main] Keyboard SharedArrayBuffer connected")
    else:
        print("[web_main] WARNING: No SharedArrayBuffer — keyboard won't work")

    # ── 3. Inject web module replacements into sys.modules ────────────────
    import web_paths
    sys.modules['cws_paths'] = web_paths
    print("[web_main] Injected web_paths as cws_paths")

    import web_sound
    sys.modules['cws_sound'] = web_sound
    print("[web_main] Injected web_sound as cws_sound")

    import web_sprite
    sys.modules['vga_sprite'] = web_sprite
    print("[web_main] Injected web_sprite as vga_sprite")

    # cws_screen_pygame is already named correctly — our web version
    # lives at /game/cws_screen_pygame.py and will be imported as-is.

    # ── 4. Initialize sound ──────────────────────────────────────────────
    web_sound.init_sound()

    # ── 5. Create the screen and game state ──────────────────────────────
    from cws_screen_pygame import PygameScreen
    from cws_globals import GameState

    screen = PygameScreen()
    g = GameState(screen=screen)
    print("[web_main] GameState created")

    # ── 6. Show a loading screen ─────────────────────────────────────────
    s = g.screen
    s.cls()
    s.color(3)
    s.locate(14, 25)
    s.print_text("Loading CWS: Civil War Strategy...")
    s.color(8)
    s.locate(16, 28)
    s.print_text("Loading sprites...")
    s.update()

    # ── 7. Load sprites ──────────────────────────────────────────────────
    web_sprite.load_all_sprites(g)

    # ── 8. Run the game ──────────────────────────────────────────────────
    s.cls()
    s.color(3)
    s.locate(14, 28)
    s.print_text("Starting game...")
    s.update()

    print("[web_main] Launching game_loop...")
    from cws_main import game_loop

    try:
        game_loop(g)
    except Exception as e:
        print(f"[web_main] Game error: {e}")
        import traceback
        traceback.print_exc()
        # Show error on screen
        s.cls()
        s.color(12)
        s.locate(10, 5)
        s.print_text("ERROR: Game crashed")
        s.color(7)
        s.locate(12, 5)
        s.print_text(str(e)[:70])
        s.update()

    print("[web_main] Game ended.")
