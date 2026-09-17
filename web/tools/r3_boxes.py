#!/usr/bin/env python3
"""6c round 3 — read QA 16's own crown / foliage boxes on an arbitrary capture tag.

    web/tools/r3_boxes.py <tag> [crown|foliage16|both]

Column 1 is <tag>, column 2 `round16b` (the scored capture), column 3 `round15`, column 4 the
reference. The measures are QA's, imported from scripts/qa_r16_probe.py and not re-implemented here,
so a number printed by this tool is the number the critic's tool prints.
"""
import os
import sys
from pathlib import Path

WT = Path(__file__).resolve().parent.parent.parent
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
os.environ.setdefault("PFA_VIEWER_WEB", str(WT / "renders/web"))
sys.path.insert(0, str(MAIN / "scripts"))

import qa_r16_probe as Q  # noqa: E402

tag = sys.argv[1] if len(sys.argv) > 1 else "round16b"
what = sys.argv[2] if len(sys.argv) > 2 else "both"
Q.P.ROUNDS["r3"] = (f"{tag}_cam%02d.png", "round16b_cam%02d.png", "round15_cam%02d.png",
                    (tag, "round16b", "round15"), Q.P.REF_R14)
Q.P.select_round("r3")
if what in ("crown", "both"):
    Q.cmd_crown()
if what in ("foliage16", "both"):
    Q.cmd_foliage16()
