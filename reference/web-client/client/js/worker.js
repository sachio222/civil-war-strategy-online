/**
 * worker.js — Web Worker that runs the CWS game via Pyodide.
 *
 * Loads Pyodide, mounts game Python files into the virtual filesystem,
 * pre-decodes PNG sprites, and runs web_main.py which calls game_loop(g).
 *
 * Communication with main thread:
 *   - SharedArrayBuffer for keyboard input (Atomics.wait to block)
 *   - postMessage for framebuffer and sound
 */

/* global importScripts */

// Exposed as worker globals for Python access via js.self
self.keyBuffer = null; // Int32Array over SharedArrayBuffer

let pyodide = null;

// ── Handle messages from main thread ──────────────────────────────────────
// After Python starts, the worker is blocked in Python. Messages are only
// processed during Atomics.wait timeouts in time_mod.py. So we only need
// to handle the init message here.
self.onmessage = async function (e) {
  const msg = e.data;
  if (msg.type === "init") {
    self.keyBuffer = new Int32Array(msg.keyBuffer);
    await bootPyodide();
  }
};

// ── Decode a PNG image using OffscreenCanvas (available in workers) ────────
async function decodePNG(url) {
  const resp = await fetch(url);
  if (!resp.ok) return null;
  const blob = await resp.blob();
  const bmp = await createImageBitmap(blob);
  const canvas = new OffscreenCanvas(bmp.width, bmp.height);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(bmp, 0, 0);
  const imgData = ctx.getImageData(0, 0, bmp.width, bmp.height);
  bmp.close();
  return {
    width: imgData.width,
    height: imgData.height,
    pixels: new Uint8Array(imgData.data.buffer),
  };
}

// ── Boot Pyodide and run the game ─────────────────────────────────────────
async function bootPyodide() {
  self.postMessage({ type: "status", text: "Loading Pyodide..." });

  importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.4/full/pyodide.js");
  pyodide = await loadPyodide();

  self.postMessage({ type: "status", text: "Loading game files..." });

  const FS = pyodide.FS;
  _mkdirp(FS, "/game");
  _mkdirp(FS, "/game/pygame");
  _mkdirp(FS, "/data");
  _mkdirp(FS, "/saves");
  _mkdirp(FS, "/sprites");

  // ── Fetch Python files (shim + desktop) in parallel ─────────────────────
  const shimFiles = [
    "py/pygame/__init__.py",
    "py/pygame/surface.py",
    "py/pygame/event.py",
    "py/pygame/time_mod.py",
    "py/pygame/mixer.py",
    "py/pygame/display.py",
    "py/pygame/draw.py",
    "py/pygame/transform.py",
    "py/pygame/font.py",
    "py/pygame/image.py",
    "py/web_main.py",
    "py/cws_screen_pygame.py",
    "py/web_paths.py",
    "py/web_sound.py",
    "py/web_sprite.py",
  ];

  const desktopFiles = [
    "cws_globals.py",
    "cws_main.py",
    "cws_map.py",
    "cws_combat.py",
    "cws_army.py",
    "cws_recruit.py",
    "cws_navy.py",
    "cws_railroad.py",
    "cws_ai.py",
    "cws_flow.py",
    "cws_ui.py",
    "cws_report.py",
    "cws_misc.py",
    "cws_util.py",
    "cws_data.py",
    "cws_online.py",
    "vga_font.py",
  ];

  const dataFiles = [
    "CWSLEAD.DAT",
    "CITIES.GRD",
    "CWS.INI",
    "HISCORE.CWS",
    "ALTLEAD.DAT",
    "ALTMAP.GRD",
    "ALTMAP.INI",
  ];

  const spriteFiles = [
    "mtn.png",
    "cwsicon.png",
    "face1.png",
    "face2.png",
    "face3.png",
    "face4.png",
    "face5.png",
    "fort0.png",
    "fort1.png",
    "fort2.png",
  ];

  // Launch all fetches in parallel
  const allPromises = [];

  // Shim files
  for (const path of shimFiles) {
    allPromises.push(
      fetch(path)
        .then((r) => (r.ok ? r.text() : null))
        .then((text) => {
          if (text !== null)
            FS.writeFile("/game/" + path.slice(3), text);
        })
        .catch((e) => console.error(`Shim ${path}:`, e))
    );
  }

  // Desktop files
  for (const name of desktopFiles) {
    allPromises.push(
      fetch("/desktop_py/" + name)
        .then((r) => (r.ok ? r.text() : null))
        .then((text) => {
          if (text !== null) FS.writeFile("/game/" + name, text);
        })
        .catch((e) => console.error(`Desktop ${name}:`, e))
    );
  }

  // Data files (binary)
  for (const name of dataFiles) {
    allPromises.push(
      fetch("/data_files/" + name)
        .then((r) => (r.ok ? r.arrayBuffer() : null))
        .then((buf) => {
          if (buf !== null)
            FS.writeFile("/data/" + name, new Uint8Array(buf));
        })
        .catch((e) => console.warn(`Data ${name}:`, e))
    );
  }

  // Sprite PNG files — decode to raw RGBA and store in /sprites/
  for (const name of spriteFiles) {
    allPromises.push(
      decodePNG("/assets/sprites/" + name)
        .then((info) => {
          if (info) {
            // Store as: /sprites/name.meta (4 bytes: width LE, height LE)
            //           /sprites/name.rgba (raw pixels)
            const meta = new Uint8Array(4);
            meta[0] = info.width & 0xff;
            meta[1] = (info.width >> 8) & 0xff;
            meta[2] = info.height & 0xff;
            meta[3] = (info.height >> 8) & 0xff;
            const baseName = name.replace(".png", "");
            FS.writeFile("/sprites/" + baseName + ".meta", meta);
            FS.writeFile("/sprites/" + baseName + ".rgba", info.pixels);
          }
        })
        .catch((e) => console.warn(`Sprite ${name}:`, e))
    );
  }

  await Promise.all(allPromises);

  self.postMessage({ type: "status", text: "Starting game..." });

  // ── Run the Python entry point ──────────────────────────────────────────
  try {
    pyodide.runPython(`
import sys
sys.path.insert(0, '/game')
import web_main
web_main.run()
`);
  } catch (err) {
    console.error("Python error:", err);
    self.postMessage({ type: "status", text: "Error: " + err.message });
  }
}

function _mkdirp(FS, path) {
  const parts = path.split("/").filter(Boolean);
  let cur = "";
  for (const p of parts) {
    cur += "/" + p;
    try {
      FS.mkdir(cur);
    } catch (e) {
      // already exists
    }
  }
}
