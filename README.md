# QtPass, one world

Watch the film (4K, 3:12): <https://youtu.be/R2otmal-P-A>

Three films about [QtPass](https://qtpass.org) as one place, on one clock.
The history is a canyon wall
([qtpass-strata](https://github.com/annejan/qtpass-strata)): every month of
code is a layer of rock, laid down by a glowing front and worn away as later
work replaces it. The tests are a city on the plain in front of it
([qtpass-city](https://github.com/annejan/qtpass-city)): every suite a tower,
every test a window that lights up as it lands. The classes are a solar
system in the sky above ([qtpass-orbits](https://github.com/annejan/qtpass-orbits)):
every class a planet, split-off classes born as moons of the class they came
from.

All three read the date from the same clock, so a release flares in the rock,
over the town and round the sun at once, and September 2026 hits all three in
the same frames. The film cuts between them and to wide shots of the whole
world, and keeps its own time: it opens on the finished world and runs
twelve years back to the first commit, sees 22 September three times over,
and all but stops the clock on the peak while the camera moves on.

## Files

- `clock.py`: the one clock (which date it is at every frame), the sky (dusk,
  night, dawn) and the 2026 eruption
- `shots.py`: where the parts stand, the shots and their cuts, which stretch
  of the world's clock each shot shows and how fast, and the titles
- `canyon/`, `city/`, `planets/`: the three scenes from their own films, each
  built under one empty so it can be placed and scaled, with their data and
  the scripts that count it
- `build_scene.py`: builds the world in Blender (sky, mist, moon, camera) and
  renders it
- `look.sh`: test views of one frame from fixed cameras
- `cards.py`: Lato title cards with the QtPass logo, as transparent PNGs
- `audio.py`: the soundtrack: one drone, and a voice per part (commit pings
  and the eruption in the canyon, test blips and fireworks in town, bells and
  swells round the sun), loudest for the part on screen
- `finish.sh`: bloom, vignette, grain, fades, titles and sound into an MP4

## Pipeline

```sh
python3 audio.py audio.wav
blender -b --factory-startup -P build_scene.py -- --stills 73,2809 --pct 25
./render_chunks.sh 1 4620 25 8 frames            # low-res, resumes after a crash
./finish.sh renders/frames qtpass-world.mp4
```

The data of each part is regenerated as in its own repository (see the
pipelines there); `canyon/prep.py`, `city/count_tests.py` and
`planets/count_files.py` are the counting scripts. All three are counted at
QtPass `acce8abde` (10 November 2026).

4620 frames at 24 fps (3:12), 3840x1608 (2.39:1) at 100 %.

Needs Blender 5.1, Python 3 with numpy, scipy, Pillow and matplotlib, and ffmpeg.
The Lato fonts come with it, in `assets/fonts/`.

## License

[REUSE](https://reuse.software) compliant; `REUSE.toml` says which file is
under which terms, the texts are in `LICENSES/`:

- the code and everything else of this film: MIT (see also `LICENSE`), so
  take it and make your own
- the Lato fonts in `assets/fonts/`: SIL Open Font License 1.1, by Łukasz
  Dziedzic
- the QtPass logo: CC0, after
  [Heart-padlock by AnonMoos](https://commons.wikimedia.org/wiki/File:Heart-padlock.svg),
  as in QtPass
- the data counted from QtPass's git history (`canyon/data/`,
  `canyon/scene_data.json`, `city/data/` and `planets/data/`):
  GPL-3.0-or-later, as QtPass itself
