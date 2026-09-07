"""Architectural parameters for the Palace of Fine Arts rotunda + colonnades. ALL VALUES IN METRES.

Source of every number: docs/reference_sheet.md (sections 2b, 3b, 3c) unless marked DERIVED, in which case the derivation is
written in docs/arch_notes.md. World frame: origin = rotunda floor centre, z=0 = rotunda floor, +Y east (lagoon), -X north.
Compass azimuth az (deg clockwise from north) maps to world (X, Y) = (-r*cos(az), r*sin(az)).
"""
import math

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
COL_SHAFT_H = 16.3
COL_SHAFT_Z1 = COL_SHAFT_Z0 + COL_SHAFT_H       # 24.8 (shaft top = capital socket)
COL_D_BOTTOM = 2.5
COL_D_TOP = 2.1
CAPITAL_H = 2.6
ENTABLATURE_Z0 = COL_SHAFT_Z1 + CAPITAL_H       # 27.4
ARCHITRAVE_H, FRIEZE_H, CORNICE_H = 1.4, 1.2, 1.2
ENTABLATURE_Z1 = ENTABLATURE_Z0 + ARCHITRAVE_H + FRIEZE_H + CORNICE_H   # 31.2
ATTIC_Z0 = ENTABLATURE_Z1
ATTIC_H = 7.1
ATTIC_Z1 = ATTIC_Z0 + ATTIC_H                   # 38.3
ATTIC_BASE_MOULDING_H = 0.9    # DERIVED (085): modillion course + Greek key band forming the attic base over the ressauts
ATTIC_TOP_CORNICE_H = 0.8      # DERIVED (085)
ATTIC_PANEL_FRAME = 0.45       # Greek-key band around the relief panels (catalog #6)
ATTIC_PANEL_DEPTH = 0.25
DRUM_Z0 = ATTIC_Z1
DRUM_H = 3.5
DRUM_Z1 = DRUM_Z0 + DRUM_H                      # 41.8
DRUM_BAND_R = 17.5        # scale/guilloche cushion band
DRUM_BAND_H = 1.6
DRUM_CORNICE_R = 18.7
DOME_BASE_R = 16.5
DOME_APEX_Z = 49.4
DOME_RISE = DOME_APEX_Z - DRUM_Z1               # 7.6
DOME_SPHERE_R = (DOME_BASE_R ** 2 + DOME_RISE ** 2) / (2 * DOME_RISE)   # 21.7
DOME_SPHERE_CZ = DOME_APEX_Z - DOME_SPHERE_R    # 27.7

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
COFFER_DEPTH = 0.3

# ----------------------------------------------------------------------------- podium / rostra (OSM lobes, section 3b; DERIVED widths)
PODIUM_LOBE_R = 27.3      # outer radius of the podium block around each pier (OSM lobes r 27-28)
PODIUM_LOBE_HALF_ANGLE = 14.5    # degrees each side of the pier azimuth (OSM lobes ~29 deg wide)
PODIUM_BAND_H = 0.5       # Greek-key/rosette band at the top of every podium wall (catalog #12)
PODIUM_BAND_RECESS = 0.06
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
BOX_H = 3.0
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
FILLET_FRACTION = 0.25    # fillet width / flute width
BEVEL_WIDTH = 0.03
BEVEL_SEGMENTS = 2


def az_to_xy(az_deg, r):
    a = math.radians(az_deg)
    return (-r * math.cos(a), r * math.sin(a))


def az_dir(az_deg):
    a = math.radians(az_deg)
    return (-math.cos(a), math.sin(a))
