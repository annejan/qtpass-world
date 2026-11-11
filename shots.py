"""Where the parts of the world stand, and the camera: a list of shots with
cuts between them, on the world's clock (clock.py). Plain Python, no bpy.

A shot is a time span, a space its camera keys are written in, and the
keys: (second, camera xyz, target xyz, lens, f-stop). Spaces:

- "world": metres in the world
- "canyon": metres of the canyon film; an x written "c+1.5" is that far
  from the front ("now") at that frame, so the camera keeps pace with it
- "city": metres of the city film
- "planets": units of the planets film (the system's own plane)
- "follow:<class>": (outward, along the orbit, up) from that planet, in
  the system's units, for both camera and target

Planet shots roll the camera to the system's plane (roll 1), so its orbits
lie as they did in their own film.
"""
import bisect
import math

import clock as C
from canyon import timeline as CANYON
from planets import timeline as PLANETS

# ---------------------------------------------------------------- the set
# The canyon is three times the size of its own film: the wall runs along x
# from 3 to 230 m with its face towards -y. The city stands on the plain in
# front of the 2026 end of the wall, at its own film's size; the solar
# system hangs in the sky behind the wall, tilted to face the plain.
CANYON_SCALE = 3.0
CITY_AT, CITY_SCALE = (192.0, -75.0, 0.0), 1.0
PLANETS_AT, PLANETS_TILT, PLANETS_SCALE = (115.0, 160.0, 150.0), 60.0, 4.0

FPS = C.FPS
FIRST_COMMIT_FLARE = C.frame_at(8.0)  # a world frame
X1 = CANYON.X1


def from_canyon(p):
    return tuple(v * CANYON_SCALE for v in p)


def from_city(p):
    return tuple(CITY_AT[i] + CITY_SCALE * p[i] for i in range(3))


def from_planets(p):
    a = math.radians(PLANETS_TILT)
    x, y, z = (PLANETS_SCALE * v for v in p)
    return (PLANETS_AT[0] + x,
            PLANETS_AT[1] + y * math.cos(a) - z * math.sin(a),
            PLANETS_AT[2] + y * math.sin(a) + z * math.cos(a))


def from_follow(k, p, frame):
    x, y, z = PLANETS.place(k, frame)
    r = math.hypot(x, y) or 1.0
    out, along = (x / r, y / r), (-y / r, x / r)
    return from_planets((x + p[0] * out[0] + p[1] * along[0],
                         y + p[0] * out[1] + p[1] * along[1], z + p[2]))


# ---------------------------------------------------------------- the shots
# Time in the film is not the world's time. Every shot says which stretch
# of the world's clock it shows, and how fast: linear(w0, w1, ...) plays
# world seconds w0 to w1 at their own speed (camera keys in world
# seconds); timed(duration, [(film s into the shot, world s)], ...) can
# run the world's clock backwards, replay it or all but stop it (camera
# keys in film seconds into the shot).

def linear(w0, w1, space, keys, opts=None):
    return {"dur": w1 - w0, "world": [(0.0, w0), (w1 - w0, w1)], "space": space,
            "keys": [(k[0] - w0, *k[1:]) for k in keys], "opts": opts or {}}


def timed(dur, world, space, keys, opts=None):
    return {"dur": dur, "world": world, "space": space, "keys": keys,
            "opts": opts or {}}


