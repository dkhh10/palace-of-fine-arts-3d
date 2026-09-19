"""Phase 8b band-atlas constants and geometry (docs/briefs/phase8b_band_atlas.md, item 1).

One atlas per far-tree prototype: 12 azimuth columns x 3 elevation rows of 341 px frames on 4096 x 1024.
Everything else - the rig, the nursery, the coverage alpha, the gamma-2 encode at the prototype's own
`range`, the placement datum - is the Gate 3 octahedral bake unchanged (export/bake_lm.py `impostor`).

Why 341 is the frame PITCH and not the inner size: the contract fixes `atlas_px [4096, 1024]` and
"341 px frames ... 2x the 2K per axis". 12 x 341 = 4092 <= 4096 and 3 x 341 = 1023 <= 1024, while an
inner of 341 plus the scaled gutter would need 12 x 357 = 4284. So frame_px = 341 with the octahedral
gutter rule scaled x2 (4 -> 8) and inner = 341 - 16 = 325. inner/frame = 0.9531 against the 2K
frame's 162/170 = 0.9529: the same rule, scaled.

Direction convention (stated here, repeated in band.json, asserted by the viewer from its boot log):
  * azimuth 0 = the camera stands on the world +X axis from the tree, i.e. the view direction
    d = camera - billboard = (1, 0, 0) in BLENDER Z-up. In the octahedral map that direction is the
    +X pole, frame (col, row) = (11, 6) by `impostors.frame_lookup`.
  * azimuth increases CLOCKWISE seen from above (+Z looking down): +X -> -Y -> -X -> +Y, so
    d_xy = (cos az, -sin az).
  * In the project's compass convention (degrees clockwise from north, CLAUDE.md: -X is north,
    +Y is east/the lagoon), azimuth 0 = 180 deg (due south) and the band's azimuth index i is at
    compass 180 + 30*i.
  * elevation is measured at the BILLBOARD CENTRE (the quad centre the viewer places at
    trunk_base + (0, 0, centre_z_m * s)), positive above the horizon.
  * rows are counted from the BOTTOM of the image, exactly as `impostors.frame_lookup` counts its
    octahedral rows; row 0 = elevations_deg[0].
"""
import json
import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                   # this checkout (the phase8-bake worktree)
MAIN_ROOT = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
OUT = ROOT / "export" / "out" / "gate3"
BAND_OUT = OUT / "band"                              # written here, rsynced to MAIN by band_pack.sh
MAIN_BAND_OUT = MAIN_ROOT / "export" / "out" / "gate3" / "band"
MAIN_MANIFEST = MAIN_ROOT / "export" / "out" / "gate3" / "manifest.json"
BAND_BLEND = OUT / "band_imp.blend"                  # the nursery, rebuilt from MAIN master_delivery.blend
REC_DIR = BAND_OUT / "rec"                           # one record per prototype (the queue's resume marker)
# the shipped octahedral PNGs, read-only, for the side-by-side crop and the histogram comparison
OCTA_DIR = Path(os.environ.get(
    "PFA_OCTA_DIR",
    str(MAIN_ROOT / ".claude" / "worktrees" / "phase6-bake" / "export" / "out" / "gate3" / "impostor")))

GRID_AZ = 12
GRID_EL = 3
AZ_STEP_DEG = 360.0 / GRID_AZ                        # 30
ELEV_DEG = (0.0, 20.0, 40.0)
ATLAS_W = 4096
ATLAS_H = 1024
FRAME_PX = 341
GUTTER_PX = 8
INNER_PX = FRAME_PX - 2 * GUTTER_PX                  # 325
PAD_X = ATLAS_W - GRID_AZ * FRAME_PX                 # 4
PAD_Y = ATLAS_H - GRID_EL * FRAME_PX                 # 1
SAMPLES = 64                                         # gate3_common.SAMPLES_IMPOSTOR
ALPHA_FLOOR = 0.02                                   # bake_lm.py IMP_ALPHA_FLOOR, un-premultiply cap
AZIMUTH0_BLENDER_DIR = (1.0, 0.0, 0.0)
AZIMUTH0_COMPASS_DEG = 180.0                         # -X is north, so +X is due south

