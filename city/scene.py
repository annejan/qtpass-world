"""The city: QtPass in tests, every test suite a tower and every test a
window that lights up green the moment the test lands on main (from
qtpass-city).

City(...) builds it under one empty; update(frame) sets every tower,
window, sign, searchlight (CI workflows), firework (releases) and light
snake (commits) from timeline.py.
"""
import math
import os
import random

import bpy
import numpy as np

from . import timeline as TL
from . import traffic

COLLECTION = None  # everything in town, under ROOT
ROOT = None
LIGHT = 1.0        # lamp energy for the city's scale (inverse square)


def link(ob):
    COLLECTION.objects.link(ob)
    if ob is not ROOT and ob.parent is None:
        ob.parent = ROOT
    return ob

FPS, FRAMES = TL.FPS, TL.FRAMES
LATO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets",
                    "fonts", "Lato-Bold.ttf")
FH = 0.8          # floor height
SPACING = 11.0    # one block per suite
PASS = (0.3, 1.0, 0.45)


def node(nt, kind, loc, **props):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n


def new_mesh(name, verts, faces, attrs=None, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    for key, vals in (attrs or {}).items():
        a = me.attributes.new(key, "FLOAT", "POINT")
        a.data.foreach_set("value", np.asarray(vals, dtype=np.float32))
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if mat:
        me.materials.append(mat)
    return ob


def emission_material(name, rgb, strength):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (300, 0))
    em = node(nt, "ShaderNodeEmission", (0, 0))
    em.inputs["Color"].default_value = (*rgb, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    return m, em


def principled(name, rgb, rough, metal=0.0):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def hue(i, n):
    """A neon colour per suite, spread round the wheel, never green (that is
    the colour of a passing test)."""
    h = (0.45 + 0.8 * (i * 0.618034 % 1.0)) % 1.0
    if 0.22 < h < 0.42:
        h += 0.2
    import colorsys
    return colorsys.hsv_to_rgb(h, 0.75, 1.0)


# ---------------------------------------------------------------- layout

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


class Tower:
    def __init__(self, i, suite, cell):
        self.suite = suite
        n = max(TL.PEAK[suite], 1)
        self.side = int(min(max(round(math.sqrt(n) / 4), 1), 3))
        self.wpf = 4 * self.side
        w = self.side * 0.9 + 0.5
        self.w = w
        rnd = random.Random(i)
        x = cell[0] * SPACING + rnd.uniform(-1.5, 1.5)
        y = cell[1] * SPACING + rnd.uniform(-1.5, 1.5)
        self.xy = (x, y)
        self.rgb = hue(i, len(TL.SUITES))

        # the body: a box from z 0 to 1, scaled to its height
        hw = w / 2
        v = [(-hw, -hw, 0), (hw, -hw, 0), (hw, hw, 0), (-hw, hw, 0),
             (-hw, -hw, 1), (hw, -hw, 1), (hw, hw, 1), (-hw, hw, 1)]
        f = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)]
        self.body = new_mesh(f"Body {suite}", v, f, mat=body_material(suite, self.rgb))
        self.body.location = (x, y, 0)

        # corner neon strips, scaled with the body
        strips, sf = [], []
        t = 0.06
        for cx, cy in ((-hw, -hw), (hw, -hw), (hw, hw), (-hw, hw)):
            b = len(strips)
            ox, oy = (t if cx < 0 else -t), (t if cy < 0 else -t)
            strips += [(cx - ox * 0.2, cy - oy * 0.2, 0), (cx + ox, cy - oy * 0.2, 0),
                       (cx + ox, cy - oy * 0.2, 1), (cx - ox * 0.2, cy - oy * 0.2, 1)]
            sf.append((b, b + 1, b + 2, b + 3))
        self.neon_mat, self.neon_em = emission_material(f"Neon {suite}", self.rgb, 0.0)
        self.neon = new_mesh(f"Neon {suite}", strips, sf, mat=self.neon_mat)
        self.neon.location = (x, y, 0)

        # the roof ring
        rv, rf = [], []
        o, ii = hw + 0.05, hw - 0.12
        for k, (a, b) in enumerate(((o, ii),)):
            pass
        quad = [(-o, -o), (o, -o), (o, o), (-o, o)]
        inner = [(-ii, -ii), (ii, -ii), (ii, ii), (-ii, ii)]
        for j in range(4):
            a, b = quad[j], quad[(j + 1) % 4]
            c, d = inner[(j + 1) % 4], inner[j]
            base = len(rv)
            rv += [(*a, 0), (*b, 0), (*c, 0), (*d, 0)]
            rf.append((base, base + 1, base + 2, base + 3))
        self.roof = new_mesh(f"Roof {suite}", rv, rf, mat=self.neon_mat)

        # every window it will ever have, floor by floor, round the facades
        wv, wf, idx = [], [], []
        ww, wh = 0.42, 0.44
        for k in range(n):
            fl, p = divmod(k, self.wpf)
            side, s = divmod(p, self.side)
            u = -hw + 0.25 + 0.45 + s * 0.9
            z0 = fl * FH + 0.2
            # side 0 faces -y (the camera), then round
            pts = []
            for du, dz in ((-ww / 2, 0), (ww / 2, 0), (ww / 2, wh), (-ww / 2, wh)):
                uu = u + du
                if side == 0:
                    pts.append((uu, -hw - 0.012, z0 + dz))
                elif side == 1:
                    pts.append((hw + 0.012, uu, z0 + dz))
                elif side == 2:
                    pts.append((-uu, hw + 0.012, z0 + dz))
                else:
                    pts.append((-hw - 0.012, -uu, z0 + dz))
            base = len(wv)
            wv += pts
            wf.append((base, base + 1, base + 2, base + 3))
            idx += [k] * 4
        self.win_mat, self.lit, self.height = window_material(suite)
        self.windows = new_mesh(f"Windows {suite}", wv, wf, {"idx": idx}, self.win_mat)
        self.windows.location = (x, y, 0)

        sign_mat, self.sign_em = emission_material(f"Sign {suite}", self.rgb, 0.0)
        self.sign = add_text(suite, (x, y - hw - 0.05, 1.0), 0.42, sign_mat)
        self.h = 0.0

    def update(self, frame):
        t = TL.date_at(frame)
        lit = TL.count_at(self.suite, t)
        # the height follows the floors needed, smoothed over half a second
        floors = 0.0
        for k in range(12):
            tt = TL.date_at(frame - k)
            need = math.ceil(TL.count_at(self.suite, tt) / self.wpf - 1e-6)
            floors += need
        floors /= 12
        h = floors * FH + (0.3 if floors > 0 else 0)
        on = h > 0.01
        for ob in (self.body, self.neon, self.roof, self.windows, self.sign):
            ob.hide_render = not on
        if not on:
            return
        x, y = self.xy
        self.body.scale = (1, 1, h)
        self.neon.scale = (1, 1, h)
        self.roof.location = (x, y, h + 0.005)
        self.sign.location = (x, y - self.w / 2 - 0.05, h + 0.15)
        self.lit.default_value = lit
        self.height.default_value = h
        glow = 2.0 + 4.0 * min(lit / 40, 1)
        self.neon_em.inputs["Strength"].default_value = glow * (1 + 3 * TL.pulse(TL.t_of(frame)))
        self.sign_em.inputs["Strength"].default_value = 3.0