SHOTS = [
    # today, the finished world at night; then twelve years run backwards
    # to the first commit, at dusk, on an empty plain
    timed(16.0, [(0.0, 138.0), (6.4, 144.4), (7.0, 143.6), (9.6, 1.2), (10.3, 0.0),
                 (16.0, 6.0)], "world", [
        (0.0, (128, -285, 9), (168, 0, 62), 26, 0),
        (16.0, (131, -268, 8), (166, 0, 58), 26, 0)],
     {"exposure": 0.5, "releases": False}),
    # the first commit: a flare at the foot of the bare wall (8.0 s)
    linear(6.0, 14.0, "canyon", [
        (6.0, ("c-0.75", -0.85, 0.09), ("c+0.1", -0.15, 0.05), 40, 1.4),
        (10.0, ("c-0.95", -1.0, 0.12), ("c+0.05", -0.1, 0.07), 38, 1.4),
        (14.0, ("c-1.6", -1.3, 0.25), ("c-0.25", 0, 0.22), 30, 1.6)],
     {"exposure": -0.4, "hand": 0.004}),
    # MainWindow and its dialogs form round the sun; the first releases
    linear(14.0, 21.5, "planets", [
        (14.0, (1.5, -8, 3.5), (0, 0, 2.0), 32, 0),
        (21.5, (3, -11, 5), (0, 0, 0.5), 30, 0)],
     {"roll": 1, "labels": 1}),
    # 2015: v1.0.0, the first layers
    linear(21.5, 30.0, "canyon", [
        (21.5, ("c-2.2", -1.5, 0.35), ("c-0.4", 0, 0.25), 28, 1.0),
        (25.0, ("c-4.5", -2.6, 0.9), ("c-0.5", 0, 0.8), 26, 1.4),
        (30.0, ("c-6", -3.6, 1.5), ("c-0.8", 0, 1.3), 26, 1.9)],
     {"exposure": -0.4, "hand": 0.01}),
    # November 2016: Pass, ImitatePass and RealPass split off MainWindow (35.1 s)
    linear(30.0, 37.0, "follow:mainwindow", [
        (30.0, (-1.2, -5.0, 2.8), (0, 0, 0), 30, 0),
        (37.0, (-0.8, -4.0, 2.2), (0, 0, 0), 32, 0)],
     {"roll": 1, "labels": 1}),
    # 13 December 2016: the first test, one window in an empty town (39.1 s)
    linear(37.0, 44.0, "city", [
        (37.0, (-5.0, -12.0, 1.4), (0.0, 6.0, 5.0), 30, 0),
        (40.0, (-2.6, -6.5, 1.1), (0.0, 0.0, 0.7), 34, 0),
        (44.0, (-4.0, -14.0, 1.6), (6.0, -5.0, 1.0), 28, 0)],
     {"hand": 0.02}),
    # 22 December 2017: the CVE, a red fault in the rock, until v1.2.1 seals
    # it on 4 January
    linear(44.0, 53.0, "canyon", [
        (44.0, ("c-5", -4.2, 1.4), ("c-0.5", 0, 1.0), 28, 1.9),
        (53.0, ("c-4", -3.2, 1.2), ("c-0.2", 0, 0.9), 30, 1.9)],
     {"exposure": -0.4, "hand": 0.01}),
    # 2018: datahelpers in three (54.9 s), then QtPass splits off (60.7 s)
    linear(53.0, 62.5, "planets", [
        (53.0, (2, -16, 7), (0, 0, 0), 28, 0),
        (62.5, (4, -18, 8), (0, 0, 0), 28, 0)],
     {"roll": 1, "labels": 1}),
    # seven quiet years: the front runs along the wall at night, and 2026
    # catches fire under it
    linear(62.5, 75.0, "canyon", [
        (62.5, ("c-10", -22.0, 1.6), ("c+1", 0, 2.4), 40, 0),
        (70.0, ("c-9", -24.0, 2.0), ("c+2", 0, 3.0), 40, 0),
        (75.0, ("c-8", -22.0, 2.6), ("c+0", 0, 6.0), 32, 0)],
     {"exposure": 0.2}),
    # March: 140 tests in a week, the city goes up
    linear(75.0, 85.0, "city", [
        (75.0, (-8.0, -24.0, 2.0), (6.0, -4.0, 2.5), 28, 0),
        (85.0, (-14.0, -18.0, 5.0), (2.0, 2.0, 4.0), 26, 0)],
     {"hand": 0.03}),
    # spring: 10,683 lines become 18,490
    linear(85.0, 96.0, "planets", [
        (85.0, (-8, -22, 9), (0, 0, 0), 26, 0),
        (96.0, (-10, -21, 8), (0, 0, 0), 26, 0)],
     {"roll": 1, "labels": 1}),
    # May: from the edge of town, all three at once
    linear(96.0, 101.5, "world", [
        (96.0, (146, -215, 2.2), (170, 0, 52), 26, 0),
        (101.5, (150, -210, 2.4), (172, 0, 55), 26, 0)],
     {"exposure": 0.4, "hand": 0.04}),
    # September: down into the streets; v1.8.0 and v1.8.1 go up
    linear(101.5, 107.5, "city", [
        (101.5, (-34.0, -5.2, 2.0), (-10.0, -2.0, 4.0), 20, 0),
        (107.5, (-16.0, -5.2, 1.8), (6.0, 4.0, 6.0), 18, 0)],
     {"hand": 0.03}),
    # 16 - 17 September: eight classes pulled off in two days (108.4 - 110.1 s)
    linear(107.5, 112.5, "follow:mainwindow", [
        (107.5, (-0.8, -4.0, 2.2), (0, 0, 0), 26, 0),
        (112.5, (-0.8, -4.0, 2.4), (0, 0, 0), 24, 0)],
     {"roll": 1, "labels": 1}),
    # 22 September, three times over: up the street to util ...
    timed(4.4, [(0.0, 112.5), (4.4, 116.9)], "city", [
        (0.0, (4.0, -6.0, 1.6), (8.0, 14.0, 7.0), 17, 0),
        (4.4, (6.0, 1.5, 1.5), (6.0, 22.0, 9.0), 16, 0)],
     {"hand": 0.03}),
    # ... at the front, as the rock erupts ...
    timed(2.8, [(0.0, 114.1), (2.8, 116.95)], "canyon", [
        (0.0, ("c-15", -22.0, 3.0), ("c+0", 0, 9.0), 24, 0),
        (2.8, ("c-14", -20.5, 3.4), ("c+0", 0, 10.0), 24, 0)],
     {"exposure": -0.2, "hand": 0.01}),
    # ... round the sun ...
    timed(2.4, [(0.0, 114.6), (2.4, 117.0)], "planets", [
        (0.0, (-6, -16, 6), (0, 0, 0), 28, 0),
        (2.4, (-6.5, -17, 6.5), (0, 0, 0), 28, 0)],
     {"roll": 1, "labels": 1}),
    # ... and on the peak's boom the whole world at once, time all but
    # stopped while the camera moves through it
    timed(9.0, [(0.0, 116.55), (0.74, C.CLIMAX), (1.7, 117.98), (6.0, 118.22),
                (7.3, 119.0), (9.0, 121.5)], "world", [
        (0.0, (140, -250, 10), (186, -20, 46), 24, 0),
        (6.0, (172, -150, 24), (194, -48, 30), 24, 0),
        (9.0, (186, -126, 31), (198, -40, 36), 24, 0)],
     {"exposure": 0.4}),
    # the past, rewritten: the old walls wear down under 2026
    linear(121.5, 131.0, "canyon", [
        (121.5, ("c-12", -16.0, 5.0), ("c-1", 2, 12.0), 22, 0),
        (131.0, ("c+3", -14.0, 7.0), ("c-1", 3, 14.0), 22, 0)],
     {"exposure": -0.2}),
    # today: the opening ran time back; now all twelve years build up once
    # more in one take, the camera arcing round the world, and land on today
    timed(12.0, [(0.0, 0.0), (1.0, 1.5), (8.0, 128.0), (9.2, 131.6), (12.0, 134.0)], "world", [
        (0.0, (40, -330, 22), (165, -20, 40), 28, 0),
        (6.0, (175, -385, 34), (168, -20, 46), 28, 0),
        (12.0, (318, -290, 30), (165, -20, 50), 28, 0)],
     {"exposure": 0.55, "releases": False, "quiet": True}),
    # and up: out of the streets, past the rim, into the sky
    linear(150.0, 180.0, "world", [
        (150.0, (186, -118, 2.5), (200, -40, 14), 22, 0),
        (160.0, (172, -165, 35), (175, 0, 55), 26, 0),
        (170.0, (150, -240, 100), (130, 60, 110), 28, 0),
        (180.0, (140, -290, 125), (125, 60, 120), 28, 0)],
     {"exposure": 0.5}),
]

