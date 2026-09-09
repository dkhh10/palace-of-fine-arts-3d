#!/bin/zsh
# Lead's master build: assemble master.blend, then bake the Eevee irradiance volumes into it (needs geometry).
# Usage: scripts/lead_build.sh [build_master args]
# 2026-09-09: both runs go through scripts/blender_run.sh (registered maxima for the deadline watchdog).
set -e
cd "$(dirname "$0")/.."
scripts/blender_run.sh 1800 -- --background --python scripts/build_master.py -- "$@"
scripts/blender_run.sh 2400 -- --background --python scripts/light_probes.py -- --blend master.blend --bake --save
