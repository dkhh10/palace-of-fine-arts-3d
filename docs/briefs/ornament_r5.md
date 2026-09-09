# Ornament round 5 (no render, no master write) — brief from the lead (2026-09-09). Branch `ornament`. Read docs/briefs/process.md first.
Slot-filler while QA round 6 holds the GPU: nothing in this round renders; validate with the ORN stats / socket / coverage scripts only.
`git merge main` first (main has architecture r4: the 24 rotunda SOCKET_frieze_run_* moved to z 28.55 and +0.10 m outward, and the rotunda
frieze band is now 0.90 m tall; docs/arch_notes.md round 4, docs/reviews/arch_r4_review.md finding 5).
1. Rotunda frieze band: nothing is placed on the 24 rotunda frieze_run sockets today (scripts/build_master.py ORN_COLL has no frieze_run key).
   Ship a rotunda frieze relief asset for a 0.90 m band on the socket contract in docs/sockets.md (run_length from the socket; LOD0/1/2 within the
   tier budgets in docs/ornament_notes.md; per-instance variation seed), or state with numbers that the colonnade frieze_run asset fits the 0.90 m band
   and how. Report the exact ORN_COLL entry the lead must add to build_master.py (name, socket type, LOD names); do not edit build_master.py.
2. Hero attic panels: the reference's attic band is a deep figural relief (ref 169 / ref 085); ray-casts put ORN attic panels at 50 % of QA's hero
   attic box. Report the current ORN_attic_panel_v2 relief depth and the per-instance weathering variation as measured by your stats script, and
   list what a deeper relief would cost in tris per LOD (no build unless it stays inside the tier budget; if built, keep the socket contract).
3. Open issues in docs/ornament_notes.md "Open issues (ORN)": fix those that need no render (ORN_attic_panel_v2_LOD2 5598 -> <= 2400 tris, and any
   others), log the rest.
Deliverables: assets/ornament.blend, scripts/orn_*.py, notes section "Round 5", report < 20 lines with the tri tables and last commit.
