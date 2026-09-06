"""All dimensions in metres. Origin = rotunda centre at water level (z=0 = lagoon surface).
+x = east (lagoon / hero camera side), +y = north. Octagon faces are centred at OCT_ROT + 45k degrees (OSM)."""
import math

# ---------------------------------------------------------------- rotunda
OCT_ROT = 8.0                 # deg, rotation of the octagon (face centre of the "front" arch faces the lagoon)
A_OUT = 19.8                  # apothem of the outer arch-wall plane
A_IN = 14.8                   # apothem of the inner (rotunda-side) face of the ring  -> vault depth 6 m
A_ATTIC = 18.8                # apothem of the attic wall
FACE = 2 * A_OUT * math.tan(math.radians(22.5))   # 18.2 m face length (outer)
SPAN = 11.6                   # clear arch span (semicircular)
ARCH_SPRING = 19.5            # z of arch springing line (above water)
ARCH_TOP = ARCH_SPRING + SPAN / 2

Z_PLATFORM = 1.3              # top of the rotunda platform above water
PED_H = 4.6                   # pedestal height
PED_SIZE = 3.1                # pedestal plan size
PLATFORM_R = 32.0             # rotunda platform radius
COL_D = 2.4                   # pink column diameter at the base of the shaft
COL_BASE_H = 1.0
COL_SHAFT_H = 16.6
COL_CAP_H = 2.8
COL_PAIR_CC = 3.5             # centre-to-centre of the column pair at a pier
COL_OFFSET = 1.3              # distance of column axis in front of the arch-wall plane (radially outward)
ENT_H = 3.3                   # lower entablature (architrave+frieze+cornice)
ATTIC_H = 6.1
DRUM_H = 2.0
DOME_D = 36.0
DOME_RISE = 11.5

Z_PED_TOP = Z_PLATFORM + PED_H                       # 5.9
Z_COL_TOP = Z_PED_TOP + COL_BASE_H + COL_SHAFT_H + COL_CAP_H   # 26.3
Z_ENT_TOP = Z_COL_TOP + ENT_H                        # 29.6
Z_ATTIC_TOP = Z_ENT_TOP + ATTIC_H                    # 35.7
Z_DRUM_TOP = Z_ATTIC_TOP + DRUM_H                    # 37.7
Z_APEX = Z_DRUM_TOP + DOME_RISE                      # 49.2

# inner (tan) columns at the inner vertices
IN_COL_D = 1.7
IN_COL_H = 13.0               # base+shaft+capital
IN_ENT_H = 2.0
Z_IN_COL_BASE = Z_PLATFORM + 1.2
Z_IN_SPRING = Z_IN_COL_BASE + IN_COL_H + IN_ENT_H     # inner arches spring here (~17.5)
CEIL_RISE = 5.0               # interior coffered saucer dome rise
CEIL_BASE_Z = ARCH_TOP + 1.0  # base ring of the coffered ceiling

# ---------------------------------------------------------------- colonnade
CN_COL_D = 2.0
CN_PLINTH_H = 1.0
CN_BASE_H = 0.7
CN_SHAFT_H = 15.5
CN_CAP_H = 2.2
CN_ENT_H = 2.6
CN_ROW_GAP = 4.5              # between the two rows
CN_BAY = 4.6                  # column spacing along the arc
CN_BOX_H = 5.0
CN_GROUND_Z = 1.0             # colonnade ground level above water
CN_CLUSTER_EVERY = 5          # every 5th position is a 2x2 cluster with a box

# ---------------------------------------------------------------- site
WATER_Z = 0.0
GROUND_Z = 0.9
LAGOON_DEPTH = 1.5

# ---------------------------------------------------------------- colours (linear sRGB)
STONE_TAN = (0.72, 0.57, 0.38)
STONE_LIGHT = (0.80, 0.68, 0.48)
COL_PINK = (0.50, 0.24, 0.18)
DOME_CREAM = (0.86, 0.80, 0.66)