STARTS = []
for _sh in SHOTS:
    STARTS.append(STARTS[-1] + SHOTS[len(STARTS) - 1]["dur"] if STARTS else 0.0)
FILM_SECONDS = STARTS[-1] + SHOTS[-1]["dur"]
FILM_FRAMES = int(round(FILM_SECONDS * FPS))
OPEN_END = 10.4  # the opening has run time back to the first commit by then


def _hermite(ts, vs, t):
    n = len(ts)
    i = min(max(bisect.bisect_right(ts, t) - 1, 0), n - 2)
    t0, t1 = ts[i], ts[i + 1]
    u = min(max((t - t0) / (t1 - t0), 0.0), 1.0)

    def slope(j):
        if j <= 0 or j >= n - 1:
            return 0.0
        return (vs[j + 1] - vs[j - 1]) / (ts[j + 1] - ts[j - 1])

    m0, m1 = slope(i) * (t1 - t0), slope(i + 1) * (t1 - t0)
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1
    h10 = u ** 3 - 2 * u ** 2 + u
    h01 = -2 * u ** 3 + 3 * u ** 2
    h11 = u ** 3 - u ** 2
    return h00 * vs[i] + h10 * m0 + h01 * vs[i + 1] + h11 * m1


def _pchip(xs, ys, x):
    """Monotone cubic through (xs, ys): no overshoot, so the world's clock
    never wobbles back where the keys only slow it down."""
    n = len(xs)
    if n == 2:
        u = min(max((x - xs[0]) / (xs[1] - xs[0]), 0.0), 1.0)
        return ys[0] + (ys[1] - ys[0]) * u
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0], m[-1] = d[0], d[-1]
    i = min(max(bisect.bisect_right(xs, x) - 1, 0), n - 2)
    u = min(max((x - xs[i]) / h[i], 0.0), 1.0)
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1
    h10 = u ** 3 - 2 * u ** 2 + u
    h01 = -2 * u ** 3 + 3 * u ** 2
    h11 = u ** 3 - u ** 2
    return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]


