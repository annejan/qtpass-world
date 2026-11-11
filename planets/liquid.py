"""Planets that touch run together like drops: a class split off another
buds out of it and pinches off, and planets passing on neighbouring orbits
merge for a moment.

The surface is a smooth union of the spheres' distance fields:
sum_i exp(-d_i / k_i) = 1, with d_i the distance to sphere i and k_i its
softness. Every planet keeps its own mesh, bands and colour: each vertex
moves along its ray from the planet's centre onto that surface. Past the
seam, where a neighbour's term is the larger one, it dives under the
surface instead, so each planet shows on its own side and the meshes
overlap out of sight rather than meeting edge to edge (their vertices do
not line up). The normals come from the field itself, so the shading runs
across the seam unbroken.
"""
import numpy as np

SOFT = 0.22     # softness of a planet, as a share of its radius
REACH = 6.0     # softnesses beyond which a neighbour is not felt
STEPS = 40      # samples along each ray, then bisection
DIVE = 0.6      # how steeply a surface dives once it is past its seam


def softness(r):
    return SOFT * r + 0.02


class Liquid:
    def __init__(self, planets):
        self.planets = planets
        self.base = {}
        for p in planets:
            me = p.ob.data
            co = np.empty(len(me.vertices) * 3, dtype=np.float32)
            me.vertices.foreach_get("co", co)
            self.base[p.k] = co.reshape(-1, 3).astype(np.float64)  # the unit sphere
        self.bent = set()

    def update(self):
        """After every planet has its place, size and spin for the frame."""
        live = [p for p in self.planets if not p.ob.hide_render and p.ob.scale[0] > 0.01]
        c = np.array([p.ob.location for p in live], dtype=np.float64).reshape(-1, 3)
        r = np.array([p.ob.scale[0] for p in live], dtype=np.float64)
        k = softness(r)
        for i, p in enumerate(live):
            dist = np.linalg.norm(c - c[i], axis=1)
            near = np.nonzero((dist < r + r[i] + REACH * np.maximum(k, k[i]))
                              & (np.arange(len(live)) != i))[0]
            if len(near):
                self.bend(p, c[i], r[i], k[i], c[near], r[near], k[near])
                self.bent.add(p.k)
            elif p.k in self.bent:
                self.reset(p)
        for p in self.planets:
            if p.k in self.bent and p not in live:
                self.reset(p)

    def reset(self, p):
        base = self.base[p.k]
        me = p.ob.data
        me.vertices.foreach_set("co", base.astype(np.float32).ravel())
        me.normals_split_custom_set_from_vertices(base.tolist())
        me.update()
        self.bent.discard(p.k)

    def bend(self, p, c, r, k, cn, rn, kn):
        base = self.base[p.k]
        rot = np.array(p.ob.rotation_euler.to_matrix())
        rays = base @ rot.T  # the vertices' directions, in the system's frame

        def field(t):
            """(field, ownership) at distance t along every ray: the field is
            negative inside the drop, the ownership where this planet's
            term is the largest."""
            pts = c + rays * t[:, None]
            own = (t - r) / k
            others = (np.linalg.norm(pts[:, None, :] - cn[None, :, :], axis=2) - rn) / kn
            total = np.exp(-own) + np.exp(-others).sum(axis=1)
            return -np.log(total), own - others.min(axis=1)

        n = len(rays)
        far = r + 3.0 * k
        lo, hi = np.zeros(n), np.full(n, far)
        found = np.zeros(n, dtype=bool)
        for s in range(1, STEPS + 1):
            t = np.full(n, far * s / STEPS)
            f, _ = field(t)
            out = (f >= 0) & ~found
            hi[out] = t[out]
            found |= out
            lo[~found] = t[~found]
        for _ in range(14):
            mid = (lo + hi) / 2
            f, _ = field(mid)
            inside = f < 0
            lo[inside] = mid[inside]
            hi[~inside] = mid[~inside]
        t = (lo + hi) / 2
        _, o = field(t)
        t = np.maximum(t - DIVE * k * np.clip(o, 0.0, 4.0), 0.0)
        pts = c + rays * t[:, None]
        # the field's gradient: every sphere pushes outwards, by its weight
        grad = np.exp(-(t - r) / k)[:, None] / k * rays
        for j in range(len(cn)):
            v = pts - cn[j]
            d = np.linalg.norm(v, axis=1)
            grad += (np.exp(-(d - rn[j]) / kn[j]) / kn[j] / np.maximum(d, 1e-9))[:, None] * v
        grad /= np.maximum(np.linalg.norm(grad, axis=1), 1e-9)[:, None]
        me = p.ob.data
        me.vertices.foreach_set("co", (base * (t / r)[:, None]).astype(np.float32).ravel())
        me.normals_split_custom_set_from_vertices((grad @ rot).tolist())
        me.update()
