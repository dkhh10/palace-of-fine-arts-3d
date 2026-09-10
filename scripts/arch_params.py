"""Architectural parameters for the Palace of Fine Arts rotunda + colonnades. ALL VALUES IN METRES.

Source of every number: docs/reference_sheet.md (sections 2b, 3b, 3c) unless marked DERIVED, in which case the derivation is
written in docs/arch_notes.md. World frame: origin = rotunda floor centre, z=0 = rotunda floor, +Y east (lagoon), -X north.
Compass azimuth az (deg clockwise from north) maps to world (X, Y) = (-r*cos(az), r*sin(az)).
"""
import math
import os
from pathlib import Path

# ----------------------------------------------------------------------------- site levels
FLOOR_Z = 0.0            # rotunda floor slab
GROUND_Z = -0.6          # peninsula lawn / path around the rotunda (sheet section 1)
WATER_Z = -1.3           # lagoon surface (common.WATER_Z)
COLONNADE_GROUND_Z = -0.6  # gravel floor of the colonnade (sheet: colonnade heights are "above ground")

# ----------------------------------------------------------------------------- rotunda plan (section 3)
FACE_AZ0 = 82.0          # compass azimuth of face-0 normal (lagoon face); faces at FACE_AZ0 + 45k
VERTEX_AZ0 = FACE_AZ0 - 22.5   # 59.5: pier axes at VERTEX_AZ0 + 45k
WALL_APOTHEM = 21.5      # outer face of the arch wall (also the attic panel face)
WALL_THICKNESS = 2.0     # DERIVED: arch wall from apothem 19.5 to 21.5
INNER_APOTHEM = WALL_APOTHEM - WALL_THICKNESS
WALL_CIRCUMRADIUS = WALL_APOTHEM / math.cos(math.radians(22.5))   # 23.27
FACE_LENGTH = 2 * WALL_APOTHEM * math.tan(math.radians(22.5))    # 17.81
ARCH_SPAN = 12.5         # clear span of the outer arches (section 2b)
ARCH_SPRING_Z = 17.5     # springing line
ARCH_CROWN_Z = ARCH_SPRING_Z + ARCH_SPAN / 2   # 23.75 (sheet: 23.7)
PIER_WALL = (FACE_LENGTH - ARCH_SPAN) / 2       # 2.65 m of pier each side of the arch at the wall
COL_D_ALONG = 1.9        # column axis: distance along the face from the vertex
COL_O_OUT = 1.3          # column axis: distance outside the wall plane
RESSAUT_ALONG = 3.2      # DERIVED (085): ressaut / attic corner block meets the wall this far along each face from the vertex (block 5.9 m wide)
WEDGE_ALONG = 1.03       # DERIVED: pier wedge between the columns; chamfer face 2*1.03*cos22.5 = 1.9 m wide, clears the 2.5 m shafts
CHAMFER_CIRCUMRADIUS = 25.0   # section 3b: corner niches project to circumradius ~25.0 (the chamfer plane of the piers/ressauts)

