"""QtPass, one world: the canyon of its history, the city of its tests in
front of it, and the solar system of its classes in the sky above, all on
one clock (clock.py).

blender -b --factory-startup -P build_scene.py -- [--stills 300,1100]
        [--anim --start N --end M] [--pct 25] [--samples 16] [--out frames]

The camera follows shots.py; CAM=x,y,z,tx,ty,tz,lens overrides it for
tests.
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clock as C  # noqa: E402
import shots  # noqa: E402
from canyon import scene as canyon  # noqa: E402
from city import scene as city  # noqa: E402
from planets import scene as planets  # noqa: E402

FPS, FRAMES = C.FPS, C.FRAMES

# Where everything stands: see shots.py.
CITY_AT, CITY_SCALE = shots.CITY_AT, shots.CITY_SCALE
PLANETS_AT, PLANETS_TILT, PLANETS_SCALE = shots.PLANETS_AT, shots.PLANETS_TILT, shots.PLANETS_SCALE


def node(nt, kind, loc, **props):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n


# ---------------------------------------------------------------- the sky

def setup_world():
    """Twilight from a sun just under the horizon at the first commit, night
    and stars from 2016 on, and the first light of dawn at the end."""
    s = bpy.context.scene
    w = bpy.data.worlds.new("Sky")
    s.world = w
    nt = w.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputWorld", (900, 0))
    bg = node(nt, "ShaderNodeBackground", (700, 0))
    sky = node(nt, "ShaderNodeTexSky", (-150, 250), sky_type="MULTIPLE_SCATTERING")
    for prop, val in (("sun_disc", False), ("air_density", 1.4),
                      ("aerosol_density", 2.5), ("dust_density", 2.5)):
        if hasattr(sky, prop):
            setattr(sky, prop, val)
    twi = node(nt, "ShaderNodeMix", (150, 150), data_type="RGBA", blend_type="MULTIPLY")
    twi.inputs["Factor"].default_value = 1.0
    nt.links.new(sky.outputs["Color"], twi.inputs["A"])
    sky_level = node(nt, "ShaderNodeValue", (-150, 0))
    sky_level.label = "twilight"
    comb = node(nt, "ShaderNodeCombineColor", (0, 0))
    for i in range(3):
        nt.links.new(sky_level.outputs[0], comb.inputs[i])
    nt.links.new(comb.outputs[0], twi.inputs["B"])
    # stars: sparse Voronoi points on the view direction, above the horizon
    tc = node(nt, "ShaderNodeTexCoord", (-900, -300))
    vor = node(nt, "ShaderNodeTexVoronoi", (-650, -300))
    vor.inputs["Scale"].default_value = 420.0
    nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
    pt = node(nt, "ShaderNodeMapRange", (-450, -300))
    pt.inputs["From Min"].default_value = 0.0
    pt.inputs["From Max"].default_value = 0.09
    pt.inputs["To Min"].default_value = 1.0
    pt.inputs["To Max"].default_value = 0.0
    nt.links.new(vor.outputs["Distance"], pt.inputs["Value"])
    bright = node(nt, "ShaderNodeMath", (-280, -300), operation="POWER")
    bright.inputs[1].default_value = 6.0
    nt.links.new(pt.outputs["Result"], bright.inputs[0])
    tw = node(nt, "ShaderNodeMath", (-120, -360), operation="MULTIPLY")
    nt.links.new(bright.outputs["Value"], tw.inputs[0])
    nt.links.new(vor.outputs["Color"], tw.inputs[1])  # varied brightness
    sep = node(nt, "ShaderNodeSeparateXYZ", (-650, -520))
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    hz = node(nt, "ShaderNodeMapRange", (-450, -520))
    hz.inputs["From Min"].default_value = 0.02
    hz.inputs["From Max"].default_value = 0.2
    nt.links.new(sep.outputs["Z"], hz.inputs["Value"])
    star = node(nt, "ShaderNodeMath", (40, -400), operation="MULTIPLY")
    nt.links.new(tw.outputs["Value"], star.inputs[0])
    nt.links.new(hz.outputs["Result"], star.inputs[1])
    star_level = node(nt, "ShaderNodeValue", (40, -560))
    star_level.label = "stars"
    lv = node(nt, "ShaderNodeMath", (220, -450), operation="MULTIPLY")
    nt.links.new(star.outputs["Value"], lv.inputs[0])
    nt.links.new(star_level.outputs[0], lv.inputs[1])
    lv2 = node(nt, "ShaderNodeMath", (380, -450), operation="MULTIPLY")
    lv2.inputs[1].default_value = 30.0
    nt.links.new(lv.outputs["Value"], lv2.inputs[0])
    # the night: a deep blue floor under everything
    night = node(nt, "ShaderNodeMix", (380, 150), data_type="RGBA", blend_type="ADD")
    night.inputs["Factor"].default_value = 1.0
    nt.links.new(twi.outputs["Result"], night.inputs["A"])
    night.inputs["B"].default_value = (0.006, 0.01, 0.026, 1)
    add = node(nt, "ShaderNodeMix", (550, 100), data_type="RGBA", blend_type="ADD")
    add.inputs["Factor"].default_value = 1.0
    nt.links.new(night.outputs["Result"], add.inputs["A"])
    nt.links.new(lv2.outputs["Value"], add.inputs["B"])
    nt.links.new(add.outputs["Result"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.25
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    # the sun: just set at the first commit, far below by 2016, and
    # climbing back towards the horizon at the end
    for f in range(1, FRAMES + 2, 6):
        t = C.t_of(f)
        d, dw = C.dusk(t), C.dawn(t)
        el = -1.5 - 16 * (1 - d) + 15.5 * dw
        az = -70 + 140 * dw  # sets in the west, rises in the east
        sky.sun_elevation = math.radians(el)
        sky.sun_rotation = math.radians(az + 180)
        sky.keyframe_insert("sun_elevation", frame=f)
        sky.keyframe_insert("sun_rotation", frame=f)
        sky_level.outputs[0].default_value = 3.0 * max(d, dw)
        sky_level.outputs[0].keyframe_insert("default_value", frame=f)
        star_level.outputs[0].default_value = 1.0 - 0.75 * max(d, dw)
        star_level.outputs[0].keyframe_insert("default_value", frame=f)


def setup_moon():
    """Cold light from the plain onto the wall face."""
    s = bpy.context.scene
    md = bpy.data.lights.new("Moon", "SUN")
    md.color = (0.55, 0.66, 1.0)
    md.angle = math.radians(0.6)
    moon = bpy.data.objects.new("Moon", md)
    moon.rotation_euler = (math.radians(55), 0, math.radians(-25))
    s.collection.objects.link(moon)
    for f in range(1, FRAMES + 2, 6):
        t = C.t_of(f)
        md.energy = 0.6 + 1.4 * (1 - C.dusk(t))
        md.keyframe_insert("energy", frame=f)
    return moon


def build_mist():
    """Ground mist over the plain and the canyon floor, thin above."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(110, 150, 70))
    box = bpy.context.active_object
    box.name = "Mist"
    box.scale = (1700, 1700, 140)
    box.visible_shadow = False
    m = bpy.data.materials.new("Mist")
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (600, 0))
    vol = node(nt, "ShaderNodeVolumePrincipled", (350, 0))
    vol.inputs["Color"].default_value = (0.8, 0.82, 0.9, 1)
    vol.inputs["Anisotropy"].default_value = 0.45
    tc = node(nt, "ShaderNodeNewGeometry", (-500, 0))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-300, 0))
    nt.links.new(tc.outputs["Position"], sep.inputs["Vector"])
    k = node(nt, "ShaderNodeMath", (-120, 0), operation="MULTIPLY")
    k.inputs[1].default_value = -0.12
    nt.links.new(sep.outputs["Z"], k.inputs[0])
    ex = node(nt, "ShaderNodeMath", (40, 0), operation="EXPONENT")
    nt.links.new(k.outputs["Value"], ex.inputs[0])
    dens = node(nt, "ShaderNodeMath", (200, 0), operation="MULTIPLY")
    dens.inputs[1].default_value = 0.012
    nt.links.new(ex.outputs["Value"], dens.inputs[0])
    haze = node(nt, "ShaderNodeMath", (280, -150), operation="ADD")
    haze.inputs[1].default_value = 0.0003
    nt.links.new(dens.outputs["Value"], haze.inputs[0])
    nt.links.new(haze.outputs["Value"], vol.inputs["Density"])
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    box.data.materials.append(m)
    return box