def body_material(suite, rgb):
    """Tinted glass, so the towers behind show through, with a faint line of
    the suite's colour at every floor."""
    m = bpy.data.materials.new(f"Body {suite}")
    m.surface_render_method = "BLENDED"
    if hasattr(m, "use_transparency_overlap"):
        m.use_transparency_overlap = True
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (700, 0))
    geo = node(nt, "ShaderNodeNewGeometry", (-700, 0))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-500, 0))
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    per = node(nt, "ShaderNodeMath", (-350, 0), operation="DIVIDE")
    per.inputs[1].default_value = FH
    nt.links.new(sep.outputs["Z"], per.inputs[0])
    fr = node(nt, "ShaderNodeMath", (-200, 0), operation="FRACT")
    nt.links.new(per.outputs[0], fr.inputs[0])
    line = node(nt, "ShaderNodeMapRange", (-50, 0))
    line.inputs["From Min"].default_value = 0.0
    line.inputs["From Max"].default_value = 0.05
    line.inputs["To Min"].default_value = 1.0
    line.inputs["To Max"].default_value = 0.0
    nt.links.new(fr.outputs[0], line.inputs["Value"])
    glow = node(nt, "ShaderNodeMath", (120, 0), operation="MULTIPLY_ADD")
    glow.inputs[1].default_value = 1.2
    glow.inputs[2].default_value = 0.04
    nt.links.new(line.outputs[0], glow.inputs[0])
    b = node(nt, "ShaderNodeBsdfPrincipled", (350, 0))
    b.inputs["Base Color"].default_value = (0.01, 0.012, 0.02, 1)
    b.inputs["Roughness"].default_value = 0.12
    b.inputs["Alpha"].default_value = 0.35
    b.inputs["Emission Color"].default_value = (*rgb, 1)
    nt.links.new(glow.outputs[0], b.inputs["Emission Strength"])
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def window_material(suite):
    """Lit (green, with a white flash as it lights), dark glass, or not yet
    built (above the roof: transparent)."""
    m = bpy.data.materials.new(f"Windows {suite}")
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (900, 0))
    attr = node(nt, "ShaderNodeAttribute", (-800, 200), attribute_name="idx")
    lit = node(nt, "ShaderNodeValue", (-800, 0))
    lit.label = "lit"
    height = node(nt, "ShaderNodeValue", (-800, -200))
    height.label = "height"
    geo = node(nt, "ShaderNodeNewGeometry", (-800, -400))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-600, -400))
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    # age = lit - idx: > 0 once lit; small = just lit
    age = node(nt, "ShaderNodeMath", (-600, 100), operation="SUBTRACT")
    nt.links.new(lit.outputs[0], age.inputs[0])
    nt.links.new(attr.outputs["Fac"], age.inputs[1])
    on = node(nt, "ShaderNodeMath", (-400, 200), operation="GREATER_THAN")
    on.inputs[1].default_value = 0.0
    nt.links.new(age.outputs[0], on.inputs[0])
    # flash: 1 at the moment it lights, gone after ~8 more tests
    fl = node(nt, "ShaderNodeMapRange", (-400, 0))
    fl.inputs["From Min"].default_value = 0.0
    fl.inputs["From Max"].default_value = 1.5
    fl.inputs["To Min"].default_value = 1.0
    fl.inputs["To Max"].default_value = 0.0
    nt.links.new(age.outputs[0], fl.inputs["Value"])
    flash = node(nt, "ShaderNodeMath", (-200, 0), operation="MULTIPLY")
    nt.links.new(fl.outputs[0], flash.inputs[0])
    nt.links.new(on.outputs[0], flash.inputs[1])
    col = node(nt, "ShaderNodeMix", (0, 100), data_type="RGBA")
    col.inputs["A"].default_value = (0.08, 1.0, 0.22, 1)
    col.inputs["B"].default_value = (0.9, 1.0, 0.9, 1)
    nt.links.new(flash.outputs[0], col.inputs["Factor"])
    strength = node(nt, "ShaderNodeMath", (0, -100), operation="MULTIPLY_ADD")
    strength.inputs[1].default_value = 8.0
    strength.inputs[2].default_value = 0.55
    nt.links.new(flash.outputs[0], strength.inputs[0])
    em = node(nt, "ShaderNodeEmission", (250, 100))
    nt.links.new(col.outputs["Result"], em.inputs["Color"])
    nt.links.new(strength.outputs[0], em.inputs["Strength"])
    glass = node(nt, "ShaderNodeBsdfPrincipled", (250, -150))
    glass.inputs["Base Color"].default_value = (0.01, 0.015, 0.025, 1)
    glass.inputs["Roughness"].default_value = 0.08
    glass.inputs["Metallic"].default_value = 0.6
    mix_lit = node(nt, "ShaderNodeMixShader", (500, 0))
    nt.links.new(on.outputs[0], mix_lit.inputs[0])
    nt.links.new(glass.outputs[0], mix_lit.inputs[1])
    nt.links.new(em.outputs[0], mix_lit.inputs[2])
    # built: below the roof
    built = node(nt, "ShaderNodeMath", (-200, -400), operation="LESS_THAN")
    nt.links.new(sep.outputs["Z"], built.inputs[0])
    nt.links.new(height.outputs[0], built.inputs[1])
    tr = node(nt, "ShaderNodeBsdfTransparent", (500, -200))
    mix = node(nt, "ShaderNodeMixShader", (700, 0))
    nt.links.new(built.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(mix_lit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m, lit.outputs[0], height.outputs[0]


def add_text(body, loc, size, mat):
    cu = bpy.data.curves.new(body, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = size * 0.05
    cu.font = bpy.data.fonts.load(LATO, check_existing=True)
    cu.align_x = "CENTER"
    ob = bpy.data.objects.new("Sign " + body, cu)
    ob.location = loc
    ob.rotation_euler = (math.pi / 2, 0, 0)
    link(ob)
    cu.materials.append(mat)
    ob.visible_shadow = False
    return ob


# ---------------------------------------------------------------- the city

def build_ground():
    """Wet asphalt, with streets of sodium light between the blocks."""
    m = bpy.data.materials.new("Ground")
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (900, 0))
    tc = node(nt, "ShaderNodeTexCoord", (-900, 0))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-700, 0))
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    lines = []
    for axis, y in (("X", 150), ("Y", -150)):
        # distance to the middle of the street between blocks
        a = node(nt, "ShaderNodeMath", (-500, y), operation="ADD")
        a.inputs[1].default_value = SPACING / 2
        nt.links.new(sep.outputs[axis], a.inputs[0])
        md = node(nt, "ShaderNodeMath", (-350, y), operation="PINGPONG")
        md.inputs[1].default_value = SPACING / 2
        nt.links.new(a.outputs[0], md.inputs[0])
        line = node(nt, "ShaderNodeMapRange", (-200, y))
        line.inputs["From Min"].default_value = 0.0
        line.inputs["From Max"].default_value = 0.08
        line.inputs["To Min"].default_value = 1.0
        line.inputs["To Max"].default_value = 0.0
        nt.links.new(md.outputs[0], line.inputs["Value"])
        lines.append(line)
    both = node(nt, "ShaderNodeMath", (0, 0), operation="MAXIMUM")
    nt.links.new(lines[0].outputs[0], both.inputs[0])
    nt.links.new(lines[1].outputs[0], both.inputs[1])
    # fade the streets out with distance, so the grid has an edge
    ln = node(nt, "ShaderNodeVectorMath", (-500, -350), operation="LENGTH")
    nt.links.new(tc.outputs["Object"], ln.inputs[0])
    edge = node(nt, "ShaderNodeMapRange", (-300, -350))
    edge.inputs["From Min"].default_value = 30.0
    edge.inputs["From Max"].default_value = 70.0
    edge.inputs["To Min"].default_value = 1.0
    edge.inputs["To Max"].default_value = 0.0
    nt.links.new(ln.outputs["Value"], edge.inputs["Value"])
    street = node(nt, "ShaderNodeMath", (150, -100), operation="MULTIPLY")
    nt.links.new(both.outputs[0], street.inputs[0])
    nt.links.new(edge.outputs[0], street.inputs[1])
    self_street = node(nt, "ShaderNodeValue", (150, -300))
    self_street.label = "streets"
    st = node(nt, "ShaderNodeMath", (300, -150), operation="MULTIPLY")
    nt.links.new(street.outputs[0], st.inputs[0])
    nt.links.new(self_street.outputs[0], st.inputs[1])
    bsdf = node(nt, "ShaderNodeBsdfPrincipled", (500, 100))
    # wet asphalt in town, giving way to the canyon's sand at the edge
    sand = node(nt, "ShaderNodeMapRange", (-300, -550))
    sand.inputs["From Min"].default_value = 62.0
    sand.inputs["From Max"].default_value = 84.0
    nt.links.new(ln.outputs["Value"], sand.inputs["Value"])
    base = node(nt, "ShaderNodeMix", (300, 300), data_type="RGBA")
    base.inputs["A"].default_value = (0.012, 0.013, 0.016, 1)
    base.inputs["B"].default_value = (0.25, 0.18, 0.12, 1)
    nt.links.new(sand.outputs[0], base.inputs["Factor"])
    nt.links.new(base.outputs["Result"], bsdf.inputs["Base Color"])
    noise = node(nt, "ShaderNodeTexNoise", (-200, 350))
    noise.inputs["Scale"].default_value = 0.35
    rough = node(nt, "ShaderNodeMapRange", (0, 350))
    rough.inputs["To Min"].default_value = 0.04
    rough.inputs["To Max"].default_value = 0.45
    nt.links.new(noise.outputs["Fac"], rough.inputs["Value"])
    matte = node(nt, "ShaderNodeMix", (300, 450), data_type="FLOAT")
    nt.links.new(sand.outputs[0], matte.inputs["Factor"])
    nt.links.new(rough.outputs[0], matte.inputs["A"])
    matte.inputs["B"].default_value = 1.0
    nt.links.new(matte.outputs["Result"], bsdf.inputs["Roughness"])
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.55, 0.2, 1)
    nt.links.new(st.outputs[0], bsdf.inputs["Emission Strength"])
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    bpy.ops.mesh.primitive_plane_add(size=180)
    g = bpy.context.active_object
    g.name = "Ground"
    g.data.materials.append(m)
    return self_street.outputs[0]