# ----------------------------------------------------------------------------- rotunda vertical stack (section 2b, forced to apex 49.4)
PODIUM_TOP_Z = 4.3
PEDESTAL_TOP_Z = 7.5
PEDESTAL_SIZE = 3.4
COL_BASE_H = 1.0                   # plinth + torus-scotia-torus
COL_SHAFT_Z0 = PEDESTAL_TOP_Z + COL_BASE_H      # 8.5
COL_SHAFT_H = 14.46                # r6: 16.3 -> 14.46, see the round-6 note below
COL_SHAFT_Z1 = COL_SHAFT_Z0 + COL_SHAFT_H       # 22.96 (shaft top = capital socket)
COL_D_BOTTOM = 2.5
COL_D_TOP = 2.1
CAPITAL_H = 3.0                    # r6: 2.6 -> 3.0 (ref 169 capital 39 rows vs the render's 33 at 13.84 px/m)
ENTABLATURE_Z0 = COL_SHAFT_Z1 + CAPITAL_H       # 25.96
# ---------------------------------------------------------------------------------------------------------------
# ROUND 6 (QA-06-1): the courses inside the fixed envelope, registered against ref 169 on QA's round-05 alignment.
# The envelope does NOT move: ATTIC_Z1 38.30, the drum, the dome and the attic crown cornice's 0.74 m projection are
# all unchanged, so the silhouette fit (apex / corner_top / W_a) that rides on refs 169 / 085 / 063 is untouched.
# What moved, and the measurement behind each (rows are 1920x1080 cam01 rows in QA's aligned overlay,
# renders/qa_comparisons/round06_cam01_aligned_vs_ref169.png; the model's row(z, d) map is
# row = 678.81 - 13.486*z - 5.157*d, fitted on the round-5 course table to +-0.34 row):
#   entablature corona soffit   render row 254 -> ref 281  (-2.00 m)  => ENTABLATURE_Z1 31.20 -> 29.18
#   architrave bottom           render row 309 -> ref 328  (-1.44 m)  => ENTABLATURE_Z0 27.40 -> 25.96
#   attic relief field bottom   render row 241 -> ref 269  (-2.06 m)  => panel_z0 32.55 -> 30.48
#   attic relief field top      render row 180 -> ref 198  (-1.30 m)  => panel_z1 37.05 -> 35.75
#   attic cornice corona soffit render (none)  -> ref 182            => the attic crown cornice grows 0.80 -> 2.10
#                                                                       and gains a real soffit at +0.42 (it had none)
#   capital top / shaft top     render 302/334 -> ref 318/357 (13.84 px/m at the column: -1.16 / -1.71 m)
# The APPARENT heights that round 4 measured on the same photograph are preserved: the plain frieze+architrave band
# reads 28 rows in the render and 26-28 in the photo (round 4: "one plain surface, 2.02 m"), so ARCHITRAVE_H+FRIEZE_H
# only shrinks 2.05 -> 1.85; the whole entablature reads 54.7 rows against the photo's 47, hence 3.80 -> 3.22.
# QA's own table read the render's architrave fascia (row 302) as its "frieze bottom" and the drum edge (row 168) as
# the attic crown, which is why it reported the attic storey at 0.70 and the frieze at 1.00; the anchors above are
# the same physical feature in both images. Derivation and the zoomed panels in docs/arch_notes.md "Round 6".
ARCHITRAVE_H, FRIEZE_H, CORNICE_H = 1.04, 0.81, 1.37     # was 1.15 / 0.90 / 1.75 (3.80 total)
ENTABLATURE_Z1 = ENTABLATURE_Z0 + ARCHITRAVE_H + FRIEZE_H + CORNICE_H   # 29.18
CORNICE_CORONA_D = 1.66            # corona projection past the wall plane (round 4, unchanged)
CORNICE_CORONA_SOFFIT_DZ = 2.97    # corona soffit above ENTABLATURE_Z0 (was 3.48); the checks import it from here
ATTIC_Z0 = ENTABLATURE_Z1
ATTIC_H = 9.12                     # was 7.1; ATTIC_Z1 is held at 38.30
ATTIC_Z1 = ATTIC_Z0 + ATTIC_H                   # 38.30
ATTIC_BASE_MOULDING_H = 0.85   # DERIVED (085 + ref 169 r6): modillion course + Greek key band over the ressauts
ATTIC_TOP_CORNICE_H = 2.10     # DERIVED (ref 169 r6): crown cornice, soffit 1.68 m below the crown
ATTIC_CORNICE_D = 0.74         # max projection of the attic crown cornice -- HOLDS the silhouette W_a, do not raise
ATTIC_CORNICE_SOFFIT_DZ = 0.42 # corona soffit above the attic cornice base (ref 169 row 182)
ATTIC_PANEL_FRAME = 0.45       # Greek-key band around the relief panels (catalog #6)
ATTIC_PANEL_DEPTH = 0.25
DRUM_Z0 = ATTIC_Z1
# Phase 3 (QA-01-1), lead arbitration 2026-09-07: THE PHOTOGRAPHS OVERRIDE the reference sheet's 49.4 m apex (the
# sheet forced the DPR's 162 ft after deriving the rise from a foreshortened telephoto). The sheet's drum height 3.5 was
# the part VISIBLE above the attic cornice from a low camera; ~1.6 m more is hidden behind it. Drum = plain 2.7 +
# guilloche cushion 1.5 + cornice ring 0.9 = 5.1 m, top 43.4. DOME_RISE solved (not eyeballed) against the silhouette
# test: apex 52.8 (+0.6 apex cap = 53.4) puts the visible dome rise at 150 px / W_a 673 px = 0.223 on the cam01 hero at
# 1920x1080, i.e. +1.8 % of frame height vs ref 169 and -1.7 % vs ref 085 (tolerance 2 %; the only band that satisfies
# BOTH photos is rise/W_a 0.219-0.228). Derivation in docs/arch_notes.md "QA-01-1".
DRUM_PLAIN_H = 2.7
DRUM_BAND_H = 1.5
DRUM_CORNICE_H = 0.9
DRUM_H = DRUM_PLAIN_H + DRUM_BAND_H + DRUM_CORNICE_H   # 5.1
DRUM_Z1 = DRUM_Z0 + DRUM_H                      # 43.4
DRUM_BAND_R = 17.5        # scale/guilloche cushion band
DRUM_CORNICE_R = 18.7
DOME_BASE_R = 16.5
DOME_RISE = 9.4           # SOLVED, see the note above; do not eyeball
DOME_APEX_Z = DRUM_Z1 + DOME_RISE               # 52.8 (apex cap top 53.4)
DOME_SPHERE_R = (DOME_BASE_R ** 2 + DOME_RISE ** 2) / (2 * DOME_RISE)   # 19.18
DOME_SPHERE_CZ = DOME_APEX_Z - DOME_SPHERE_R    # 33.6

