# SPDX-License-Identifier: MPL-2.0
"""8x13 monochrome-blue LED matrix frame generators (values 0..7, row-major).

The matrix is blue-only; colour (purple/yellow/green) lives on the RGB LED and
the browser. Here we shape the *motion* in blue. Each function returns a flat
list of 104 ints (8 rows x 13 cols, row-major).
"""
import math
import random

H, W = 8, 13
N = H * W
CX, CY = 6.0, 3.5          # geometric centre
_XS = 1.6                   # x-scale so distances look round on a 13x8 grid


def blank():
    return [0] * N


def _set(buf, y, x, v):
    if 0 <= y < H and 0 <= x < W:
        i = y * W + x
        v = max(0, min(7, int(round(v))))
        if v > buf[i]:
            buf[i] = v


def _dist(x, y):
    return math.hypot((x - CX) / _XS, y - CY)


def radiate(p):
    """Expanding ring from the centre to the edges; p in 0..1 (boot motion)."""
    buf = blank()
    maxr = 6.0
    r = p * maxr
    for y in range(H):
        for x in range(W):
            e = r - _dist(x, y)
            if -1.0 < e < 1.4:
                _set(buf, y, x, 7 - abs(e) * 4.5)
    _set(buf, 3, 6, max(2, 7 - r * 1.5)); _set(buf, 4, 6, max(2, 7 - r * 1.5))
    return buf


def sparkle():
    """Random activation of a random number of LEDs (boot twinkle)."""
    buf = blank()
    n = random.randint(12, 48)
    for _ in range(n):
        buf[random.randrange(N)] = random.randint(2, 7)
    return buf


def explode(p):
    """Explosive expanding burst from the centre outward; p in 0..1."""
    buf = blank()
    r = p * 6.5
    for y in range(H):
        for x in range(W):
            d = _dist(x, y)
            e = r - d
            if -0.6 < e < 1.6:                 # bright leading shockwave
                _set(buf, y, x, 7 - abs(e) * 3.5)
            elif 0 <= d < r:                   # filling interior, fading outward
                _set(buf, y, x, max(0, 3 - (r - d) * 1.3))
    return buf


def scan(i):
    """Rotating radar sweep with a fading trail (object-detection 'scanning')."""
    buf = blank()
    theta = (i * 0.45) % (2 * math.pi)
    for y in range(H):
        for x in range(W):
            d = _dist(x, y)
            if d > 6.6:
                continue
            ang = math.atan2(y - CY, (x - CX) / _XS) % (2 * math.pi)
            da = (theta - ang) % (2 * math.pi)        # angle behind the sweep
            if da < 1.1:
                _set(buf, y, x, 7 * (1 - da / 1.1) * min(1.0, d / 2.0))
    _set(buf, 3, 6, 4); _set(buf, 4, 6, 4)            # bright hub
    return buf


def busy(level=1.0):
    """'Thinking' glyph; level (0..1) scales brightness for a gentle pulse."""
    buf = blank()
    level = max(0.0, min(1.0, level))
    for y in range(H):
        for x in range(W):
            d = _dist(x, y)
            if d < 2.4:
                _set(buf, y, x, (6 if d < 1.2 else 3) * level)
    return buf


def idle_frame():
    """Calm centred diamond (static)."""
    buf = blank()
    _set(buf, 3, 6, 5); _set(buf, 4, 6, 5)
    for y, x in ((3, 5), (3, 7), (4, 5), (4, 7), (2, 6), (5, 6)):
        _set(buf, y, x, 2)
    return buf


def check(on=True):
    """Checkmark glyph (on) or blank (off) — used for the done blink."""
    buf = blank()
    if on:
        for y, x in ((4, 3), (5, 4), (6, 5), (5, 6), (4, 7), (3, 8), (2, 9), (1, 10)):
            _set(buf, y, x, 7)
        for y, x in ((4, 4), (3, 9)):
            _set(buf, y, x, 3)
    return buf


def error_glyph(on=True):
    buf = blank()
    if on:
        for d in range(H):
            _set(buf, d, 3 + d, 7)
            _set(buf, d, 9 - d, 7)
    return buf
