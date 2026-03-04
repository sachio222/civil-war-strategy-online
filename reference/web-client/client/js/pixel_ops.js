/**
 * pixel_ops.js -- Performance-critical pixel manipulation for CWS.
 *
 * Provides snapToVGA() and floodFill() on window.CWSPixelOps.
 * Called from Python via js_bridge.py.
 */

(function () {
  "use strict";

  // VGA 16-color palette as [R, G, B]
  var VGA = [
    [0x00, 0x00, 0x00], // 0  Black
    [0x00, 0x00, 0xaa], // 1  Blue
    [0x00, 0xaa, 0x00], // 2  Green
    [0x00, 0xaa, 0xaa], // 3  Cyan
    [0xaa, 0x00, 0x00], // 4  Red
    [0xaa, 0x00, 0xaa], // 5  Magenta
    [0xaa, 0x55, 0x00], // 6  Brown
    [0xaa, 0xaa, 0xaa], // 7  Light Gray
    [0x55, 0x55, 0x55], // 8  Dark Gray
    [0x55, 0x55, 0xff], // 9  Light Blue
    [0x55, 0xff, 0x55], // 10 Light Green
    [0x55, 0xff, 0xff], // 11 Light Cyan
    [0xff, 0x55, 0x55], // 12 Light Red
    [0xff, 0x55, 0xff], // 13 Light Magenta
    [0xff, 0xff, 0x55], // 14 Yellow
    [0xff, 0xff, 0xff], // 15 White
  ];

  /**
   * Find the nearest VGA palette index for an RGB color.
   */
  function nearestVGA(r, g, b) {
    var best = 0;
    var bestDist = Infinity;
    for (var i = 0; i < 16; i++) {
      var dr = r - VGA[i][0];
      var dg = g - VGA[i][1];
      var db = b - VGA[i][2];
      var d = dr * dr + dg * dg + db * db;
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    }
    return best;
  }

  /**
   * snapToVGA(ctx)
   * Read all pixels, snap each to the nearest VGA palette color.
   * Skips fully transparent pixels.
   */
  function snapToVGA(ctx) {
    var canvas = ctx.canvas;
    var w = canvas.width;
    var h = canvas.height;
    var imageData = ctx.getImageData(0, 0, w, h);
    var data = imageData.data;

    for (var i = 0; i < data.length; i += 4) {
      if (data[i + 3] === 0) continue; // skip transparent
      var idx = nearestVGA(data[i], data[i + 1], data[i + 2]);
      data[i] = VGA[idx][0];
      data[i + 1] = VGA[idx][1];
      data[i + 2] = VGA[idx][2];
      data[i + 3] = 255;
    }

    ctx.putImageData(imageData, 0, 0);
  }

  /**
   * floodFill(ctx, seedX, seedY, fillColorIdx, borderColorIdx)
   * QBasic-style PAINT: fill from seed with fillColorIdx, stopping at borderColorIdx.
   * Uses scanline algorithm for performance.
   */
  function floodFill(ctx, seedX, seedY, fillColorIdx, borderColorIdx) {
    var canvas = ctx.canvas;
    var w = canvas.width;
    var h = canvas.height;
    seedX = Math.round(seedX);
    seedY = Math.round(seedY);

    if (seedX < 0 || seedX >= w || seedY < 0 || seedY >= h) return;

    var imageData = ctx.getImageData(0, 0, w, h);
    var data = imageData.data;

    var fillR = VGA[fillColorIdx][0];
    var fillG = VGA[fillColorIdx][1];
    var fillB = VGA[fillColorIdx][2];

    var borderR = VGA[borderColorIdx][0];
    var borderG = VGA[borderColorIdx][1];
    var borderB = VGA[borderColorIdx][2];

    // Check if a pixel matches the border color (within small tolerance)
    function isBorder(offset) {
      var dr = data[offset] - borderR;
      var dg = data[offset + 1] - borderG;
      var db = data[offset + 2] - borderB;
      return dr * dr + dg * dg + db * db < 400;
    }

    // Check if a pixel is already the fill color
    function isFilled(offset) {
      return (
        data[offset] === fillR &&
        data[offset + 1] === fillG &&
        data[offset + 2] === fillB
      );
    }

    // Check seed point
    var seedOffset = (seedY * w + seedX) * 4;
    if (isBorder(seedOffset) || isFilled(seedOffset)) return;

    // Scanline flood fill
    var stack = [[seedX, seedY]];

    while (stack.length > 0) {
      var point = stack.pop();
      var px = point[0];
      var py = point[1];

      var offset = (py * w + px) * 4;
      if (isBorder(offset) || isFilled(offset)) continue;

      // Scan left
      var left = px;
      while (left > 0) {
        var lo = (py * w + (left - 1)) * 4;
        if (isBorder(lo) || isFilled(lo)) break;
        left--;
      }

      // Scan right
      var right = px;
      while (right < w - 1) {
        var ro = (py * w + (right + 1)) * 4;
        if (isBorder(ro) || isFilled(ro)) break;
        right++;
      }

      // Fill the scanline
      for (var x = left; x <= right; x++) {
        var fo = (py * w + x) * 4;
        data[fo] = fillR;
        data[fo + 1] = fillG;
        data[fo + 2] = fillB;
        data[fo + 3] = 255;
      }

      // Push spans above and below
      for (var x = left; x <= right; x++) {
        if (py > 0) {
          var ao = ((py - 1) * w + x) * 4;
          if (!isBorder(ao) && !isFilled(ao)) {
            stack.push([x, py - 1]);
            // Skip to end of this run above to avoid duplicate pushes
            while (x < right) {
              var nao = ((py - 1) * w + (x + 1)) * 4;
              if (isBorder(nao) || isFilled(nao)) break;
              x++;
            }
          }
        }
      }
      for (var x = left; x <= right; x++) {
        if (py < h - 1) {
          var bo = ((py + 1) * w + x) * 4;
          if (!isBorder(bo) && !isFilled(bo)) {
            stack.push([x, py + 1]);
            while (x < right) {
              var nbo = ((py + 1) * w + (x + 1)) * 4;
              if (isBorder(nbo) || isFilled(nbo)) break;
              x++;
            }
          }
        }
      }
    }

    ctx.putImageData(imageData, 0, 0);
  }

  window.CWSPixelOps = {
    snapToVGA: snapToVGA,
    floodFill: floodFill,
  };
})();
