"""Gate 3 step 3b: the authoritative 8-bit encode of every lightmap, from the archival EXRs. CPU only.

    python3 export/gate3_encode.py

export/bake_lm.py and export/gate3_compose.py already write a first pass so that a job is self-checking, but
they pick `range` as the next power of two above the map's max, which throws away up to a full stop of code
space (measured: ARCH_rotunda_column_tan_inner_merged has max 64.7 and was encoded at range 128). This pass
re-encodes every `tex/*.exr` at `range = max` and records the error the way it is actually seen - in STOPS,
over the texels that carry signal (above 1 % of the map's own p99) - rather than as a relative error whose
99th percentile is dominated by the invisible near-black tail.

It overwrites the PNGs and writes out/gate3/encode.json, which export/manifest_v4.py prefers over the
first-pass numbers in the bake records.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402

t0 = time.time()
rep = {"started": time.strftime("%Y-%m-%dT%H:%M:%S"), "maps": {}}
exrs = sorted(g3.TEX.glob("*.exr"))
for p in exrs:
    key = p.stem
    a = g3.read_exr32(p)
    mx = float(a.max())
    rng = float(max(mx, 1e-3))
    lum = a.max(axis=-1)
    nz = lum[lum > 0]
    p99 = float(np.percentile(nz, 99)) if nz.size else 0.0
    sel = lum > 0.01 * p99
    d = dict(range=round(rng, 6), range_first_pass=g3.pick_range(a), size=[int(a.shape[1]), int(a.shape[0])],
             stats=g3.px_stats(a, ceiling=rng), signal_p99=round(p99, 4),
             signal_frac=round(float(sel.mean()), 4))
    for enc, fn, dec in (("rgbm8", g3.rgbm_encode, g3.rgbm_decode_u8),
                         ("gamma2", g3.gamma2_encode, g3.gamma2_decode_u8)):
        e = fn(a, rng)
        out = g3.TEX / f"{key}_{enc}.png"
        nb = (g3.write_png_rgba8 if e.shape[-1] == 4 else g3.write_png_rgb8)(out, e)
        rb = g3.read_png(out)
        assert np.array_equal(rb, e), f"{out}: did not read back identical"
        back = dec(rb, rng)
        s, t = a[sel], back[sel]
        # the floor is 1 % of the map's own p99 PER CHANNEL, not per texel: a lit texel can still hold a
        # near-zero blue channel, and a ratio taken on that is a metric artefact, not an encoding error
        # (it read 16.7 "stops" on the drum band before this line).
        m = s > 0.01 * p99
        rel = np.abs(t[m] - s[m]) / s[m]
        stops = np.abs(np.log2(np.maximum(t[m], 1e-9) / s[m]))
        d[enc] = dict(path=out.name, bytes=nb,
                      rel_mean=round(float(rel.mean()), 5), rel_p99=round(float(np.percentile(rel, 99)), 5),
                      stops_p99=round(float(np.percentile(stops, 99)), 5),
                      stops_p999=round(float(np.percentile(stops, 99.9)), 5),
                      abs_max=round(float(np.abs(back - a).max()), 5))
    rep["maps"][key] = d
    print(f"[gate3] encode {key}: max {mx:.3f} range {rng:.3f} (was {d['range_first_pass']:.0f}) "
          f"gamma2 {d['gamma2']['stops_p99']:.4f} stops  rgbm8 {d['rgbm8']['stops_p99']:.4f} stops")
rep["n"] = len(exrs)
rep["wall_s"] = round(time.time() - t0, 1)
(g3.OUT / "encode.json").write_text(json.dumps(rep, indent=1) + "\n")
print(f"[gate3] encode done: {len(exrs)} maps in {rep['wall_s']} s")