# ----------------------------------------------------------------------------- inner order (section 3b + DERIVED, see arch_notes.md)
INNER_COL_R = 16.0        # axis circumradius of the 8 tan columns (at the vertex azimuths)
INNER_COL_D = 1.7
INNER_COL_BASE_H = 0.8
INNER_COL_SHAFT_Z1 = 13.7                       # DERIVED: abacus at 15.5 (capital 1.8)
INNER_CAPITAL_H = 1.8
INNER_BLOCK_Z0 = INNER_COL_SHAFT_Z1 + INNER_CAPITAL_H   # 15.5
INNER_BLOCK_H = 2.0
INNER_BLOCK_SIZE = 2.4
INNER_ARCH_SPRING_Z = INNER_BLOCK_Z0 + INNER_BLOCK_H    # 17.5 = same as the outer arches (DERIVED)
INNER_SIDE = 2 * INNER_COL_R * math.sin(math.radians(22.5))   # 12.25 axis to axis
INNER_ARCH_SPAN = INNER_SIDE - INNER_BLOCK_SIZE               # 9.85 clear
INNER_WALL_THICKNESS = 1.2
INNER_WALL_APOTHEM = INNER_COL_R * math.cos(math.radians(22.5)) + INNER_WALL_THICKNESS / 2   # 15.38 outer face of the inner ring wall (centreline through the column axes)
INNER_WALL_Z1 = 30.0
CEILING_RING_Z = 24.5
CEILING_R = 15.0          # base ring radius of the coffered saucer (catalog: ~31 m diameter inner octagon)
CEILING_RISE = 5.0
CEILING_SPHERE_R = (CEILING_R ** 2 + CEILING_RISE ** 2) / (2 * CEILING_RISE)   # 25.0
CEILING_SPHERE_CZ = CEILING_RING_Z + CEILING_RISE - CEILING_SPHERE_R
# QA-03-8 (polish round 2): coffer depth measured from ref 083. A ring-3 trapezoid panel near the left edge of the
# frame (x 480-700, y 645-665) shows an 18 px splayed reveal on a ~220 px / ~4.5 m panel = 8.2 % of the panel width,
# at an off-axis angle of atan(9.5 / 25) = 20.8 deg, so the reveal implies a depth of 0.082 * 4.5 / tan(20.8) = 0.95 m,
# i.e. a depth-to-width ratio of 0.21 (the Pantheon's coffers are 0.23). Applied as 0.20 x the mean coffer width:
# saucer coffers average ~2.75 m across -> 0.55 m; barrel-vault octagons are 1.9 m across -> 0.38 m.
# The last 0.13 m at the room face steps out by COFFER_STEP so each coffer has a two-register reveal that catches the
# soffit lights instead of one flat inset outline. Was 0.30 / 0.20 with no step (read as flat at cam04).
COFFER_DEPTH = 0.55       # rotunda saucer-ceiling coffers (rib plate hangs this far below the field)
VAULT_COFFER_DEPTH = 0.38  # barrel-vault soffit ribs stand this far proud (0.12 -> 0.20 in round 1 -> 0.38 now)
# Reveal registers, read from the room face inwards as (widen, depth): a bolection lip projecting 0.05 m into the
# opening, then a splayed outer register 0.10 m wider than the box; the rest of the depth is the straight deep box.
# The lip's underside is a bright ring and the splay's floor a dark one, so every coffer gets a light/shadow line
# pair even seen almost face-on from cam04 -- the reason a single straight reveal read as a flat inset outline.
COFFER_REGISTERS = ((-0.05, 0.05), (0.10, 0.13))
# Vault: the in-row diamonds were opened up (arch_build build_vault_coffers) so 0.18 m of rib survives between
# every pair of openings; L.plate clamps these against L.polygon_clearance anyway and prints when it does.
VAULT_COFFER_REGISTERS = ((-0.030, 0.04), (0.055, 0.10))
# ARCH r8: grid the rib plates BEFORE they are bent onto the barrel / the saucer (arch_lib.bisect_grid).
# Chord error at step s on radius r is s^2/(8r): 1.1 mm on the 6.25 m barrel, 5 mm on the 25 m saucer.
VAULT_COFFER_ARC_STEP = 0.22      # in the arc PARAMETER (arc length at r_mean); 0.246 m at the wall end
VAULT_COFFER_DEPTH_STEP = 0.90    # across the barrel (no curvature there; caps the face area at 0.22 m2)
CEILING_RIB_STEP = 1.00           # saucer rib plate, both plan axes
CEILING_FIELD_LIFT = 0.02     # the field saucer sits this far above the ceiling sphere (build_ceiling)
# Sheet line 258: "Base ring with rosette band above the inner arches." That band is the VERTICAL inner face of
# the inner ring wall (radius INNER_WALL_APOTHEM - INNER_WALL_THICKNESS = 14.18), in the zone between the crown of
# the inner arches and the underside of the coffered saucer's rim. Both bounds are derived, not eyeballed:
#   crown   = INNER_ARCH_SPRING_Z + INNER_ARCH_SPAN / 2                     = 22.425
#   soffit  = CEILING_RING_Z - COFFER_DEPTH (the rib room face at the face centre) = 23.95
# The 16 band rosettes sit at the middle of that 1.53 m zone. Two per octagon face at +-11.25 deg from the face
# normal, which keeps the 22.5 deg spacing the ring had while putting every socket on a real flat face (the old
# alternate-vertex sockets sat on the octagon corner, where there is no face to stand on).
ROSETTE_BAND_HALF_ANGLE = 11.25
ROSETTE_BAND_Z = (INNER_ARCH_SPRING_Z + INNER_ARCH_SPAN / 2 + CEILING_RING_Z - COFFER_DEPTH) / 2