SCHEMA = "pfa-phase8b/band-atlas/1"


def png_name(proto):
    return f"band_{proto}_albedo_4096.png"


def ktx_name(proto):
    return f"band_{proto}_albedo_4096.ktx2"


def key(proto):
    """The texture key the export uses in `textures.gate3.files` / `impostors.band`."""
    return f"band_{proto}_albedo_4096"


def direction(i, j):
    """Blender Z-up world direction from the billboard centre to the camera for band cell (i, j)."""
    az = math.radians(i * AZ_STEP_DEG)
    el = math.radians(ELEV_DEG[j])
    return (math.cos(el) * math.cos(az), -math.cos(el) * math.sin(az), math.sin(el))


def cell_of(d):
    """The viewer's lookup, in python: a Blender-space direction -> (azimuth index, elevation index,
    azimuth in degrees, elevation in degrees). Nearest cell, no blend."""
    x, y, z = d
    n = math.sqrt(x * x + y * y + z * z)
    x, y, z = x / n, y / n, z / n
    az = math.degrees(math.atan2(-y, x)) % 360.0
    el = math.degrees(math.asin(max(-1.0, min(1.0, z))))
    i = int(round(az / AZ_STEP_DEG)) % GRID_AZ
    j = min(range(GRID_EL), key=lambda k: abs(ELEV_DEG[k] - el))
    return i, j, az, el


def octa_cell(d, grid=12):
    """`impostors.frame_lookup` in python: the octahedral (col, row) a direction picks."""
    x, y, z = d
    s = abs(x) + abs(y) + abs(z)
    x, y, z = x / s, y / s, z / s
    if z >= 0.0:
        u, v = x, y
    else:
        u = (1.0 - abs(y)) * (1.0 if x >= 0 else -1.0)
        v = (1.0 - abs(x)) * (1.0 if y >= 0 else -1.0)
    u01, v01 = u * 0.5 + 0.5, v * 0.5 + 0.5
    return int(math.floor(u01 * (grid - 1) + 0.5)), int(math.floor(v01 * (grid - 1) + 0.5))


def frame_slice(i, j):
    """(y0, y1, x0, x1) of cell (i, j) in the BOTTOM-UP atlas array, gutters included."""
    y0, x0 = j * FRAME_PX, i * FRAME_PX
    return y0, y0 + FRAME_PX, x0, x0 + FRAME_PX


def inner_slice(i, j):
    """The same frame without its gutter - what the viewer samples."""
    y0, y1, x0, x1 = frame_slice(i, j)
    return y0 + GUTTER_PX, y1 - GUTTER_PX, x0 + GUTTER_PX, x1 - GUTTER_PX


def manifest_impostors(path=None):
    m = json.loads(Path(path or MAIN_MANIFEST).read_text())
    return m["impostors"]


FRAME_LOOKUP = (
    "d = normalize(camera_pos - billboard_pos) in BLENDER Z-up (from a three.js dir with (x, -z, y)); "
    "az_deg = degrees(atan2(-d.y, d.x)) mod 360 (azimuth 0 = +X, increasing CLOCKWISE seen from above); "
    "el_deg = degrees(asin(clamp(d.z, -1, 1))) at the BILLBOARD CENTRE; "
    "i = round(az_deg / 30) mod 12; the two nearest columns are i0 = floor(az_deg/30) mod 12 and "
    "(i0 + 1) mod 12 with w = fract(az_deg/30), blended linearly in angle; "
    "row j = the nearest of elevations_deg, clamped (the band carries no negative elevation)."
)
FRAME_UV = (
    "u = (i*frame_px + gutter_px + f.x*inner_px) / atlas_px[0]; "
    "v_from_bottom = (j*frame_px + gutter_px + f.y*inner_px) / atlas_px[1]; "
    "clamp f to [0,1] and inset by half a texel. Rows are counted from the BOTTOM of the image, "
    "exactly as impostors.frame_lookup counts the octahedral rows."
)
