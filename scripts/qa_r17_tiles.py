#!/usr/bin/env python3
"""QA round 17: cut the six-station 100 % tile set (CLAUDE.md's Phase 6 gate check).

No Blender, no Chrome. Each station's 1920x1080 viewer frame is cut into 3 x 2 tiles of 640 x 540
at 100 % and pasted beside the SAME crop of that station's Cycles reference, so the critic judges
geometry and material at full resolution against the frame it must match.

    python3 scripts/qa_r17_tiles.py            # all six stations -> <out>/round16c_cam0N_tile_rRcC.png
    python3 scripts/qa_r17_tiles.py 1 2 5      # only these stations
    PFA_TILE_OUT=/some/dir python3 scripts/qa_r17_tiles.py

Output goes to $PFA_TILE_OUT (default: the scratchpad, because full-res tiles are gitignored).
"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r17_probe as P17  # noqa: E402

P = P17.P
OUT = Path(os.environ.get("PFA_TILE_OUT", "/tmp/qa_r17_tiles"))
COLS, ROWS = 3, 2


def main(stations):
    P.select_round("17")
    OUT.mkdir(parents=True, exist_ok=True)
    w, h = 1920 // COLS, 1080 // ROWS
    for st in stations:
        view = P.rgb(P.BAKED % st).astype(np.uint8)
        ref = P.rgb(P.REF[st][0]).astype(np.uint8)
        for r in range(ROWS):
            for c in range(COLS):
                x0, y0 = c * w, r * h
                a = view[y0:y0 + h, x0:x0 + w]
                b = ref[y0:y0 + h, x0:x0 + w]
                sheet = np.zeros((h, w * 2 + 8, 3), dtype=np.uint8)
                sheet[:, :w] = a
                sheet[:, w + 8:] = b
                p = OUT / f"round16c_cam{st:02d}_tile_r{r + 1}c{c + 1}.png"
                Image.fromarray(sheet).save(p)
                print(p)


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5, 6]
    main(args)
