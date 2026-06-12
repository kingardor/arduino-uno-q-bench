# SPDX-License-Identifier: MPL-2.0
"""Physical-board animation engine — charismatic but crash-safe.

The matrix is monochrome blue; colour lives on the RGB LED. We animate the
matrix (continuous draws) ONLY during the short, contention-free "burst"
windows — boot (at startup) and done/error (after inference). The steady
states (idle, processing) draw a single frame on entry and never stream — so
there are no Bridge calls during the heavy thinking phase (that's what crashed
it before). A circuit breaker disables the Bridge after sustained failures.

Colours (RGB LED + intent):  boot=purple, idle=dim violet, processing=yellow,
done=green, error=red.
"""
import math
import threading
import time

import frames as F

try:
    from arduino.app_utils import Bridge
    _HAVE_BRIDGE = True
except Exception:  # pragma: no cover
    _HAVE_BRIDGE = False

_LED_DIR = "/dev/leds/builtin"
_LED_MAX = 140
_bridge_ok = True
_fails = 0


def _led(channel, value):
    try:
        with open(f"{_LED_DIR}/{channel}", "w") as fh:
            fh.write(str(max(0, min(_LED_MAX, int(value)))))
    except Exception:
        pass


def _rgb(r, g, b):
    _led("led1_r", r); _led("led1_g", g); _led("led1_b", b)
    _led("led2_r", r); _led("led2_g", g); _led("led2_b", b)


# --- burst programs: (elapsed_seconds) -> (frame, (r,g,b)) -------------------
def _prog_boot(t):
    k = 0.45 + 0.55 * abs(math.sin(t * 7))
    purple = (int(70 * k) + 30, int(8 * k), int(95 * k) + 40)
    return F.sparkle(), purple               # random LEDs flicker on


def _prog_done(t):
    on = (t * 4.0) % 1.0 < 0.55              # blink ~4x
    green = (0, 130, 30) if on else (0, 16, 6)
    return F.check(on), green


def _prog_error(t):
    on = (t * 5.0) % 1.0 < 0.5
    red = (130, 0, 0) if on else (16, 0, 0)
    return F.error_glyph(on), red


_BURST = {"boot": (2.6, _prog_boot), "done": (1.7, _prog_done), "error": (1.3, _prog_error)}

_IDLE_FRAME = F.idle_frame()
_MTX_HZ = 4.0   # matrix refresh during processing (low enough to stay crash-safe)


class Animator:
    FPS = 15.0  # smooth bursts; steady states draw only on change

    def __init__(self, logger=None):
        self.logger = logger
        self._state = "boot"
        self._entered = time.time()
        self._drawn = None
        self._last_mtx = 0.0
        self._lock = threading.Lock()
        threading.Thread(target=self._loop, daemon=True).start()

    def set_state(self, state):
        with self._lock:
            if state != self._state:
                self._state = state
                self._entered = time.time()
                self._drawn = None

    def flash_done(self):
        self.set_state("done")

    def flash_error(self):
        self.set_state("error")

    # -- internals ----------------------------------------------------------
    def _draw(self, buf):
        global _bridge_ok, _fails
        if not (_HAVE_BRIDGE and _bridge_ok):
            return
        try:
            Bridge.call("draw", bytes(buf))
            _fails = 0
        except Exception as e:
            _fails += 1
            if _fails >= 8:           # tolerate transient startup hiccups
                _bridge_ok = False
                if self.logger:
                    self.logger.warning(f"matrix Bridge disabled after errors: {e}")

    def _loop(self):
        while True:
            with self._lock:
                state, entered = self._state, self._entered
            now = time.time()
            t = now - entered

            if state in _BURST:
                # boot/done/error: full animation (safe window — no inference)
                dur, prog = _BURST[state]
                frame, rgb = prog(t)
                self._draw(frame)
                _rgb(*rgb)
                self._drawn = None
                if t >= dur:
                    self.set_state("idle")

            elif state == "processing":
                # LED pulses yellow continuously (sysfs — safe); matrix shows
                # explosive centre->outward bursts at a low, crash-safe rate.
                k = 0.30 + 0.70 * abs(math.sin(t * 3.2))
                _rgb(int(150 * k), int(110 * k), 0)
                if now - self._last_mtx >= 1.0 / _MTX_HZ:
                    self._draw(F.explode((t * 1.25) % 1.0))
                    self._last_mtx = now
                self._drawn = None

            elif state == "detecting":
                # object detection: cyan radar sweep on the matrix + cyan LED
                k = 0.4 + 0.6 * abs(math.sin(t * 4))
                _rgb(0, int(120 * k), int(150 * k))
                if now - self._last_mtx >= 1.0 / _MTX_HZ:
                    self._draw(F.scan(int(t * 8)))
                    self._last_mtx = now
                self._drawn = None

            else:
                # idle: static blue glyph (drawn once) + gentle violet LED breathe
                if state != self._drawn:
                    self._draw(_IDLE_FRAME)
                    self._drawn = state
                k = 0.5 + 0.5 * math.sin(t * 1.4)
                _rgb(int(10 + 22 * k), 0, int(16 + 34 * k))

            time.sleep(1.0 / self.FPS)
