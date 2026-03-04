/**
 * main_thread.js — Main thread controller for CWS web client.
 *
 * Responsibilities:
 *   - Creates the Web Worker and passes SharedArrayBuffer for keyboard input
 *   - Renders framebuffer data from worker onto <canvas> via putImageData()
 *   - Captures keyboard events → writes to SharedArrayBuffer → Atomics.notify()
 *   - Plays sound commands received from worker (Web Audio API)
 *   - Decodes PNG sprite images on behalf of the worker
 */

(function () {
  "use strict";

  // ── Canvas setup ────────────────────────────────────────────────────────
  const canvas = document.getElementById("gameCanvas");
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  canvas.width = 640;
  canvas.height = 480;

  // Fill black initially
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, 640, 480);

  // Status text
  function showStatus(text) {
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, 640, 480);
    ctx.fillStyle = "#0aa";
    ctx.font = "16px monospace";
    ctx.fillText(text, 200, 240);
  }
  showStatus("Initializing...");

  // ── SharedArrayBuffer for keyboard input ────────────────────────────────
  // Layout: Int32Array[4]
  //   [0] = signal (worker waits on this; main thread sets to 1 + notifies)
  //   [1] = event type
  //   [2] = key code
  //   [3] = unicode char code
  const keyBufferSAB = new SharedArrayBuffer(4 * Int32Array.BYTES_PER_ELEMENT);
  const keyBuffer = new Int32Array(keyBufferSAB);

  // ── Web Audio for sound ─────────────────────────────────────────────────
  let audioCtx = null;

  function ensureAudioCtx() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioCtx;
  }

  function playTone(freq, durationMs) {
    if (freq <= 0 || durationMs <= 0) return;
    const ctx = ensureAudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "square";
    osc.frequency.value = freq;
    gain.gain.value = 0.15;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + durationMs / 1000);
  }

  // ── Create the worker ──────────────────────────────────────────────────
  const worker = new Worker("js/worker.js");

  worker.onmessage = function (e) {
    const msg = e.data;

    switch (msg.type) {
      case "status":
        showStatus(msg.text);
        break;

      case "frame": {
        // msg.buffer is an ArrayBuffer of 640*480*4 RGBA bytes
        const imageData = new ImageData(
          new Uint8ClampedArray(msg.buffer),
          640,
          480
        );
        ctx.putImageData(imageData, 0, 0);
        break;
      }

      case "sound":
        playTone(msg.freq, msg.duration);
        break;

      case "decode_sprite": {
        // Worker requests PNG decode — use an Image element on main thread
        const img = new Image();
        img.onload = function () {
          const offscreen = document.createElement("canvas");
          offscreen.width = img.width;
          offscreen.height = img.height;
          const octx = offscreen.getContext("2d");
          octx.drawImage(img, 0, 0);
          const imgData = octx.getImageData(0, 0, img.width, img.height);
          worker.postMessage(
            {
              type: "sprite_decoded",
              id: msg.id,
              width: img.width,
              height: img.height,
              pixels: imgData.data.buffer,
            },
            [imgData.data.buffer]
          );
        };
        img.onerror = function () {
          console.error("Failed to decode sprite:", msg.url);
          worker.postMessage({
            type: "sprite_decoded",
            id: msg.id,
            width: 0,
            height: 0,
            pixels: new ArrayBuffer(0),
          });
        };
        img.src = msg.url;
        break;
      }

      case "save_to_storage":
        // Persist save data to localStorage
        try {
          localStorage.setItem(
            "cws_save_" + msg.filename,
            msg.data
          );
        } catch (err) {
          console.warn("Failed to save to localStorage:", err);
        }
        break;

      case "load_from_storage": {
        // Load save data from localStorage
        const data = localStorage.getItem("cws_save_" + msg.filename);
        worker.postMessage({
          type: "storage_data",
          filename: msg.filename,
          data: data,
        });
        break;
      }
    }
  };

  worker.onerror = function (e) {
    console.error("Worker error:", e);
    showStatus("Worker error: " + e.message);
  };

  // ── Keyboard input → SharedArrayBuffer ─────────────────────────────────
  // Map browser key codes to pygame-compatible key codes
  const KEY_MAP = {
    Enter: 13,
    Escape: 27,
    ArrowUp: 273,
    ArrowDown: 274,
    ArrowLeft: 275,
    ArrowRight: 276,
    Home: 278,
    End: 279,
    PageUp: 280,
    PageDown: 281,
    Backspace: 8,
    " ": 32,
    F1: 282,
    F3: 284,
    F7: 288,
    F8: 289,
  };

  document.addEventListener("keydown", function (e) {
    // Prevent browser defaults for game keys
    if (
      [
        "ArrowUp",
        "ArrowDown",
        "ArrowLeft",
        "ArrowRight",
        "Backspace",
        " ",
        "F1",
        "F3",
        "F7",
        "F8",
      ].includes(e.key)
    ) {
      e.preventDefault();
    }

    let keyCode = KEY_MAP[e.key];
    let charCode = 0;

    if (keyCode === undefined) {
      // For single printable characters, use char code
      if (e.key.length === 1) {
        keyCode = e.key.charCodeAt(0);
        charCode = keyCode;
      } else {
        return; // Ignore unknown special keys
      }
    } else {
      // For special keys, set charCode from the mapping
      if (keyCode === 13) charCode = 13;
      else if (keyCode === 27) charCode = 27;
      else if (keyCode === 8) charCode = 8;
      else if (keyCode === 32) charCode = 32;
    }

    // Write event into SharedArrayBuffer
    Atomics.store(keyBuffer, 1, 258); // KEYDOWN
    Atomics.store(keyBuffer, 2, keyCode);
    Atomics.store(keyBuffer, 3, charCode);
    Atomics.store(keyBuffer, 0, 1); // signal
    Atomics.notify(keyBuffer, 0);

    // Resume AudioContext on first user interaction
    if (audioCtx && audioCtx.state === "suspended") {
      audioCtx.resume();
    }
  });

  // ── Start the worker ───────────────────────────────────────────────────
  worker.postMessage({
    type: "init",
    keyBuffer: keyBufferSAB,
  });

  // Also init audio on first click
  canvas.addEventListener(
    "click",
    function () {
      ensureAudioCtx();
      if (audioCtx.state === "suspended") audioCtx.resume();
    },
    { once: true }
  );
})();
