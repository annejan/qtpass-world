"""Traffic: a light snake down the streets for the commits, as many at a
time as there are commits around that moment of the film.

Each snake drives on the right-hand side of a street, turns at crossings
(no U-turns), and leaves town at the edge of the grid. The whole film is
simulated once, from a fixed seed, so every frame and every render agree.
Shared by build_scene.py and topview.py. Plain Python, no bpy.

snakes(frame) -> [(points, glow, kind)]: points from head to tail as (x, y),
glow 0..1 for fading in and out, kind the commit's (see COLOURS).
"""
import bisect
import json
import math
import os
import random

from . import layout as L
from . import timeline as TL

COMMITS = json.load(open(os.path.join(TL.HERE, "data", "commits.json")))  # [[t, kind]]
TIMES = [t for t, _ in COMMITS]
# The colour of a snake: the kind of commit it carries.
COLOURS = {
    "l10n": (0.2, 0.85, 1.0),    # translations: cyan
    "fix": (1.0, 0.5, 0.15),     # orange
    "feat": (1.0, 0.3, 0.8),     # magenta
    "test": (0.75, 1.0, 0.2),    # yellow-green, apart from the windows' green
    "ci": (1.0, 0.85, 0.2),      # yellow
    "docs": (0.65, 0.55, 1.0),   # lavender
    "tidy": (0.3, 0.5, 1.0),     # blue
    "other": (1.0, 0.93, 0.82),  # warm white
}
TAIL = 14           # positions kept per snake: the tail, one per frame
LANE = 0.75         # metres right of the street's centre line
MAX_ALIVE = 220
K = range(-L.RINGS, L.RINGS)  # street indices; nodes are their crossings


def _rate():
    """Snakes to start per frame: busy when the project was busy (commits
    per real week around the date), whatever the film's pace."""
    import bisect
    week = 7 * 86400
    out = []
    for f in range(TL.FRAMES + 2):
        t = TL.date_at(f)
        per_week = bisect.bisect(TIMES, t + week / 2) - bisect.bisect(TIMES, t - week / 2)
        out.append(min(0.45 * per_week ** 0.8, 12.0) / TL.FPS)
    return out


def _neighbours(node):
    i, j = node
    return [(i + di, j + dj) for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if (i + di) in K and (j + dj) in K]


def _pos(a, b, s):
    """Point s metres from node a towards node b, in the right-hand lane."""
    ax, ay = L.street(a[0]), L.street(a[1])
    bx, by = L.street(b[0]), L.street(b[1])
    dx, dy = (bx - ax) / L.SPACING, (by - ay) / L.SPACING
    return (ax + dx * s + dy * LANE, ay + dy * s - dx * LANE)


def _simulate():
    rnd = random.Random(5247)
    rate = _rate()
    alive, frames = [], [[] for _ in range(TL.FRAMES + 2)]
    carry = 0.0
    edge = [n for n in ((i, j) for i in K for j in K)
            if n[0] in (K[0], K[-1]) or n[1] in (K[0], K[-1])]
    for f in range(1, TL.FRAMES + 2):
        carry += rate[f]
        while carry >= 1 and len(alive) < MAX_ALIVE:
            carry -= 1
            a = rnd.choice(edge) if rnd.random() < 0.6 else (rnd.choice(K), rnd.choice(K))
            b = rnd.choice(_neighbours(a))
            # a real commit from around this date gives the snake its colour
            t = TL.date_at(f)
            lo = bisect.bisect(TIMES, t - 4 * 86400)
            hi = max(bisect.bisect(TIMES, t + 4 * 86400), lo + 1)
            kind = COMMITS[min(rnd.randrange(lo, hi), len(COMMITS) - 1)][1]
            alive.append({"a": a, "b": b, "s": 0.0, "v": rnd.uniform(9, 15), "kind": kind,
                          "trail": [], "age": 0, "life": rnd.uniform(4, 9) * TL.FPS,
                          "gone": None})
        carry = min(carry, 1.0)
        for c in alive:
            c["age"] += 1
            if c["gone"] is None:
                c["s"] += c["v"] / TL.FPS
                while c["s"] >= L.SPACING:
                    c["s"] -= L.SPACING
                    prev, here = c["a"], c["b"]
                    options = [n for n in _neighbours(here) if n != prev]
                    if not options or (c["age"] > c["life"] and here in edge):
                        c["gone"] = c["age"]
                        c["s"] = L.SPACING
                        c["a"], c["b"] = prev, here
                        break
                    ahead = (2 * here[0] - prev[0], 2 * here[1] - prev[1])
                    if ahead in options and rnd.random() < 0.55:
                        nxt = ahead
                    else:
                        nxt = rnd.choice(options)
                    c["a"], c["b"] = here, nxt
                c["trail"].insert(0, _pos(c["a"], c["b"], c["s"]))
            else:
                c["trail"].insert(0, c["trail"][0])
            del c["trail"][TAIL:]
        keep = []
        for c in alive:
            fade_in = min(c["age"] / 8, 1)
            fade_out = 1.0 if c["gone"] is None else max(1 - (c["age"] - c["gone"]) / TAIL, 0)
            glow = fade_in * fade_out
            if glow > 0:
                frames[f].append((list(c["trail"]), glow, c["kind"]))
                keep.append(c)
        alive = keep
    return frames


FRAMES = _simulate()


def snakes(frame):
    return FRAMES[min(max(int(frame), 1), TL.FRAMES + 1)]