# ----------------------------------------------------------------------------- podium / rostra (OSM lobes, section 3b; DERIVED widths)
PODIUM_LOBE_R = 27.3      # outer radius of the podium block around each pier (OSM lobes r 27-28)
PODIUM_LOBE_HALF_ANGLE = 14.5    # degrees each side of the pier azimuth (OSM lobes ~29 deg wide)
PODIUM_BAND_H = 0.5       # Greek-key/rosette band at the top of every podium wall (catalog #12)
PODIUM_BAND_RECESS = 0.06
BAND_UNIT = 1.0           # Greek-key meander unit pitch; rosette bosses alternate (catalog #12)
BAND_PROUD = 0.035
URN_PLINTH = 1.8
URN_PLINTH_H = 0.6
URN_H = 3.0
PLATFORM_APOTHEM = 25.5   # DERIVED: paved octagonal platform at floor level between the podium lobes
PLATFORM_STEPS = 3        # down to GROUND_Z
# planter walls sweeping out from the lobes (OSM node runs): (pier azimuth, side (+1 = clockwise), reach radius)
PLANTER_SWEEPS = [(14.5, +1, 37.0), (59.5, -1, 33.9), (104.5, +1, 34.3), (149.5, -1, 37.5),
                  (194.5, +1, 37.6), (239.5, -1, 29.9), (284.5, -1, 29.7), (329.5, -1, 37.5)]
STAIR_PIERS = [59.5, 104.5]   # two stair flights on the lagoon side (063, 022)

