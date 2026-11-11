#!/usr/bin/env python3
"""The soundtrack of the world, generated from the same clock as the picture.

audio.py [OUT.wav]   (default audio.wav; 48 kHz stereo, SECONDS long)

One drone in D that changes chord with the chapters, wind over the canyon
and crickets and hum in town, and a voice for each part, from their own
films: the canyon pings for every commit (pitch by author) and rumbles in
2026, the city blips for every test that lands and sets off fireworks, the
planets ring a bell for every new class and swell when one is torn off
another. Every release booms once for all three. The parts the camera is
on are loudest; a wide shot hears them all.
"""
import random
import sys
import wave
from datetime import datetime

import numpy as np
from scipy import signal

import clock as C
import shots
from canyon import timeline as CANYON
from city import timeline as CITY
from planets import system as S
from planets import timeline as PLANETS

SR = 48000
SECONDS = shots.FILM_SECONDS
N = int(SECONDS * SR)
T = np.arange(N) / SR
# the world's second at every film frame: sounds of the world play where
# the film passes their moment going forwards, so a replay sounds again
WS = np.array([shots.world_sec(C.t_of(f)) for f in range(1, shots.FILM_FRAMES + 2)])
FT = np.array([C.t_of(f) for f in range(1, shots.FILM_FRAMES + 2)])


SHOT = np.array([shots.shot_index(t) for t in FT])


def film_times(w):
    a, b = WS[:-1], WS[1:]
    i = np.nonzero((a < w) & (b >= w) & (SHOT[:-1] == SHOT[1:]))[0]  # not across a cut
    return list(FT[i] + (w - a[i]) / (b[i] - a[i]) / C.FPS)
rng = np.random.default_rng(2014)
rnd = random.Random(5246)


def keyed(keys):
    """Smooth envelope over the whole film from (film second, value) keys."""
    grid = np.arange(0, SECONDS + 1, 0.05)
    return np.interp(T, grid, [C.interp(keys, t) for t in grid])


def per_world_second(fn):
    """An envelope fn(world second), as the film shows the world's clock."""
    grid = np.arange(0, SECONDS + 1, 0.05)
    return np.interp(T, grid, [fn(shots.world_sec(t)) for t in grid])


def lowpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2))
    return signal.lfilter(b, a, x)


def bandpass(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    return signal.lfilter(b, a, x)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


STEMS = {k: np.zeros((N, 2)) for k in ("bed", "canyon", "city", "planets", "all")}


# shots where time races (the fast-forward): the world keeps its sounds to
# itself there, or every commit and release would go off at once
QUIET = [(shots.STARTS[i], shots.STARTS[i] + sh["dur"]) for i, sh in enumerate(shots.SHOTS)
         if sh["opts"].get("quiet")]


def add(stem, t, g, pan=0.5, amp=1.0, world=True):
    """Mix mono g into a stem at world second t (at every film moment that
    shows it), or at film second t with world=False; panned 0 .. 1."""
    if world:
        for tf in film_times(t):
            if not any(a <= tf < b for a, b in QUIET):
                add(stem, tf, g, pan, amp, world=False)
        return
    out = STEMS[stem]
    i = int(t * SR)
    if i >= N or i + len(g) <= 0:
        return
    if i < 0:
        g, i = g[-i:], 0
    j = min(i + len(g), N)
    out[i:j, 0] += g[:j - i] * amp * (1 - pan)
    out[i:j, 1] += g[:j - i] * amp * pan


def bell(stem, t, f0, amp, pan=0.5, decay=3.0, world=True):
    L = int(decay * 2.5 * SR)
    tt = np.arange(L) / SR
    g = sum(a * np.sin(2 * np.pi * f0 * p * tt) * np.exp(-tt * (1 + p) / decay)
            for p, a in ((1, 1), (2.76, 0.45), (5.4, 0.2), (8.9, 0.08)))
    add(stem, t, g, pan, amp, world)


def boom(stem, t, amp, base=42, length=2.5, world=True):
    L = int(length * SR)
    tb = np.arange(L) / SR
    fb = base * np.exp(-tb * 0.7) + 30
    g = np.sin(2 * np.pi * np.cumsum(fb) / SR) * np.exp(-tb * 1.8) * (1 - np.exp(-tb * 200))
    add(stem, t, g, 0.5, amp, world)


night = per_world_second(lambda w: 1 - C.dusk(w))
erupt = per_world_second(C.eruption)
size = per_world_second(lambda w: min(CITY.total_at(C.date_at(w * C.FPS + 1)) / 1256, 1))
BOOM = film_times(C.CLIMAX)[0]  # the peak, once, in the wide
REWIND = (7.0, 10.3)  # the opening runs twelve years back
TAIL = keyed([(0, 1), (SECONDS - 14, 1), (SECONDS - 3, 0.25), (SECONDS, 0)])  # the end


def crowd(times, window):
    """For each time, how many of the times lie within the window of it."""
    ts_ = np.sort(np.asarray(times))
    return {t: int(np.searchsorted(ts_, t + window, "right") - np.searchsorted(ts_, t - window))
            for t in times}

# ---------------------------------------------------------------- the bed
bed = STEMS["bed"]
for ch in range(2):
    w = rng.standard_normal(N)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.07 + 0.01 * ch) * T + ch) * \
        np.sin(2 * np.pi * 0.023 * T + 1.3)
    wind = (lowpass(w, 380) * 2.5 + bandpass(w, 500, 1800) * 0.25) * lfo
    bed[:, ch] += wind * (0.10 + 0.08 * night) * (1 - 0.5 * erupt) * (1 - 0.5 * size) * TAIL

