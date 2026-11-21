"""SELKARA -- a travel poster for a place that does not exist.

A single-file Python 3 program using only the standard library. It draws a
1024x1024 travel poster with a hand-built 5x7 bitmap font and a hand-written
PNG encoder, and writes it to /output/entry.png (or
$MAKEFUN_OUTPUT_DIR/entry.png). No network, no clock, no randomness: two runs
produce byte-identical output.

The poster: golden hour over Selkara, an island that is not on any map. A
ringed planet hangs in the dusk sky, a low sun melts into a mirror sea, and a
red-banded lighthouse on the headland throws its beam across the water toward
a lone sail. The place's name is set large across the top of the picture, as a
travel poster sets it.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024
HORIZON = 600

# ---------------------------------------------------------------- palette
INK = (22, 35, 63)          # deep indigo night sky, top
SKY_MID = (44, 82, 104)     # teal dusk
SKY_LOW = (214, 138, 74)    # warm amber above the horizon
GOLD = (247, 200, 115)      # low sun
SUN_CORE = (255, 233, 168)
CREAM = (245, 233, 208)     # poster type
SEA_TOP = (20, 80, 95)
SEA_BOT = (11, 43, 56)
CLIFF = (16, 34, 42)
ROCK = (26, 48, 55)
RED = (178, 58, 48)         # lighthouse bands
LAMP = (255, 214, 120)
PLANET = (232, 196, 138)
PLANET_RING = (240, 214, 160)
WHITE = (250, 248, 240)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def blend(self, x, y, c, a):
        """Blend colour c over the pixel at (x, y); a in 0..1."""
        if 0 <= x < self.w and 0 <= y < self.h and a > 0.0:
            if a >= 1.0:
                self.set(x, y, c)
                return
            i = self._idx(x, y)
            self.px[i] = int(self.px[i] * (1 - a) + c[0] * a)
            self.px[i + 1] = int(self.px[i + 1] * (1 - a) + c[1] * a)
            self.px[i + 2] = int(self.px[i + 2] * (1 - a) + c[2] * a)

    def fill_rect(self, x0, y0, x1, y1, c):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        for y in range(y0, y1):
            base = (y * self.w + x0) * 3
            for x in range(x0, x1):
                i = base + (x - x0) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def vgrad(self, y0, y1, c0, c1, dither=True):
        """Vertical gradient with a whisper of deterministic dither so the
        sky does not band."""
        span = max(1, y1 - y0)
        for y in range(y0, y1):
            t = (y - y0) / span
            r = int(c0[0] + (c1[0] - c0[0]) * t)
            g = int(c0[1] + (c1[1] - c0[1]) * t)
            b = int(c0[2] + (c1[2] - c0[2]) * t)
            base = (y * self.w) * 3
            for x in range(self.w):
                if dither:
                    n = ((x * 2654435761 + y * 40503) >> 13) & 3
                    n -= 1
                else:
                    n = 0
                i = base + x * 3
                self.px[i] = max(0, min(255, r + n))
                self.px[i + 1] = max(0, min(255, g + n))
                self.px[i + 2] = max(0, min(255, b + n))

    def disc(self, cx, cy, r, c, feather=0, alpha=1.0):
        """Filled disc; feather softens the edge over that many pixels."""
        r2 = r + feather
        x0 = int(cx - r2)
        x1 = int(cx + r2) + 1
        y0 = int(cy - r2)
        y1 = int(cy + r2) + 1
        for y in range(max(0, y0), min(self.h, y1)):
            dy = y - cy
            for x in range(max(0, x0), min(self.w, x1)):
                dx = x - cx
                d = math.sqrt(dx * dx + dy * dy)
                if d <= r:
                    a = alpha
                elif feather > 0 and d <= r2:
                    a = alpha * (1 - (d - r) / feather)
                else:
                    continue
                self.blend(x, y, c, a)

    def poly(self, pts, c, alpha=1.0):
        """Filled polygon, scanline rasterised."""
        if not pts:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys)))
        y1 = min(self.h - 1, int(max(ys)) + 1)
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for k in range(n):
                x0, y0p = pts[k]
                x1, y1p = pts[(k + 1) % n]
                if y0p == y1p:
                    continue
                if (y >= min(y0p, y1p)) and (y < max(y0p, y1p)):
                    t = (y - y0p) / (y1p - y0p)
                    xs.append(x0 + (x1 - x0) * t)
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = int(xs[k])
                xb = int(xs[k + 1])
                for x in range(max(0, xa), min(self.w, xb + 1)):
                    self.blend(x, y, c, alpha)

    def thick_line(self, x0, y0, x1, y1, w, c, alpha=1.0):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for s in range(steps + 1):
            t = s / steps
            self.disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, w / 2.0, c,
                      alpha=alpha)

    def ellipse_ring(self, cx, cy, rx, ry, tilt, thick, c, alpha=1.0):
        """A tilted ring, drawn as small discs along a rotated ellipse."""
        steps = 360
        ct = math.cos(tilt)
        st = math.sin(tilt)
        for s in range(steps):
            a = 2 * math.pi * s / steps
            ex = rx * math.cos(a)
            ey = ry * math.sin(a)
            x = cx + ex * ct - ey * st
            y = cy + ex * st + ey * ct
            self.disc(x, y, thick / 2.0, c, alpha=alpha)


# ---------------------------------------------------------------- 5x7 font
# Each glyph is 7 rows of 5 cells; '#' is ink, '.' is empty.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
}


def text_width(text, scale, spacing=1):
    return len(text) * (5 * scale + spacing * scale) - spacing * scale


def draw_text(cv, x, y, text, scale, c, shadow=None):
    """Draw text with its top-left at (x, y); scale multiplies the 5x7 cells.
    A shadow, if given, is drawn first, offset down-right."""
    if shadow is not None:
        draw_text(cv, x + scale // 2, y + scale // 2, text, scale, shadow)
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            for col in range(5):
                if glyph[row][col] == "1":
                    cv.fill_rect(cx + col * scale, y + row * scale,
                                 cx + (col + 1) * scale,
                                 y + (row + 1) * scale, c)
        cx += 6 * scale


# ---------------------------------------------------------------- the poster
def draw_poster():
    cv = Canvas(W, H)

    # Sky: indigo dusk melting into amber at the horizon.
    cv.vgrad(0, 320, INK, (38, 66, 92))
    cv.vgrad(320, HORIZON, (38, 66, 92), SKY_LOW)

    # Early stars, only high in the dusk, small and sparse.
    stars = [(60, 60), (150, 110), (250, 48), (330, 150), (430, 70),
             (520, 130), (620, 60), (700, 150), (820, 90), (920, 140),
             (960, 60), (880, 240), (180, 210), (480, 210), (60, 260),
             (940, 300), (380, 260), (700, 260), (120, 330), (840, 330)]
    for sx, sy in stars:
        cv.disc(sx, sy, 2.2, WHITE, alpha=0.75)
        cv.disc(sx, sy, 1.0, WHITE, alpha=1.0)

    # The ringed planet, high on the left: the one thing no earthly sky has.
    cv.disc(112, 232, 62, PLANET, feather=26, alpha=0.28)
    cv.disc(112, 232, 48, PLANET, feather=6)
    cv.disc(98, 219, 42, (238, 206, 150), feather=10, alpha=0.85)
    cv.ellipse_ring(112, 232, 88, 24, -0.42, 7, PLANET_RING, alpha=0.95)
    cv.ellipse_ring(112, 232, 88, 24, -0.42, 3, (250, 232, 190), alpha=0.9)
    # The planet's dark side, a crescent of shadow on its lower right.
    cv.disc(129, 248, 37, (196, 158, 104), feather=14, alpha=0.55)

    # Wisps of cloud catching the last light: faint, so they stay haze.
    for cy, cx, cw in [(330, 700, 220), (380, 300, 170), (430, 820, 190),
                       (470, 480, 150)]:
        cv.disc(cx, cy, cw // 2, (244, 178, 120), feather=cw // 3,
                alpha=0.09)
        cv.disc(cx, cy + 12, cw // 3, (250, 205, 150), feather=cw // 4,
                alpha=0.08)

    # The low sun, half-dipped at the horizon, and its halo.
    cv.disc(648, HORIZON - 6, 190, GOLD, feather=120, alpha=0.30)
    cv.disc(648, HORIZON - 6, 118, GOLD, feather=42, alpha=0.75)
    cv.disc(648, HORIZON - 6, 92, SUN_CORE, feather=10)

    # Sea: deep teal, darker as it falls away from the light.
    cv.vgrad(HORIZON, H, SEA_TOP, SEA_BOT, dither=False)
    # The sun's road across the water: short gold dashes that taper and
    # fade as they fall away from the horizon, never a solid column.
    for k in range(30):
        yy = HORIZON + 12 + k * 9
        t = k / 30.0
        half = int(96 * (1 - t * 0.6))
        xx = 648 + int(20 * math.sin(k * 2.3))
        # Two or three broken dashes per row, lengths from a fixed hash.
        segs = []
        pos = xx - half
        while pos < xx + half:
            ln = 14 + ((k * 37 + pos) % 41)
            segs.append((pos, min(xx + half, pos + ln)))
            pos += ln + 18 + ((k * 13 + pos) % 23)
        fade = 1.0 - t * 0.75
        for sx0, sx1 in segs:
            for x in range(sx0, sx1):
                cv.blend(x, yy, (255, 205, 120), 0.85 * fade)
                cv.blend(x, yy + 1, (240, 175, 90), 0.55 * fade)
    # Long horizontal shimmer strokes elsewhere on the water.
    strokes = [(180, 660, 120), (330, 700, 90), (880, 680, 130),
               (120, 760, 150), (880, 780, 110), (300, 830, 120),
               (760, 880, 150), (180, 920, 110), (520, 950, 130),
               (880, 950, 100)]
    for sx, sy, sl in strokes:
        cv.fill_rect(sx, sy, sx + sl, sy + 2, (64, 128, 140))
        cv.fill_rect(sx + 20, sy + 5, sx + sl - 30, sy + 6, (46, 104, 118))

    # The headland and its lighthouse, on the left.
    cv.poly([(0, 1024), (0, 742), (60, 700), (120, 668), (190, 652),
             (250, 640), (318, 636), (352, 660), (330, 760), (300, 900),
             (260, 1024)], CLIFF)
    cv.poly([(0, 1024), (0, 940), (110, 905), (190, 950), (230, 1024)],
            (20, 40, 48))
    # A little white town along the cliff top.
    houses = [(238, 606, 34, 26), (276, 612, 30, 20), (308, 618, 26, 18)]
    for hx, hy, hw, hh in houses:
        cv.fill_rect(hx, hy, hx + hw, hy + hh, CREAM)
        cv.poly([(hx - 3, hy), (hx + hw // 2, hy - 12), (hx + hw + 3, hy)],
                (150, 52, 44))
        cv.fill_rect(hx + hw // 2 - 3, hy + hh // 2, hx + hw // 2 + 3,
                     hy + hh // 2 + 6, (255, 196, 90))
    # The lighthouse: cream tower, two red bands, lamp room, dome.
    cv.poly([(158, 640), (166, 470), (196, 470), (204, 640)], CREAM)
    cv.poly([(160, 596), (164, 566), (198, 566), (202, 596)], RED)
    cv.poly([(163, 522), (166, 492), (196, 492), (199, 522)], RED)
    cv.fill_rect(160, 462, 202, 472, (40, 48, 58))
    cv.fill_rect(166, 430, 196, 462, (24, 30, 40))
    cv.fill_rect(176, 440, 186, 456, LAMP)
    cv.poly([(164, 430), (181, 414), (198, 430)], RED)
    cv.disc(181, 448, 26, LAMP, feather=20, alpha=0.85)
    # The beam, sweeping right across the water: one soft wedge, its inner
    # core a little brighter, ending before it reaches the sun's glow.
    cv.poly([(186, 444), (560, 408), (560, 492), (186, 456)],
            (255, 220, 130), alpha=0.11)
    cv.poly([(186, 446), (470, 428), (470, 468), (186, 452)],
            (255, 228, 150), alpha=0.08)
    # Two dark cypresses on the cliff edge.
    for tx, th in [(96, 74), (122, 58)]:
        cv.poly([(tx - 7, 668), (tx, 668 - th), (tx + 7, 668)], (10, 24, 28))
        cv.fill_rect(tx - 2, 668, tx + 2, 686, (10, 24, 28))

    # A lone sail on the mirror sea, right of the sun's road.
    cv.poly([(828, 812), (828, 730), (872, 812)], WHITE)
    cv.poly([(822, 812), (822, 748), (788, 812)], (226, 232, 228))
    cv.poly([(816, 812), (884, 812), (872, 828), (828, 828)], (24, 30, 40))
    cv.fill_rect(830, 830, 872, 832, (150, 190, 195))
    cv.fill_rect(836, 838, 864, 840, (120, 165, 175))

    # Birds, high over the water.
    for bx, by, s in [(380, 250, 16), (452, 208, 12), (520, 268, 14),
                      (610, 220, 11)]:
        cv.thick_line(bx - s, by, bx, by - 6, 3, INK)
        cv.thick_line(bx, by - 6, bx + s, by, 3, INK)

    # The name, set large across the top, cream on indigo.
    name = "SELKARA"
    scale = 15
    tw = text_width(name, scale)
    nx = (W - tw) // 2
    draw_text(cv, nx, 66, name, scale, CREAM, shadow=(10, 18, 30))
    # A thin gold rule under the name, with a small diamond at its centre.
    cv.fill_rect(300, 196, 724, 200, GOLD)
    cv.poly([(512, 186), (524, 198), (512, 210), (500, 198)], GOLD)

    # A thin cream frame, so the picture reads as a poster at a glance.
    cv.fill_rect(26, 26, W - 26, 31, CREAM)
    cv.fill_rect(26, H - 31, W - 26, H - 26, CREAM)
    cv.fill_rect(26, 26, 31, H - 26, CREAM)
    cv.fill_rect(W - 31, 26, W - 26, H - 26, CREAM)

    return cv


# ---------------------------------------------------------------- PNG writer
def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        start = y * cv.w * 3
        raw += cv.px[start:start + cv.w * 3]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    cv = draw_poster()
    size = write_png(cv, path)
    print(f"wrote {path} ({size} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
