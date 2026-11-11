"""Where every planet is and how big, on the world's clock (clock.py).
Plain Python, no bpy."""
import bisect
import math
from datetime import datetime

from . import system as S

from clock import (FPS, FRAMES, NOW, date_at, frame_of_date,  # noqa: F401
                   t_of, ts)

# ---------------------------------------------------------------- bodies

BIRTH = {k: frame_of_date(S.TIMES[i]) for k, i in S.BORN.items()}
DEATH = {k: frame_of_date(S.TIMES[i]) for k, i in S.DIED.items()}
DRIFT = 2.5 * FPS   # frames a split-off moon takes to reach its own orbit
FALL = 2.0 * FPS    # frames a dead class takes to fall into the sun
SPEED = 0.45        # rad/s at the innermost orbit


def _sizes():
    """Planet radius per body per frame, easing towards the lines it has."""
    out = {k: [0.0] * (FRAMES + 2) for k in S.ORDER}
    last = {k: 0.0 for k in S.ORDER}
    for f in range(1, FRAMES + 2):
        b = S.SIZES[S.sample_at(date_at(f))]
        for k in S.ORDER:
            n = b.get(k, 0)
            if not n and k in DEATH and f >= DEATH[k]:
                n = S.SIZES[S.DIED[k] - 1][k]  # keep its size while it falls
            target = S.radius(n) if n else 0.0
            last[k] += (target - last[k]) * 0.12
            out[k][f] = last[k]
    return out


SIZE = _sizes()


def size(k, frame):
    """Radius of body k at a frame; frames may be fractional."""
    f = min(max(frame, 1.0), FRAMES + 1.0)
    i = min(int(f), FRAMES)
    return SIZE[k][i] + (SIZE[k][i + 1] - SIZE[k][i]) * (f - i)


def lines_at(k, frame):
    return S.SIZES[S.sample_at(date_at(frame))].get(k, 0)


def _ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def _orbit_xyz(k, r, film_s):
    a = S.PHASE[k] + film_s * SPEED * (S.ORBIT[S.ORDER[0]] / S.ORBIT[k]) ** 1.5
    tilt = S.TILT[k]
    return (r * math.cos(a), r * math.sin(a), r * math.sin(a - S.PHASE[k]) * tilt)


def place(k, frame, depth=0):
    """(x, y, z) of body k at a frame: on its orbit, still drifting off its
    donor if it was just split off, or falling into the sun if it died."""
    film_s = t_of(frame)
    r = S.ORBIT[k]
    if k in DEATH and frame >= DEATH[k]:
        r *= 1 - _ease((frame - DEATH[k]) / FALL)
    p = _orbit_xyz(k, r, film_s)
    d = S.DONOR.get(k)
    if d and depth < 3 and frame < BIRTH[k] + DRIFT:
        u = _ease((frame - BIRTH[k]) / DRIFT)
        q = place(d, frame, depth + 1)
        gap = size(d, frame) * 0.8  # it buds out of its donor's surface
        a = S.PHASE[k]
        moon = (q[0] + gap * math.cos(a), q[1] + gap * math.sin(a), q[2] + 0.2)
        p = tuple(moon[i] + (p[i] - moon[i]) * u for i in range(3))
    return p


def alive(k, frame):
    """0..1: how present the body is (fades in at birth, out in the sun)."""
    if frame < BIRTH[k]:
        return 0.0
    if k in DEATH and frame >= DEATH[k] + FALL:
        return 0.0
    return 1.0


def touched(k, frame):
    """0..1: a glow when the body's lines just changed (a commit landed)."""
    i = S.sample_at(date_at(frame))
    j = S.sample_at(date_at(max(frame - 6, 1)))
    if i == j:
        return 0.0
    a, b = S.SIZES[j].get(k, 0), S.SIZES[i].get(k, 0)
    return min(abs(b - a) / 40.0, 1.0) if a and b else 0.0


def releases():
    """(frame, name) for every tag, at the frame the calendar reaches it."""
    return [(frame_of_date(t), name) for name, t in S.TAGS if t <= NOW + 86400]