class Searchlights:
    """One beam per CI workflow, sweeping the sky from the edge of town."""

    def __init__(self):
        self.beams = []
        m = bpy.data.materials.new("Beam")
        m.surface_render_method = "BLENDED"  # dithered drops what it makes transparent
        nt = m.node_tree
        nt.nodes.clear()
        out = node(nt, "ShaderNodeOutputMaterial", (700, 0))
        tc = node(nt, "ShaderNodeTexCoord", (-600, 0))
        sep = node(nt, "ShaderNodeSeparateXYZ", (-400, 0))
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        fall = node(nt, "ShaderNodeMath", (-200, 0), operation="POWER")
        inv = node(nt, "ShaderNodeMath", (-300, 100), operation="SUBTRACT")
        inv.inputs[0].default_value = 1.0
        nt.links.new(sep.outputs["Z"], inv.inputs[1])
        nt.links.new(inv.outputs[0], fall.inputs[0])
        fall.inputs[1].default_value = 3.0
        # brighter in the core of the beam (facing the camera)
        lw = node(nt, "ShaderNodeLayerWeight", (-400, -200))
        lw.inputs["Blend"].default_value = 0.85
        core = node(nt, "ShaderNodeMath", (-200, -200), operation="SUBTRACT")
        core.inputs[0].default_value = 1.0
        nt.links.new(lw.outputs["Facing"], core.inputs[1])
        a = node(nt, "ShaderNodeMath", (0, 0), operation="MULTIPLY")
        nt.links.new(fall.outputs[0], a.inputs[0])
        nt.links.new(core.outputs[0], a.inputs[1])
        self.fade = node(nt, "ShaderNodeValue", (0, -200))
        # the haze rolls in as the lens enters a beam instead of snapping on
        cam = node(nt, "ShaderNodeCameraData", (-400, -400))
        near = node(nt, "ShaderNodeMapRange", (-200, -400))
        near.inputs["From Min"].default_value = 1.0
        near.inputs["From Max"].default_value = 7.0
        nt.links.new(cam.outputs["View Distance"], near.inputs["Value"])
        fade_near = node(nt, "ShaderNodeMath", (0, -350), operation="MULTIPLY")
        nt.links.new(self.fade.outputs[0], fade_near.inputs[0])
        nt.links.new(near.outputs[0], fade_near.inputs[1])
        b = node(nt, "ShaderNodeMath", (150, 0), operation="MULTIPLY")
        nt.links.new(a.outputs[0], b.inputs[0])
        nt.links.new(fade_near.outputs[0], b.inputs[1])
        em = node(nt, "ShaderNodeEmission", (300, 100))
        em.inputs["Color"].default_value = (0.75, 0.85, 1.0, 1)
        nt.links.new(b.outputs[0], em.inputs["Strength"])
        tr = node(nt, "ShaderNodeBsdfTransparent", (300, -100))
        add = node(nt, "ShaderNodeAddShader", (500, 0))
        nt.links.new(em.outputs[0], add.inputs[0])
        nt.links.new(tr.outputs[0], add.inputs[1])
        nt.links.new(add.outputs[0], out.inputs[0])
        self.mats = []
        rnd = random.Random(12)
        for i in range(12):
            mi = m.copy()
            fade = [n for n in mi.node_tree.nodes if n.type == "VALUE"][0]
            bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.2, radius2=5.0,
                                            depth=110, end_fill_type="NOTHING",
                                            location=(0, 0, 55))
            ob = bpy.context.active_object
            ob.name = f"Beam {i}"
            # origin at the lamp
            bpy.context.scene.cursor.location = (0, 0, 0)
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
            ob.data.materials.append(mi)
            ob.visible_shadow = False
            ang = 2 * math.pi * (i * 0.381966 % 1.0)
            r = 52 + rnd.uniform(-6, 6)
            ob.location = (r * math.cos(ang), r * math.sin(ang) + 10, 0)
            self.beams.append((ob, fade.outputs[0], rnd.uniform(0, 6.28),
                               rnd.uniform(0.25, 0.45), rnd.choice((-1, 1))))

    def update(self, frame):
        t = TL.t_of(frame)
        n = TL.ci_at(TL.date_at(frame))
        for i, (ob, fade, ph, speed, sense) in enumerate(self.beams):
            on = i < n
            ob.hide_render = not on
            if not on:
                continue
            born = TL.frame_of_date(next((s["t"] for s in TL.SAMPLES if s["ci"] > i),
                                         TL.T_NOW))
            f = min(max((frame - born) / 30, 0), 1)
            fade.default_value = 0.2 * f
            tilt = math.radians(22 + 8 * math.sin(t * speed * 0.7 + ph)) * (1 - 0.9 * TL.peak(t))
            spin = ph + sense * t * speed
            # lean towards the city a little: aim at a point above it
            ob.rotation_euler = (tilt, 0, spin)