# ---------------------------------------------------------------- camera

class Camera:
    def __init__(self):
        s = bpy.context.scene
        cd = bpy.data.cameras.new("Cam")
        cd.sensor_width = 36
        cd.clip_start = 0.02
        cd.clip_end = 3000
        self.ob = bpy.data.objects.new("Cam", cd)
        s.collection.objects.link(self.ob)
        s.camera = self.ob
        self.tgt = bpy.data.objects.new("Target", None)
        s.collection.objects.link(self.tgt)
        tr = self.ob.constraints.new("TRACK_TO")
        tr.target = self.tgt
        tr.track_axis = "TRACK_NEGATIVE_Z"
        tr.up_axis = "UP_Y"
        tr.use_target_z = True  # the target's rotation sets the roll
        cd.dof.focus_object = self.tgt

    def set(self, f):
        v = shots.camera(f)
        if os.environ.get("CAM"):  # x,y,z,tx,ty,tz,lens: a fixed view for tests
            c = [float(x) for x in os.environ["CAM"].split(",")]
            v = dict(v, cam=tuple(c[0:3]), tgt=tuple(c[3:6]), lens=c[6], fstop=0,
                     roll=float(os.environ.get("ROLL", 0)))
        cd = self.ob.data
        self.ob.location = v["cam"]
        self.tgt.location = v["tgt"]
        # planet shots: up is the system's own up, so its orbits lie level
        self.tgt.rotation_euler = (math.radians(PLANETS_TILT) * v["roll"], 0, 0)
        cd.lens = v["lens"]
        cd.dof.use_dof = v["fstop"] > 0
        if v["fstop"] > 0:
            cd.dof.aperture_fstop = v["fstop"]
        bpy.context.scene.view_settings.exposure = v.get("exposure", 0.0)
        return v


