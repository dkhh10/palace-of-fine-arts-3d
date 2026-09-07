#!/bin/zsh
# Lead's master build: assemble master.blend, then bake the Eevee irradiance volumes into it (needs geometry).
# Usage: scripts/lead_build.sh [build_master args]
set -e
cd "$(dirname "$0")/.."
blender --background --python scripts/build_master.py -- "$@"
blender --background --python scripts/light_probes.py -- --blend master.blend --bake --save
