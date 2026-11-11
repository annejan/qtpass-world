#!/usr/bin/env bash
# Render test views of one frame: ./look.sh FRAME name=x,y,z,tx,ty,tz,lens ...
set -euo pipefail
cd "$(dirname "$0")"
f=$1; shift
pct=${PCT:-25}; samples=${SAMPLES:-8}
for v in "$@"; do
  name=${v%%=*}
  CAM=${v#*=} ~/.local/bin/blender -b --factory-startup -P build_scene.py -- \
    --stills "$f" --pct "$pct" --samples "$samples" --prefix "look-$name" 2>&1 |
    grep -E 'Error|Traceback|Saved' || true
done
