#!/usr/bin/env bash
# Render frames START..END in chunks; on a crash (GPU reset), a hang or a
# Python error, resume after the last frame saved.
#   ./render_chunks.sh 1 4622 [pct] [samples] [outdir]
set -u
cd "$(dirname "$0")"
start=$1 end=$2 pct=${3:-25} samples=${4:-16} out=${5:-frames} tries=0
mkdir -p "renders/$out"
have() { [ -s "renders/$out/$(printf 'f_%04d.png' "$1")" ]; }
while [ "$start" -le "$end" ]; do
  stop=$((start + 299 < end ? start + 299 : end))
  # --python-exit-code: an exception in the scene script must not pass for
  # a finished chunk; two hours is far beyond any healthy chunk
  timeout 2h ~/.local/bin/blender -b --factory-startup --python-exit-code 1 -P build_scene.py -- \
      --pct "$pct" --samples "$samples" --anim --start "$start" --end "$stop" --out "$out" \
      > renders/chunk.log 2>&1
  status=$?
  if [ "$status" -eq 0 ] && have "$stop"; then
    start=$((stop + 1)) tries=0
    continue
  fi
  last=$(grep -o "f_[0-9]*\.png" renders/chunk.log | tail -1 | tr -dc 0-9 | sed 's/^0*//')
  if [ -n "$last" ] && [ "$last" -ge "$start" ]; then
    start=$((last + 1)) tries=0   # it got somewhere: go on from there
  else
    tries=$((tries + 1))
  fi
  echo "chunk ending $stop stopped (status $status) after frame ${last:-none}, try $tries" >&2
  grep -E "Traceback|Error" renders/chunk.log | tail -3 >&2
  [ "$tries" -ge 4 ] && exit 1
done
