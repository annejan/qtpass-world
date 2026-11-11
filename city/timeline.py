"""How many tests each suite has at every frame, on the world's clock
(clock.py). Plain Python, no bpy."""
import bisect
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = json.load(open(os.path.join(HERE, "data", "tests.json")))
TAGS = json.load(open(os.path.join(HERE, "data", "tags.json")))
_ST = [s["t"] for s in SAMPLES]

from clock import (CLIMAX, FPS, FRAMES, NOW, SECONDS, T_NOW,  # noqa: E402,F401
                   date_at, dawn, frame_of_date, t_of, ts)


# ---------------------------------------------------------------- tests

SUITES = sorted({s for o in SAMPLES for s in o["suites"]},
                key=lambda s: (next(o["t"] for o in SAMPLES if s in o["suites"]), s))
FINAL = {s: SAMPLES[-1]["suites"].get(s, max(o["suites"].get(s, 0) for o in SAMPLES))
         for s in SUITES}
PEAK = {s: max(o["suites"].get(s, 0) for o in SAMPLES) for s in SUITES}
BORN = {s: next(o["t"] for o in SAMPLES if s in o["suites"]) for s in SUITES}


def count_at(suite, t):
    """Tests in a suite at unix time t, linear between the weekly samples."""
    i = bisect.bisect_right(_ST, t) - 1
    if i < 0:
        return 0.0
    a = SAMPLES[i]["suites"].get(suite, 0)
    if i + 1 >= len(SAMPLES):
        return float(a)
    b = SAMPLES[i + 1]["suites"].get(suite, 0)
    u = (t - _ST[i]) / (_ST[i + 1] - _ST[i])
    return a + (b - a) * u


def total_at(t):
    return sum(count_at(s, t) for s in SUITES)


def ci_at(t):
    i = bisect.bisect_right(_ST, t) - 1
    return SAMPLES[max(i, 0)]["ci"] if i >= 0 else 0


def lit_events():
    """(frame, suite, window index) for every window as it first lights."""
    out = []
    counts = {s: 0 for s in SUITES}
    for f in range(1, FRAMES + 1):
        t = date_at(f)
        for s in SUITES:
            n = int(count_at(s, t) + 1e-6)
            while counts[s] < n:
                out.append((f, s, counts[s]))
                counts[s] += 1
    return out


def releases():
    """(frame, name) for every tag, at the frame the calendar reaches it."""
    return [(frame_of_date(t), name) for name, t in TAGS if t <= T_NOW + 86400]


def pulse(t):
    """0..1: the city's flare at the climax, sharp in, slow out."""
    if t < CLIMAX:
        return math.exp(-(CLIMAX - t) / 0.25)
    return math.exp(-(t - CLIMAX) / 1.2)


def peak(t):
    """0..1: a wider swell round the climax (the searchlights stand up)."""
    if t < CLIMAX:
        u = min(max((t - (CLIMAX - 1.5)) / 1.5, 0.0), 1.0)
    else:
        u = min(max(1 - (t - CLIMAX) / 3.0, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def finale():
    """(frame, name) for the climax's own fireworks, after the releases'."""
    return [(int((CLIMAX + 0.05 + 0.3 * k) * FPS) + 1, "finale") for k in range(8)]