class Fireworks:
    """A burst over town for every release."""

    def __init__(self):
        rnd = random.Random(44)
        self.bursts = []
        for f0, name in TL.releases() + TL.finale():
            big = "rc" not in name and "beta" not in name
            n = 90 if big else 45
            col = [(1.0, 0.45, 0.2), (0.4, 0.7, 1.0), (1.0, 0.85, 0.35),
                   (0.95, 0.35, 0.8), (0.6, 1.0, 0.9)][rnd.randrange(5)]
            c = (rnd.uniform(-25, 25), rnd.uniform(5, 40), rnd.uniform(28, 42))
            if name == "finale":  # over util, where the camera looks up
                c = (rnd.uniform(-14, 18), rnd.uniform(4, 30), rnd.uniform(24, 36))
            dirs = []
            for _ in range(n):
                v = np.array([rnd.gauss(0, 1) for _ in range(3)])
                v /= np.linalg.norm(v) + 1e-9
                dirs.append(v * rnd.uniform(9, 13) * (1.0 if big else 0.7))
            jitter = 0 if name == "finale" else rnd.uniform(0, 4)
            self.bursts.append((f0 + jitter, np.array(c), np.array(dirs), col))
        m = bpy.data.materials.new("Spark")
        nt = m.node_tree
        nt.nodes.clear()
        out = node(nt, "ShaderNodeOutputMaterial", (400, 0))
        em = node(nt, "ShaderNodeEmission", (200, 0))
        ca = node(nt, "ShaderNodeAttribute", (-200, 100), attribute_name="Col")
        ha = node(nt, "ShaderNodeAttribute", (-200, -100), attribute_name="heat")
        mul = node(nt, "ShaderNodeMath", (0, -100), operation="MULTIPLY")
        mul.inputs[1].default_value = 40.0
        nt.links.new(ha.outputs["Fac"], mul.inputs[0])
        nt.links.new(ca.outputs["Color"], em.inputs["Color"])
        nt.links.new(mul.outputs[0], em.inputs["Strength"])
        nt.links.new(em.outputs[0], out.inputs[0])
        self.mat = m
        self.ob = None
        self.flash = bpy.data.lights.new("Burst", "POINT")
        self.flash.shadow_soft_size = 4
        self.lo = bpy.data.objects.new("Burst", self.flash)
        link(self.lo)

    def update(self, frame):
        pts, cols, heat = [], [], []
        flash, fpos, fcol = 0.0, (0, 0, 30), (1, 1, 1)
        for f0, c, dirs, col in self.bursts:
            tau = (frame - f0) / FPS
            if tau < 0 or tau > 2.6:
                continue
            k = 1.6
            p = c + dirs * (1 - math.exp(-k * tau)) / k
            p[:, 2] -= 0.5 * 4.0 * tau * tau
            life = max(1 - tau / 2.6, 0)
            for q in p:
                pts.append(q)
                cols.append(col)
                heat.append(life ** 1.5 * (0.6 + 0.4 * math.sin(frame * 1.7 + q[0])))
            e = max(1 - tau / 0.5, 0)
            if e > flash:
                flash, fpos, fcol = e, tuple(c), col
        if self.ob is not None:
            bpy.data.objects.remove(self.ob)
        self.flash.energy = 60000 * flash * LIGHT
        self.flash.color = fcol
        self.lo.location = fpos
        if not pts:
            self.ob = None
            return
        r = 0.16
        oct_v = np.array([(r, 0, 0), (-r, 0, 0), (0, r, 0), (0, -r, 0), (0, 0, r), (0, 0, -r)])
        oct_f = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
        verts, faces, vcol, vheat = [], [], [], []
        for i, q in enumerate(pts):
            verts += list(oct_v + q)
            faces += [tuple(j + 6 * i for j in f) for f in oct_f]
            vcol += [cols[i]] * 6
            vheat += [heat[i]] * 6
        me = bpy.data.meshes.new("Sparks")
        me.from_pydata([tuple(v) for v in verts], [], faces)
        ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        c4 = np.ones((len(verts), 4), dtype=np.float32)
        c4[:, :3] = vcol
        ca.data.foreach_set("color", c4.ravel())
        ha = me.attributes.new("heat", "FLOAT", "POINT")
        ha.data.foreach_set("value", np.asarray(vheat, dtype=np.float32))
        me.materials.append(self.mat)
        self.ob = bpy.data.objects.new("Sparks", me)
        self.ob.visible_shadow = False
        link(self.ob)


