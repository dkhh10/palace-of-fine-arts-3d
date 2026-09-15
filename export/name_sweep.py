"""Gate 1 step 4: the CLAUDE.md object-name sweep, run on the EXPORT SET instead of master.blend.

    python3 export/name_sweep.py [export/out/gate1/export_set.json]

Same pattern and same exemptions as scripts/qa_name_sweep.py (the gate check added 2026-09-10), applied to every
object the Gate 1 export actually writes - which is what ships to the viewer. Exit 1 on any non-exempt hit.
Needs no Blender: export_set.json lists every exported object with its class, mesh and triangle count.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "export" / "out" / "gate1" / "export_set.json"

# scripts/qa_name_sweep.py's pattern, plus the stand-in words QA round 11b showed it could not see
# (`board|impostor|billboard`): the export's own 127 far-tree carriers passed the sweep as 0 hits while
# covering 16-26 % of every frame. The same three words go into scripts/qa_name_sweep.py (the lead's file).
PAT = re.compile(r"placeholder|proxy|blocker|fill|occlud|block|dummy|temp|card|board|impostor|billboard", re.I)
EXEMPT = re.compile(r"^(ARCH_rotunda_inner_block(_cap)?_\d+|ENV_backdrop_fill(roof)?_\d+)$")
# Gate 1 additions, each a merged object whose name carries a source material, not a placeholder:
#   ENV_backdropgroup_backdrop_fill / _backdrop_fillroof are the merged city blocks (the objects the exemption
#   on record already covers, joined into one mesh each); ARCH_*_inner_block* no longer exist as objects.
EXEMPT_GATE1 = re.compile(r"^(ENV_backdropgroup_backdrop_fill(roof)?|ENV_treeboard_\d+)$")
# Named exemptions, with the justification the gate check demands:
JUSTIFICATION = {
    "ENV_backdropgroup_backdrop_fill": "the merged city blocks (the round-10 ENV_backdrop_fill_* exemption, joined)",
    "ENV_backdropgroup_backdrop_fillroof": "the merged city-block roofs (same exemption, joined)",
    "ENV_treeboard_": "Gate 3 impostor carriers, hidden in every QA capture until the impostor bake",
}


def justify(name):
    for k, v in JUSTIFICATION.items():
        if name.startswith(k):
            return v
    return "on record in docs/quality_checklist.md"


def main(path):
    data = json.loads(Path(path).read_text())
    assets = data["assets"]
    hits, exempt = [], []
    for name in sorted(assets):
        if not PAT.search(name):
            continue
        a = assets[name]
        row = f"{name:52s} {a['cls']:5s} {a.get('kind', '-'):12s} mesh={a['mesh']} tris={a['tris']}"
        if EXEMPT.match(name) or EXEMPT_GATE1.match(name):
            exempt.append(f"{row}  [{justify(name)}]")
        else:
            hits.append(row)
    print(f"[name_sweep] {len(assets)} exported objects, {len(exempt)} exempt (on record in "
          f"docs/quality_checklist.md), {len(hits)} to explain:")
    groups = {}
    for r in exempt:
        groups.setdefault(r.split()[0].rstrip("0123456789"), []).append(r)
    for k, rows in sorted(groups.items()):
        print(f"   exempt x{len(rows):<4d} {rows[0]}")
        if len(rows) > 1:
            print(f"                  ... {len(rows) - 1} more, {rows[-1].split()[0]} last")
    for r in hits:
        print("   HIT", r)
    print("[name_sweep] " + ("PASS" if not hits else "FAIL"))
    return 0 if not hits else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT))