# ---------------------------------------------------------------- render

def setup_render(pct, samples):
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.render.resolution_x, s.render.resolution_y = 3840, 1608
    s.render.resolution_percentage = pct
    s.render.fps = FPS
    s.frame_start, s.frame_end = 1, FRAMES
    ee = s.eevee
    ee.taa_render_samples = samples
    for prop, val in (("use_raytracing", True), ("use_shadows", True),
                      ("shadow_pool_size", "1024"),
                      ("volumetric_end", 800.0), ("volumetric_tile_size", "4"),
                      ("volumetric_samples", 128), ("volumetric_sample_distribution", 0.85),
                      ("use_volumetric_shadows", True)):
        if hasattr(ee, prop):
            try:
                setattr(ee, prop, val)
            except Exception as e:  # enum names shift between versions
                print("skip", prop, e)
    vs = s.view_settings
    vs.view_transform = "AgX"
    for look in ("AgX - Punchy", "Punchy"):
        try:
            vs.look = look
            break
        except TypeError:
            pass


class World:
    def __init__(self):
        setup_world()
        self.moon = setup_moon()
        build_mist()
        self.camera = Camera()
        canyon.FLARE = shots.FIRST_COMMIT_FLARE
        self.canyon = canyon.Canyon(scale=shots.CANYON_SCALE)
        self.city = city.City(CITY_AT, CITY_SCALE)
        self.planets = planets.Planets(self.camera.ob, PLANETS_AT,
                                       (math.radians(PLANETS_TILT), 0, 0), PLANETS_SCALE)
        # the moon and the canyon's lamps light the ground, not the sky
        keep_off = bpy.data.collections.new("Not the planets")
        keep_off.children.link(self.planets.bodies)
        for ob in bpy.data.objects:
            if ob.type == "LIGHT" and ob.name != "Sunlight":
                ob.light_linking.receiver_collection = keep_off
        for c in keep_off.collection_children:
            c.light_linking.link_state = "EXCLUDE"

    def update(self, f):
        """Film frame f: the camera follows the film, the world shows the
        moment of its own clock that the shot asks for."""
        v = self.camera.set(f)
        w = v["world"]
        s = bpy.context.scene
        s.frame_set(int(w), subframe=w - int(w))  # keyed lamps and fades
        self.canyon.update(w, v.get("releases", True))
        self.city.update(w, v["calm"], v["sweep"])
        self.planets.update(w, v["cam"], v.get("labels", 1.0), v["calm"])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"pct": 25, "stills": "", "anim": False, "samples": 16,
            "start": 1, "end": shots.FILM_FRAMES, "out": "frames", "save": "",
            "prefix": "still"}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k == "anim":
            opts["anim"] = True
            i += 1
        else:
            opts[k] = argv[i + 1]
            i += 2
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_render(int(opts["pct"]), int(opts["samples"]))
    w = World()
    s = bpy.context.scene

    def render(f, path):
        w.update(f)
        s.render.filepath = path
        bpy.ops.render.render(write_still=True)

    if opts["save"]:
        f = int(opts["stills"].split(",")[0]) if opts["stills"] else 1
        w.update(f)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, opts["save"]))
    for f in [int(v) for v in opts["stills"].split(",") if v]:
        render(f, os.path.join(HERE, "renders", f"{opts['prefix']}_{f:04d}.png"))
    if opts["anim"]:
        s.render.image_settings.file_format = "PNG"
        for f in range(int(opts["start"]), int(opts["end"]) + 1):
            render(f, os.path.join(HERE, "renders", opts["out"], f"f_{f:04d}.png"))


main()