def shot_index(t):
    return min(max(bisect.bisect_right(STARTS, t) - 1, 0), len(SHOTS) - 1)


def world_sec(t):
    """The world's second at film second t."""
    i = shot_index(t)
    sh = SHOTS[i]
    xs, ys = zip(*sh["world"])
    return _pchip(xs, ys, t - STARTS[i])


def world_frame(frame):
    """The world's frame (fractional) at a film frame."""
    return world_sec(C.t_of(frame)) * FPS + 1.0


_WS = [world_sec(C.t_of(f)) for f in range(1, FILM_FRAMES + 2)]


def calm(frame):
    """1 while the world's clock runs at up to twice its speed, 0 from six
    times on: what flashes for a moment (fireworks, shockwaves) is left out
    when time races, where it could only strobe."""
    i = min(max(int(frame), 2), FILM_FRAMES)
    speed = abs(_WS[i] - _WS[i - 2]) / 2 * FPS  # world frames per film frame
    return min(max(1 - (speed - 2) / 4, 0.0), 1.0)


def _sweep():
    """Seconds swept by what turns at its own pace (the searchlights): the
    world's clock, but never faster than the film's, and not across cuts."""
    out, s = [0.0, 0.0], 0.0
    for f in range(2, FILM_FRAMES + 2):
        s += min(max(_WS[f - 1] - _WS[f - 2], -1 / FPS), 1 / FPS)
        out.append(s)
    return out


_SWEEP = _sweep()


def film_times(w):
    """Every film second at which the world's clock passes world second w
    going forwards (a replay passes it again)."""
    out = []
    for f in range(1, len(_WS)):
        a, b = _WS[f - 1], _WS[f]
        if a < w <= b:
            out.append(C.t_of(f) + (w - a) / (b - a) / FPS)
    return out


def film(w):
    """The film second at which the story first reaches world second w,
    after the opening has run time back."""
    times = [t for t in film_times(w) if t >= OPEN_END]
    return times[0] if times else FILM_SECONDS


def _track(space, keys, idx, t, frame, start):
    """One of camera (idx 1) or target (idx 2), in world metres, at film
    second t into the shot and the world's frame."""
    ts = [k[0] for k in keys]
    p = []
    for a in range(3):
        vals = []
        for k in keys:
            v = k[idx][a]
            if space == "canyon" and a == 0:
                # x relative to the cursor at that key, so the move keeps
                # pace with the front however fast time runs
                if isinstance(v, str):
                    v = float(v[1:])
                else:
                    v -= CANYON.cursor_x(world_sec(start + k[0]) * FPS + 1)
            vals.append(v)
        p.append(_hermite(ts, vals, t))
    if space == "world":
        return tuple(p)
    if space == "canyon":
        p[0] += CANYON.cursor_x(frame)
        return from_canyon(p)
    if space == "city":
        return from_city(p)
    if space == "planets":
        return from_planets(p)
    if space.startswith("follow:"):
        return from_follow(space[7:], p, frame)
    raise ValueError(space)


def _hand(t, amp, seed):
    """A slow drift, as from a hand-held camera: a few incommensurate sines."""
    if not amp:
        return (0.0, 0.0, 0.0)
    return tuple(amp * sum(math.sin(t * f + seed * 1.7 + a * 2.3 + f * 4.1) / (1 + j)
                           for j, f in enumerate((0.37, 0.71, 1.31)))
                 for a in range(3))


