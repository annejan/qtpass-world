"""One clock for the whole world: which date it is at every frame.

The canyon, the city, the planets, the titles and the sound all read the
date from here, so a release flares in all three at once and September 2026
hits the rock, the towers and the sky in the same frames. Plain Python, no
bpy.
"""
import bisect
import json
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 24
SECONDS = 180
FRAMES = SECONDS * FPS


def ts(day):
    return datetime.fromisoformat(day).timestamp()


def _last_sample():
    """The newest date any of the three data sets reaches."""
    last = []
    with open(os.path.join(HERE, "planets", "data", "files.json")) as fh:
        last.append(json.load(fh)["samples"][-1]["t"])
    with open(os.path.join(HERE, "city", "data", "tests.json")) as fh:
        last.append(json.load(fh)[-1]["t"])
    with open(os.path.join(HERE, "canyon", "scene_data.json")) as fh:
        last.append(json.load(fh)["ts"][-1])
    return max(last)


NOW = ts(datetime.fromtimestamp(_last_sample()).date().isoformat()) + 86400

# The calendar: (second, date). The quiet years go by in a blink; the first
# split and the first test, the CVE, and September 2026 get room.
KEYS = [
    (0, ts("2014-07-30")), (8, ts("2014-07-30")),      # the first commit
    (26, ts("2015-12-31")),                             # MainWindow, the first layers
    (33, ts("2016-11-12")),
    (40, ts("2016-12-20")),                             # the first split, the first test
    (45, ts("2017-12-20")),
    (51, ts("2018-01-25")),                             # the CVE, and v1.2.1
    (55, ts("2018-03-25")),                             # datahelpers in three
    (58, ts("2018-09-15")),
    (62, ts("2018-10-01")),                             # QtPass split off
    (70, ts("2026-01-01")),                             # seven quiet years
    (76, ts("2026-03-17")),
    (84, ts("2026-03-27")),                             # 140 tests in a week
    (90, ts("2026-05-12")),
    (97, ts("2026-05-20")),                             # another 140 in four days
    (101, ts("2026-09-12")),                            # a quiet summer
    (121, ts("2026-09-25")),                            # September
    (131, NOW),
    (SECONDS, NOW),                                     # the present
]
T_NOW = KEYS[-1][1]


def _raw(sec):
    for (s0, d0), (s1, d1) in zip(KEYS, KEYS[1:]):
        if sec <= s1:
            u = min(max((sec - s0) / (s1 - s0), 0.0), 1.0)
            return d0 + (d1 - d0) * u
    return KEYS[-1][1]


def _smooth():
    half = int(0.6 * FPS)
    raw = [_raw((f - 1) / FPS) for f in range(1 - half, FRAMES + 2 + half)]
    out = [raw[half]]
    for f in range(1, FRAMES + 2):
        w = raw[f - 1:f + 2 * half]
        out.append(sum(w) / len(w))
    for f in range(2, len(out)):  # keep it monotone
        out[f] = max(out[f], out[f - 1])
    return out


DATE = _smooth()  # unix time at every frame (1-based)


def t_of(frame):
    return (frame - 1) / FPS


def frame_at(sec):
    return int(round(sec * FPS)) + 1


def date_at(frame):
    """Unix time at a frame; frames may be fractional (slow motion)."""
    f = min(max(frame, 1.0), FRAMES + 1.0)
    i = min(int(f), FRAMES)
    return DATE[i] + (DATE[i + 1] - DATE[i]) * (f - i)


def frame_of_date(t):
    """First frame at which the calendar has reached t (the last one at most)."""
    return max(1, bisect.bisect_left(DATE, min(t, DATE[-1]), 1))


def sec_of_date(t):
    return t_of(frame_of_date(t))


def interp(keys, x):
    """Smoothstep between (x, value) keys."""
    for (x0, v0), (x1, v1) in zip(keys, keys[1:]):
        if x <= x1:
            u = min(max((x - x0) / (x1 - x0), 0.0), 1.0)
            u = u * u * (3 - 2 * u)
            return v0 + (v1 - v0) * u
    return keys[-1][1]


# ------------------------------------------------------------ the sky
# Dusk at the first commit, night from 2016 on, and a first light of dawn
# over the finished world at the end.

T_END = sec_of_date(T_NOW)  # second at which the calendar reaches today


def dusk(t):
    """0..1: what is left of the sunset (1 at the first commit)."""
    return interp([(0, 1.0), (8, 0.85), (22, 0.25), (34, 0.0)], t)


def dawn(t):
    """0..1: the sky lightening over the finished world."""
    return interp([(SECONDS - 26, 0.0), (SECONDS - 4, 0.7), (SECONDS, 0.75)], t)


# ------------------------------------------------------------ 2026

CLIMAX = sec_of_date(ts("2026-09-22T14:00"))  # the most windows lighting at once


def eruption(t):
    """0..1: how hard 2026 is erupting in the canyon at second t."""
    day = date_at(frame_at(t))
    e = interp([(ts("2025-12-15"), 0.0), (ts("2026-03-15"), 0.35),
                (ts("2026-08-01"), 0.8), (ts("2026-09-20"), 1.0)], day)
    # after today: the rock cools, slowly
    return e * interp([(T_END, 1.0), (T_END + 20, 0.55), (SECONDS, 0.45)], t)
