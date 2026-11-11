"""Where "now" is on the wall at every frame, on the world's clock
(clock.py). Plain Python, no bpy."""
import bisect
import json
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "scene_data.json")))
XMAP = DATA["xmap"]  # [unix time, x] on the first of every month
X0, X1 = DATA["x0"], DATA["x1"]
_XT = [t for t, _ in XMAP]
_XX = [x for _, x in XMAP]


def x_at_ts(ts):
    """x on the wall of a unix time."""
    i = min(max(bisect.bisect_right(_XT, ts) - 1, 0), len(_XT) - 2)
    f = (ts - _XT[i]) / (_XT[i + 1] - _XT[i])
    return _XX[i] + (_XX[i + 1] - _XX[i]) * f


def ts_at_x(x):
    """Unix time at x on the wall (x grows with time)."""
    i = min(max(bisect.bisect_right(_XX, x) - 1, 0), len(_XX) - 2)
    f = (x - _XX[i]) / (_XX[i + 1] - _XX[i])
    return _XT[i] + (_XT[i + 1] - _XT[i]) * f


def X(day):
    return x_at_ts(datetime.fromisoformat(day).timestamp())


from clock import FPS, FRAMES, SECONDS, DATE, dusk, eruption, t_of  # noqa: E402,F401

# The "now" cursor: where the world's date is on the wall, every frame.
CURSOR = [min(max(x_at_ts(d), X0), X1) for d in DATE]
for _f in range(2, len(CURSOR)):  # keep it monotone
    CURSOR[_f] = max(CURSOR[_f], CURSOR[_f - 1])


def cursor_x(frame):
    f = min(max(frame, 1.0), FRAMES + 1.0)
    i = min(int(f), FRAMES)
    return CURSOR[i] + (CURSOR[i + 1] - CURSOR[i]) * (f - i)


def now_ts(frame):
    return ts_at_x(cursor_x(frame))


def frame_of_x(x):
    """First frame at which the cursor has reached x (the present at most)."""
    return max(1, bisect.bisect_left(CURSOR, min(x, CURSOR[-1]), 1))


def night(t):
    """0..1: stars and moonlight."""
    return 1.0 - dusk(t)


# ------------------------------------------------------------ titles
STATS = DATA.get("stats", {})