class Traffic:
    """The commits as light snakes on the streets (traffic.py): a tapered tube
    per snake with a white-hot rounded head, the colour of its commit's kind
    along the body, fading to the tail."""

    def __init__(self):
        m = bpy.data.materials.new("Snake")
        nt = m.node_tree
        nt.nodes.clear()
        out = node(nt, "ShaderNodeOutputMaterial", (400, 0))
        em = node(nt, "ShaderNodeEmission", (200, 0))
        ca = node(nt, "ShaderNodeAttribute", (-200, 100), attribute_name="Col")
        ha = node(nt, "ShaderNodeAttribute", (-200, -100), attribute_name="heat")
        mul = node(nt, "ShaderNodeMath", (0, -100), operation="MULTIPLY")
        mul.inputs[1].default_value = 2.2
        nt.links.new(ha.outputs["Fac"], mul.inputs[0])
        nt.links.new(ca.outputs["Color"], em.inputs["Color"])
        nt.links.new(mul.outputs[0], em.inputs["Strength"])
        nt.links.new(em.outputs[0], out.inputs[0])
        self.mat = m
        self.ob = None

    STYLE = os.environ.get("SNAKE_STYLE", "tube")  # tube; t, capsule, wedge to compare

    def update(self, frame):
        if self.ob is not None:
            bpy.data.objects.remove(self.ob)
            self.ob = None
        verts, faces, cols, heat = [], [], [], []
        half = 0.2

        def sphere(cx, cy, cz, r, c, h, rings=5, segs=10):
            base = len(verts)
            for a in range(rings + 1):
                th = math.pi * a / rings
                for b in range(segs):
                    ph = 2 * math.pi * b / segs
                    verts.append((cx + r * math.sin(th) * math.cos(ph),
                                  cy + r * math.sin(th) * math.sin(ph), cz + r * math.cos(th)))
                    cols.append(c)
                    heat.append(h)
            for a in range(rings):
                for b in range(segs):
                    p0 = base + a * segs + b
                    p1 = base + a * segs + (b + 1) % segs
                    faces.append((p0, p1, p1 + segs, p0 + segs))

        for pts, glow, kind in traffic.snakes(frame):
            if len(pts) < 2:
                continue
            rgb = np.array(traffic.COLOURS[kind])
            n = len(pts)
            prof = []  # (x, y, tx, ty, half width, fin height, colour, heat)
            for k, (x, y) in enumerate(pts):
                a = pts[max(k - 1, 0)]
                b = pts[min(k + 1, n - 1)]
                dx, dy = a[0] - b[0], a[1] - b[1]  # forward: towards the head
                ln = math.hypot(dx, dy) or 1.0
                tx, ty = dx / ln, dy / ln
                u = k / (n - 1)
                w = max(1 - u * 12, 0)
                c = w * np.ones(3) + (1 - w) * rgb * (1 - 0.4 * u)
                h = glow * (1 - 0.85 * u) * (1.6 if k == 0 else 1.0)
                prof.append([x, y, tx, ty, half, 0.32 * (1 - 0.6 * u), c, h])
            hx, hy, htx, hty = prof[0][:4]
            if self.STYLE == "wedge":
                # an arrowhead: wider at the head, coming to a point ahead
                prof[0][4] = half * 1.9
                prof[0][5] = 0.42
                tip = [hx + htx * 0.75, hy + hty * 0.75, htx, hty, 0.0, 0.05,
                       np.ones(3), prof[0][7]]
                prof.insert(0, tip)
            if self.STYLE == "tube":
                ring = 12
                base = len(verts)
                for k, (x, y, tx, ty, _, _, c, h) in enumerate(prof):
                    r = 0.2 * (1 - 0.75 * k / (len(prof) - 1))
                    nx, ny = -ty, tx
                    for q in range(ring):
                        an = 2 * math.pi * q / ring
                        verts.append((x + nx * r * math.cos(an), y + ny * r * math.cos(an),
                                      0.05 + r + r * math.sin(an)))
                        cols.append(c)
                        heat.append(h)
                    if k:
                        for q in range(ring):
                            p0 = base + (k - 1) * ring + q
                            p1 = base + (k - 1) * ring + (q + 1) % ring
                            faces.append((p0, p1, p1 + ring, p0 + ring))
                sphere(hx, hy, 0.25, 0.2, np.ones(3), prof[0][7] * 1.6, 4, 8)  # the cap
                continue
            base = len(verts)
            for k, (x, y, tx, ty, hw, fin, c, h) in enumerate(prof):
                nx, ny = -ty * hw, tx * hw
                # a ribbon on the road and a low fin, so it reads from the street too
                verts += [(x + nx, y + ny, 0.05), (x - nx, y - ny, 0.05),
                          (x, y, 0.05), (x, y, fin)]
                cols += [c, c, c, c]
                heat += [h, h, h, h * 0.8]
                if k:
                    i = base + 4 * (k - 1)
                    faces.append((i, i + 1, i + 5, i + 4))
                    faces.append((i + 2, i + 3, i + 7, i + 6))
            if self.STYLE == "capsule":
                sphere(hx + htx * 0.1, hy + hty * 0.1, 0.26, 0.26,
                       0.6 * np.ones(3) + 0.4 * rgb, prof[0][7] * 1.3)
        if not faces:
            return
        me = bpy.data.meshes.new("Snakes")
        me.from_pydata(verts, [], faces)
        ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        c4 = np.ones((len(verts), 4), dtype=np.float32)
        c4[:, :3] = cols
        ca.data.foreach_set("color", c4.ravel())
        ha = me.attributes.new("heat", "FLOAT", "POINT")
        ha.data.foreach_set("value", np.asarray(heat, dtype=np.float32))
        me.materials.append(self.mat)
        self.ob = bpy.data.objects.new("Snakes", me)
        self.ob.visible_shadow = False
        link(self.ob)