# ----------------------------------------------------------------------------- colonnade (section 2b/3c + DERIVED arc, see arch_notes.md)
COL_ARC_CENTER = (-11.2, 84.7)   # world (X, Y): DERIVED least-squares circle through the OSM box bumps of both wings + pylon midpoints
COL_ARC_R = 117.4
COL_ROW_SPACING = 4.5
COL_BAY = 4.5
COL_CLUSTER_PAIR = 3.0           # the two columns of a 2x2 cluster, centre to centre along the arc
COL_MODULE = COL_CLUSTER_PAIR + 4 * COL_BAY     # 21.0 cluster centre to cluster centre (OSM bumps 20-24 m)
COL_FIRST_CLUSTER_S = 5.0        # arc length from the wing's rotunda end to the first cluster centre (OSM)
COLONNADE_D = 1.7
COLONNADE_D_TOP = 1.45
COLONNADE_BASE_H = 1.0
COLONNADE_SHAFT_H = 11.2
COLONNADE_CAPITAL_H = 1.8
COLONNADE_ABACUS = COLONNADE_BASE_H + COLONNADE_SHAFT_H + COLONNADE_CAPITAL_H   # 14.0 above ground
COLONNADE_ENTABLATURE_H = 2.4
PYLON_EXTRA_H = 2.4              # pylon-cluster shafts are taller: their capitals reach the entablature top
BOX_SIZE = 5.3
BOX_H = 3.55              # rim 3.55 above the box base: maidens (4.36 m, ORN) lean on it at shoulder height (refs 187/167)
MAIDEN_OUT = 0.32         # ORN maiden asset: box corner edge at local (0, -0.32) -> socket 0.32 m outward on the corner diagonal
PERGOLA_BEAM = 0.6
PYLON_RETURN = 17.0              # OSM: second pylon of each end pair is 17 m west (toward the hall) of the first
PYLON_RETURN_DIR = (0.0, -1.0)   # world direction of the return (west)
# wing ends (world), from the OSM wing polygons: rotunda-end cap centre and the first pylon (on the arc)
WINGS = {
    "south": dict(start=(32.0, -25.6), pylon=(100.0, 47.0)),
    "north": dict(start=(-22.0, -34.5), pylon=(-108.5, 13.0)),
}

# ----------------------------------------------------------------------------- misc
FLUTES = 24
FILLET_FRACTION = 0.25    # fillet width / flute width (sheet, ornament catalog row 5)
# QA-03-4 / QA-03-9: the flute hollow is a segmental circular arc, sampled at equal arc angles so the two samples
# nearest each fillet sit close to the arris and the flute wall there is steep (~72 deg off the tangent at LOD1).
# The old half-sine profile with evenly spaced samples never exceeded 56 deg, so the hollows caught almost full sun
# and the shafts read smooth at hero scale. Half-angle 90 deg -> depth / flute width = (1-cos90)/(2 sin90) = 0.500,
# the semicircular hollow of a Roman Corinthian order, 0.129 m on a 24-flute 2.46 m shaft (ref 054, 128: flutes read as narrow hard dark lines).
FLUTE_ARC_HALF_DEG = 90.0
# Attic base (sheet ornament catalog row 4: "base h 1.0, torus-scotia-torus Attic base on a square plinth,
# plinth square = 1.15 x shaft D"). Fractions of the height above the plinth, bottom to top; ref 113 shows the
# bold carved lower torus, a plain scotia and a smaller upper torus.
BASE_PLINTH_FRACTION = 0.20
BASE_COURSES = (("torus", 0.34), ("fillet", 0.04), ("scotia", 0.22),
                ("fillet", 0.04), ("torus", 0.28), ("apophyge", 0.08))
BASE_LOWER_TORUS_R = 1.16   # x shaft radius, capped so the torus stays inside the plinth
BASE_UPPER_TORUS_F = 0.80   # upper torus projection as a fraction of the lower torus projection
BASE_SCOTIA_R = 0.975       # scotia throat, x shaft radius
BEVEL_WIDTH = 0.03
BEVEL_SEGMENTS = 2


def az_to_xy(az_deg, r):
    a = math.radians(az_deg)
    return (-r * math.cos(a), r * math.sin(a))


def az_dir(az_deg):
    a = math.radians(az_deg)
    return (-math.cos(a), math.sin(a))


# ----------------------------------------------------------------------------- QA round-05 hero alignment
# THE single source of these three numbers (docs/reviews/arch_r4_review.md item 7): qa_silhouette's round-05 fit of
# ref 169 onto the 1920x1080 cam01 hero, photo px * S + (DX, DY) = render px. Both the measure tool and the sheet
# import them from here, so a QA re-alignment is a one-line change.
REF169_XF = (1.3108, -291.8, -124.6)
REF169_REL = "photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg"
MAIN_ROOT = Path("/Users/dk/Projects/3d render blender 3rd attempt building")   # the checkout that has reference/


def reference_dir():
    """common.REFERENCE_DIR, reachable from the python3-only tools too (common imports bpy)."""
    try:
        import common
        return Path(common.REFERENCE_DIR)
    except Exception:
        return Path(os.environ.get("PFA_REFERENCE_DIR", str(MAIN_ROOT / "reference")))


def ref169_path():
    """Absolute path to ref 169. Worktrees have no reference/ of their own, so it resolves into the main checkout."""
    return reference_dir() / REF169_REL