CHORDS = [  # (from film second, MIDI notes)
    (0, [38, 45, 52, 54, 57]),   # Dsus2/6: today
    (REWIND[1], [38, 45, 50, 53]),  # Dm: the first commit
    (shots.film(14), [34, 41, 46, 50]),  # Bb: MainWindow, the first layers
    (shots.film(30), [41, 48, 53, 57]),  # F: the first split, the first test
    (shots.film(62), [38, 45, 52]),      # Dm9, sparse: the quiet years
    (shots.film(72), [38, 45, 50, 53]),  # Dm: 2026 begins
    (shots.film(88), [34, 41, 46, 50, 53]),  # Bb
    (shots.film(101), [36, 43, 48, 52, 55]),  # C: September
    (BOOM, [38, 45, 50, 54, 57]),        # D major: the peak
    (shots.film(150), [38, 45, 52, 54, 57]),  # Dsus2/6, open: up into the sky
]
# crossfades are centred on the change at equal power, so the level holds;
# the peak's chord comes in on the boom itself. The two detuned voices of
# every note lean left and right: wide, and still whole in mono.
drone = np.zeros((N, 2))
fade = int(2.5 * SR)
for i, (t0, notes) in enumerate(CHORDS):
    t1 = CHORDS[i + 1][0] if i + 1 < len(CHORDS) else SECONDS
    lead = int(0.1 * SR) if t0 == BOOM else fade
    a = max(int(t0 * SR) - (0 if t0 == BOOM else fade // 2), 0)
    b = min(int(t1 * SR) + fade // 2, N)
    tt = T[a:b]
    g = np.ones(b - a)
    if a:
        g[:lead] = np.linspace(0, 1, lead) ** 0.5
    if b < N:
        g[-fade:] *= np.linspace(1, 0, fade) ** 0.5
    for n in notes:
        f = hz(n)
        for h, amp in ((1, 1.0), (2, 0.35), (3, 0.12)):
            for det, left in ((-0.6, 0.7), (0.6, 0.3)):
                v = np.sin(2 * np.pi * (f * h + det) * tt + rng.uniform(0, 6.28)) * amp * g
                drone[a:b, 0] += v * left
                drone[a:b, 1] += v * (1 - left)
drone = lowpass(drone.T, 1400).T / 15
level = keyed([(0, 0), (3, 0.6), (REWIND[0], 0.6), (REWIND[0] + 1.5, 0.1), (REWIND[1], 0.15),
               (REWIND[1] + 4, 0.4), (shots.film(62), 0.55), (shots.film(64), 0.35),
               (shots.film(72), 0.45), (shots.film(101), 0.6), (BOOM, 0.9),
               (shots.film(131), 0.75), (SECONDS - 7, 0.6), (SECONDS, 0)])
bed += drone * level[:, None]

# the rewind: tape running backwards, a reversed swell and a falling sweep
a, b = int(REWIND[0] * SR), int(REWIND[1] * SR)
tr = np.arange(b - a) / SR
u = tr / tr[-1]
whoosh = bandpass(rng.standard_normal(b - a), 200, 6000) * np.sin(np.pi * u) ** 1.5
sweep = np.sin(2 * np.pi * np.cumsum(900 * (1 - u) ** 2 + 60) / SR) * np.sin(np.pi * u) ** 2
rev = np.zeros(b - a)
L = min(int(2.5 * SR), b - a)
tt = np.arange(L) / SR
cymbal = bandpass(rng.standard_normal(L), 3000, 12000) * np.exp(-tt * 2.0)
rev[-L:] = cymbal[::-1]
for ch in range(2):
    STEMS["all"][a:b, ch] += (whoosh * 0.18 + sweep * 0.05 + rev * 0.12) * (1 if ch else 0.92)

# the fast-forward: the rewind's mirror, a rising sweep that lands on today
for q0, q1 in QUIET:
    a, b = int((q0 + 0.6) * SR), int((q0 + 9.4) * SR)
    tr = np.arange(b - a) / SR
    u = tr / tr[-1]
    build = u ** 1.5 * np.clip((1 - u) / 0.1, 0, 1)  # grows into the landing
    swell = bandpass(rng.standard_normal(b - a), 300, 7000) * build
    sweep = np.sin(2 * np.pi * np.cumsum(70 + 700 * u ** 2) / SR) * build
    for ch in range(2):
        STEMS["all"][a:b, ch] += (swell * 0.10 + sweep * 0.05) * (1 if ch else 0.92)
    land = shots.film_times(131.0)[-1]
    bell("all", land, hz(74), 0.12, 0.45, decay=5, world=False)
    bell("all", land + 0.03, hz(78), 0.07, 0.55, decay=5, world=False)
    bell("all", land + 0.06, hz(81), 0.06, 0.5, decay=5, world=False)

# ---------------------------------------------------------------- canyon
# a soft ping for every commit as the front passes it, pitched by author
PENTA = [62, 64, 66, 69, 71, 74, 76, 78, 81, 83]  # D major pentatonic
times = []
for x, a in CANYON.DATA["commits"]:
    t = C.t_of(CANYON.frame_of_x(x) + rnd.random())
    if t < 8.0:  # the first commit's own, after its flare
        t = 8.2 + rnd.uniform(0, 3)
    times.append((t, a))
counts = np.zeros(C.SECONDS + 1)
for t, _ in times:
    counts[min(int(t), C.SECONDS)] += 1
L = int(0.35 * SR)
tg = np.arange(L) / SR
for t, a in times:
    note = PENTA[(a * 7 + 3) % len(PENTA)] if a else PENTA[(int(t * 7) % 4) + 2]
    f = hz(note) * (1 + rnd.uniform(-0.003, 0.003))
    amp = 0.09 / np.sqrt(max(counts[min(int(t), C.SECONDS)], 1))
    g = np.sin(2 * np.pi * f * tg) * np.exp(-tg * 14) * (1 - np.exp(-tg * 900))
    g += 0.3 * np.sin(2 * np.pi * f * 2.01 * tg) * np.exp(-tg * 22)
    add("canyon", t, g, rnd.uniform(0.15, 0.85), amp)

bell("canyon", C.t_of(shots.FIRST_COMMIT_FLARE), hz(74), 0.22, decay=4.5)

# CVE-2017-18021: the fault cracks open over a tritone that does not belong
# to D, then v1.2.1 seals it and the tension resolves
t_cve = C.t_of(CANYON.frame_of_x(CANYON.x_at_ts(datetime.fromisoformat("2017-12-22").timestamp())))
t_fix = C.t_of(CANYON.frame_of_x(CANYON.x_at_ts(datetime.fromisoformat("2018-01-04").timestamp())))
L = int(0.9 * SR)
tt = np.arange(L) / SR
snap = (rng.random(L) < 0.02 * np.exp(-tt * 6)) * rng.standard_normal(L)
snap = bandpass(snap, 700, 7000) * 6 + bandpass(rng.standard_normal(L), 150, 900) \
    * np.exp(-tt * 9) * 0.5
L2 = int(1.6 * SR)
t2 = np.arange(L2) / SR
cluster = sum(np.sin(2 * np.pi * hz(n) * t2 + p) for n, p in ((56, 0), (62, 1.1), (63, 2.3)))
cluster *= np.minimum(t2 / 0.05, 1) * np.exp(-t2 * 1.8) * 0.05
add("canyon", t_cve, snap, 0.45, 0.14)
add("canyon", t_cve - 0.9, snap[::-1], 0.55, 0.06)  # and the strain before it
add("canyon", t_cve, cluster, 0.5, 1.0)
bell("canyon", t_fix + 0.1, hz(74), 0.12, decay=3.0)  # v1.2.1 seals it
bell("canyon", t_fix + 0.12, hz(81), 0.06, decay=3.0)

# the 2026 eruption: rumble and crackle
rum = lowpass(rng.standard_normal(N), 90, 4) * 6 + 0.4 * np.sin(2 * np.pi * 33 * T)
rum *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.31 * T) * np.sin(2 * np.pi * 0.13 * T)
crack = (rng.random(N) < 0.0009).astype(float) * rng.standard_normal(N)
crack = np.tanh(bandpass(crack, 900, 6000) * 9 / 3) * 3  # no click louder than the boom
for ch in range(2):
    STEMS["canyon"][:, ch] += np.roll(crack, ch * 37) * erupt ** 1.5 * 0.08
# The rumble is the ground under everything, so it does not jump with the
# cuts as the voices do; it draws back before the peak so the boom has
# somewhere to come from, and settles after it.
RUMBLE = rum * erupt * 0.24 * TAIL * keyed([
    (0, 0.5), (REWIND[0], 0.5), (REWIND[1], 1.0), (BOOM - 3.0, 1.0), (BOOM - 0.4, 0.3),
    (BOOM, 1.0), (BOOM + 8.0, 0.6), (SECONDS, 0.6)])

# ---------------------------------------------------------------- city
for ch in range(2):
    # crickets until the city drowns them, and its hum as it grows
    chirp = np.sin(2 * np.pi * (4300 + 180 * ch) * T)
    gate = (np.sin(2 * np.pi * 21 * T + ch) > 0.2) * \
        (np.sin(2 * np.pi * (0.43 + 0.07 * ch) * T + 2 * ch) > 0.35)
    STEMS["city"][:, ch] += lowpass(gate.astype(float), 300) * chirp * 0.012 * night * (1 - 0.6 * size)
    hum = lowpass(rng.standard_normal(N), 160, 3) * 3 + 0.25 * np.sin(2 * np.pi * (55 + ch * 0.3) * T)
    STEMS["city"][:, ch] += hum * (0.01 + 0.07 * size) * TAIL

PENTA_T = [62, 64, 66, 69, 71, 74, 76, 78, 81, 83, 86]
events = CITY.lit_events()
per_sec = np.zeros(C.SECONDS + 1)
for f, _, _ in events:
    per_sec[min(int(C.t_of(f)), C.SECONDS)] += 1
L = int(0.3 * SR)
tg = np.arange(L) / SR
for f, suite, k in events:
    t = C.t_of(f) + rnd.uniform(0, 1 / C.FPS)
    si = CITY.SUITES.index(suite)
    fr = hz(PENTA_T[(si * 3 + k % 3) % len(PENTA_T)]) * (1 + rnd.uniform(-0.002, 0.002))
    amp = 0.1 / max(per_sec[min(int(t), C.SECONDS)], 1) ** 0.35  # many sound like many
    g = np.sin(2 * np.pi * fr * tg) * np.exp(-tg * 16) * (1 - np.exp(-tg * 900))
    g += 0.25 * np.sin(2 * np.pi * fr * 3.0 * tg) * np.exp(-tg * 30)
    add("city", t, g, 0.5 + 0.35 * np.sin(si * 1.7), amp)
bell("city", C.t_of(events[0][0]), hz(74), 0.2, decay=4.5)  # the first test

for f0, name in CITY.releases() + CITY.finale():
    t = C.t_of(f0) + (0 if name == "finale" else rnd.uniform(0, 4) / C.FPS)
    big = "rc" not in name and "beta" not in name
    wl = int(0.5 * SR)
    tw = np.arange(wl) / SR
    whistle = np.sin(2 * np.pi * np.cumsum(1200 + 1600 * tw / 0.5) / SR) * np.linspace(0, 1, wl) * 0.025
    Lp = int(1.6 * SR)
    tp = np.arange(Lp) / SR
    pop = lowpass(rng.standard_normal(Lp), 900, 2) * np.exp(-tp * 9) * (0.5 if big else 0.3)
    crk = (rng.random(Lp) < 0.004 * np.exp(-tp * 1.5)) * rng.standard_normal(Lp)
    crk = np.tanh(bandpass(crk, 1500, 9000) * 2.5 / 0.8) * 0.8
    pan = rnd.uniform(0.25, 0.75)
    for tf in film_times(t):  # the whistle belongs to its pop, once per pop
        if not any(a <= tf < b for a, b in QUIET):
            add("city", tf - 0.5, whistle, pan, world=False)
    add("city", t, pop + crk, pan, 0.5)

# ---------------------------------------------------------------- planets
R = max(S.ORBIT.values())
STEPS = [50, 52, 54, 57, 59, 62, 64, 66, 69, 71, 74, 76, 78, 81]
FIRST = C.t_of(shots.FIRST_COMMIT_FLARE)
BORN = {k: max(C.t_of(PLANETS.BIRTH[k]), FIRST + 0.4) for k in S.ORDER}  # after the first bell
TOGETHER = crowd(list(BORN.values()), 0.5)
for k in S.ORDER:
    t = BORN[k]
    pan = 0.5 + 0.35 * np.sin(S.PHASE[k])
    note = STEPS[int((S.ORBIT[k] - 4.2) / (R - 4.2) * (len(STEPS) - 1))]
    big = min(S.SIZES[-1].get(k, 300) / 1500, 1.0)
    if k in S.DONOR:
        # torn off its donor: a swell of filtered noise, then the bell
        Ls = int(1.2 * SR)
        ts_ = np.arange(Ls) / SR
        sw = bandpass(rng.standard_normal(Ls), 300, 2500) * np.sin(np.pi * ts_ / 1.2) ** 2
        sweep = np.sin(2 * np.pi * np.cumsum(90 + 140 * ts_ / 1.2) / SR) * np.sin(np.pi * ts_ / 1.2) ** 2
        add("planets", max(t - 0.6, 0), sw * 0.05 + sweep * 0.08, pan)
    bell("planets", t, hz(note), (0.05 + 0.07 * big) / TOGETHER[t] ** 0.5, pan,
         decay=2.0 + 2.5 * big)

for k, f in PLANETS.DEATH.items():
    Lf = int(PLANETS.FALL / C.FPS * SR)
    tf = np.arange(Lf) / SR
    fr = 330 * np.exp(-tf * 1.2)
    g = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tf * 1.0) * (1 - np.exp(-tf * 40))
    add("planets", C.t_of(f), g, 0.5 + 0.35 * np.sin(S.PHASE[k]), 0.06)

# a faint high shimmer: space
space = bandpass(rng.standard_normal(N), 5000, 11000)
for ch in range(2):
    STEMS["planets"][:, ch] += np.roll(space, ch * 997) * 0.006

# ---------------------------------------------------------------- all three
# every release: one boom and one bell, heard everywhere
RELEASED = crowd([C.t_of(f0) for f0, _ in PLANETS.releases()], 0.75)
for f0, name in PLANETS.releases():
    t = C.t_of(f0)
    big = "rc" not in name and "beta" not in name
    boom("all", t, (0.25 if big else 0.14) / RELEASED[t] ** 0.5)
    Lb = int(2.5 * SR)
    tb = np.arange(Lb) / SR
    add("all", t, bandpass(rng.standard_normal(Lb), 3000, 9000) * np.exp(-tb * 2.5) * 0.15,
        rnd.uniform(0.4, 0.6), 0.6 if big else 0.3)
    bell("all", t + 0.02, hz(81 if big else 86), 0.07, decay=2.5)

# September: a riser into the peak, a deep boom under three bells
rise = keyed([(0, 0), (shots.film(101), 0), (BOOM - 0.05, 1), (BOOM + 0.3, 0), (SECONDS, 0)])
noise = bandpass(rng.standard_normal(N), 400, 6000)
for ch in range(2):
    STEMS["all"][:, ch] += np.roll(noise, ch * 31) * rise ** 2 * 0.09
boom("all", BOOM, 0.6, base=48, length=3.0, world=False)
bell("all", BOOM, hz(74), 0.16, 0.45, decay=5, world=False)
bell("all", BOOM + 0.02, hz(78), 0.1, 0.55, decay=5, world=False)
bell("all", BOOM + 0.04, hz(81), 0.08, 0.5, decay=5, world=False)

# ---------------------------------------------------------------- the mix
# each shot turns up the part it shows; a wide shot hears all three
FOCUS = {"canyon": (1.0, 0.3, 0.3), "city": (0.3, 1.0, 0.3),
         "planets": (0.3, 0.3, 1.0), "world": (0.75, 0.75, 0.75)}
gains = np.zeros((int(SECONDS * 20) + 1, 3))
for n in range(len(gains)):
    space_ = shots.SHOTS[shots.shot_index(n / 20)]["space"]
    space_ = "planets" if ":" in space_ else space_  # follow:<class>, under:<class>
    gains[n] = FOCUS[space_]
k = int(0.3 * 20)  # ease over 0.3 s round each cut
kernel = np.ones(k) / k
for c in range(3):
    gains[:, c] = np.convolve(np.pad(gains[:, c], (k // 2, k - k // 2 - 1), mode="edge"),
                              kernel, mode="valid")
out = STEMS["bed"] + STEMS["all"]
for c, name in enumerate(("canyon", "city", "planets")):
    g = np.interp(T, np.arange(len(gains)) / 20, gains[:, c])
    out += STEMS[name] * g[:, None]
    if name == "canyon":
        out += (RUMBLE * (0.6 + 0.4 * g))[:, None]

ir_len = int(2.6 * SR)
ti = np.arange(ir_len) / SR
wet = np.zeros_like(out)
hp = signal.butter(2, 120 / (SR / 2), btype="high")  # the lows stay out of the room
for ch in range(2):
    ir = lowpass(rng.standard_normal(ir_len) * np.exp(-ti * 3.2), 4800)
    ir /= np.sqrt(np.sum(ir ** 2))  # unit energy: about +7 dB below 4.8 kHz
    wet[:, ch] = signal.fftconvolve(signal.lfilter(*hp, out[:, ch]), ir)[:N]
mix = out * 0.8 + wet * 0.16
mix *= (np.minimum(T / 0.5, 1) * np.clip((SECONDS - T) / 6.0, 0, 1))[:, None]
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.4) / np.tanh(1.4) * 0.9

path = sys.argv[1] if len(sys.argv) > 1 else "audio.wav"
with wave.open(path, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", path, f"{SECONDS:.1f} s,", len(times), "commit pings,", len(events), "test blips,",
      len(S.ORDER), "classes,", len(PLANETS.releases()), "releases, peak at",
      round(BOOM, 2), "s")