class City:
    def __init__(self, location, scale):
        global COLLECTION, ROOT, LIGHT
        COLLECTION = bpy.data.collections.new("City")
        bpy.context.scene.collection.children.link(COLLECTION)
        ROOT = link(bpy.data.objects.new("City", None))
        ROOT.location = location
        ROOT.scale = [scale] * 3
        LIGHT = scale * scale
        before = set(bpy.context.scene.collection.objects)
        self.streets = build_ground()
        cells = spiral(len(TL.SUITES))
        self.towers = [Tower(i, s, cells[i]) for i, s in enumerate(TL.SUITES)]
        self.beams = Searchlights()
        self.fireworks = Fireworks()
        self.traffic = Traffic()
        # what bpy.ops added went to the scene: bring it into town
        for ob in set(bpy.context.scene.collection.objects) - before:
            bpy.context.scene.collection.objects.unlink(ob)
            link(ob)

    def update(self, f):
        t = TL.t_of(f)
        for tw in self.towers:
            tw.update(f)
        self.beams.update(f)
        self.fireworks.update(f)
        self.traffic.update(f)
        # the streets light up with the city
        total = TL.total_at(TL.date_at(f))
        self.streets.default_value = (0.08 + 0.9 * min(total / 400, 1)) * (1 + 4 * TL.pulse(t))
