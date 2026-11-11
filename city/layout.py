"""Where everything stands in town: one block per suite, spiralling out from
the first suite (util) in order of birth, and the streets between them.
Shared by build_scene.py, traffic.py and topview.py. Plain Python, no bpy."""
import math
import random

from . import timeline as TL

SPACING = 11.0   # one block per suite
FH = 0.8         # floor height
RINGS = 4        # streets run round the outermost ring of blocks


def spiral(n):
    """Grid cells from the centre outwards: (0,0), then ring by ring."""
    cells = [(0, 0)]
    r = 1
    while len(cells) < n:
        ring = [(x, y) for x in range(-r, r + 1) for y in range(-r, r + 1)
                if max(abs(x), abs(y)) == r]
        ring.sort(key=lambda c: (math.atan2(c[1], c[0]) + 2 * math.pi + 1.2) % (2 * math.pi))
        cells += ring
        r += 1
    return cells[:n]


CELLS = spiral(len(TL.SUITES))


def side_of(suite):
    """Windows per facade per floor: big suites get a wider tower."""
    return int(min(max(round(math.sqrt(max(TL.PEAK[suite], 1)) / 4), 1), 3))


def width_of(suite):
    return side_of(suite) * 0.9 + 0.5


def xy_of(i):
    rnd = random.Random(i)
    cx, cy = CELLS[i]
    return (cx * SPACING + rnd.uniform(-1.5, 1.5), cy * SPACING + rnd.uniform(-1.5, 1.5))


def street(k):
    """The k-th street line (k = -RINGS .. RINGS-1), between blocks."""
    return (k + 0.5) * SPACING