def camera(frame):
    """{cam, tgt, lens, fstop, exposure, labels, roll, shot, world} at a film
    frame; world is the world's (fractional) frame to show."""
    t = C.t_of(frame)
    i = shot_index(t)
    sh = SHOTS[i]
    space, keys, opts = sh["space"], sh["keys"], sh["opts"]
    dt = t - STARTS[i]
    wf = world_frame(frame)
    ts = [k[0] for k in keys]
    cam = _track(space, keys, 1, dt, wf, STARTS[i])
    tgt = _track(space, keys, 2, dt, wf, STARTS[i])
    h = opts.get("hand", 0.0) * (CANYON_SCALE if space == "canyon" else 1.0)
    hc, ht = _hand(t, h, i), _hand(t, h * 0.6, i + 9)
    return {
        "cam": tuple(cam[a] + hc[a] for a in range(3)),
        "tgt": tuple(tgt[a] + ht[a] for a in range(3)),
        "lens": _hermite(ts, [k[3] for k in keys], dt),
        "fstop": _hermite(ts, [k[4] for k in keys], dt),
        "exposure": opts.get("exposure", 0.0),
        "labels": opts.get("labels", 0.0),
        "roll": opts.get("roll", 0),
        "releases": opts.get("releases", True),
        "shot": i,
        "world": wf,
        "calm": calm(frame),
        "sweep": _SWEEP[min(max(int(frame), 1), FILM_FRAMES + 1)],
    }


def middles():
    """The middle film frame of every shot: a storyboard."""
    return [C.frame_at(STARTS[i] + sh["dur"] / 2) for i, sh in enumerate(SHOTS)]


# ---------------------------------------------------------------- titles

NUMBER = {n: w for n, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve".split())}


def stats():
    """The numbers the titles quote, from the three data sets."""
    from datetime import datetime

    from city import timeline as TESTS
    from planets import system as S

    def system_at(day):
        b = S.SIZES[S.sample_at(C.ts(day))]
        return len(b), sum(b.values())

    last = TESTS.SAMPLES[-1]["suites"]
    split = [k for k in S.DONOR if datetime.fromtimestamp(S.TIMES[S.BORN[k]]).date()
             .isoformat() in ("2026-09-16", "2026-09-17")]
    q_classes, q_lines = system_at("2025-12-31")
    st = dict(CANYON.STATS)
    st.update({
        "tests": sum(last.values()), "suites": len(last),
        "classes": len(S.SIZES[-1]), "class_lines": sum(S.SIZES[-1].values()),
        "quiet_classes": q_classes, "quiet_lines": q_lines,
        "spring_from": system_at("2026-03-01")[1], "spring_to": system_at("2026-05-31")[1],
        "split": NUMBER.get(len(split), len(split)),
    })
    return st


def cards():
    """(start, end, layout, big line, small line), in film seconds. Most are
    written in the world's seconds and land where the story reaches them."""
    s = stats()
    world = [
        (6.6, 12.8, "30 July 2014", "the first commit"),
        (14.6, 20.6, "2014 – 2015", "MainWindow and its dialogs"),
        (22.0, 29.2, "2015", f"v1.0.0 · {s['commits_2015']:,} commits that year"),
        (30.6, 37.0, "November 2016", "Pass, ImitatePass and RealPass split off MainWindow"),
        (38.2, 43.5, "13 December 2016", "the first test: “LOL wut, also how do I link ..”"),
        (44.8, 51.2, "22 December 2017", "CVE-2017-18021 reported; v1.2.1 seals it on 4 January"),
        (52.6, 57.2, "March 2018", "datahelpers breaks into three"),
        (57.6, 61.6, "September 2018",
         "QtPass splits off MainWindow: “It compiles, ship it . .”"),
        (62.6, 71.4, "2019 – 2025",
         f"seven quiet years: three tests, {s['quiet_classes']} classes"),
        (72.6, 79.4, "2026",
         f"{s['commits_2026']:,} commits · {s['share_2026']}% of all history"),
        (80.6, 87.4, "March", "140 tests in a week"),
        (88.6, 95.4, "spring",
         f"{s['spring_from']:,} lines of classes become {s['spring_to']:,}"),
        (96.4, 100.6, "May", "another 140 tests in four days"),
        (101.6, 107.0, "September", "526 tests in one week"),
        (107.9, 112.3, "16 – 17 September", f"{s['split']} classes pulled off in two days"),
        (121.6, 130.4, "the past, rewritten",
         f"{s['replaced_pct']}% of the older code replaced this year"),
    ]
    out = [(0.6, 6.2, "centre", "QtPass", "one world: its history, its tests, its classes")]
    out += [(round(film(w0), 2), round(film(w1), 2), "lower", big, small)
            for w0, w1, big, small in world]
    land = film_times(131.0)[-1]  # the last fast-forward reaches today
    out.append((round(land - 0.3, 2), round(land + 6.0, 2), "lower", "today",
                f"{s['lines_now']:,} lines · {s['tests']:,} tests · {s['classes']} classes"))
    out.append((round(film(164.0), 2), round(FILM_SECONDS - 0.6, 2), "centre", "QtPass",
                f"{s['commits']:,} commits · {s['authors']} contributors · "
                f"{s['locales']} languages · twelve years"))
    return out
