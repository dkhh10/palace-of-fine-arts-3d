"""Phase 10 r1 -- shared numpy helpers (no bpy): cameras.json, projection with the SIMPLE_RADIAL term, EXR passes."""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
P2 = ROOT / "assets" / "textures" / "projection2"
WORK = P2 / "work"


def load_cams(path=None):
    return json.loads(Path(path or P2 / "cameras.json").read_text())["cameras"]


def project(X, c, distort=True, R=None, t=None):
    """World points (n,3) -> photo pixels (n,2) at the registered size, and camera depth (n,)."""
    R = np.asarray(c["R"] if R is None else R); t = np.asarray(c["t"] if t is None else t)
    K = np.asarray(c["K"])
    Xc = X @ R.T + t
    z = Xc[:, 2]
    zs = np.where(np.abs(z) < 1e-9, 1e-9, z)
    x, y = Xc[:, 0] / zs, Xc[:, 1] / zs
    if distort:
        r2 = x * x + y * y
        f = 1 + c.get("k1", 0.0) * r2
        x, y = x * f, y * f
    return np.stack([K[0, 0] * x + K[0, 2], K[1, 1] * y + K[1, 2]], 1), z


def read_passes(path):
    """Blender multilayer EXR -> dict(pos (h,w,3), nrm (h,w,3), alpha (h,w), z (h,w)); row 0 = top of image."""
    import OpenEXR
    f = OpenEXR.File(str(path))
    ch = {}
    for p in f.parts:
        for k, v in p.channels.items():
            ch[k] = v.pixels
    def g(prefix):
        return np.stack([ch[f"ViewLayer.{prefix}.{a}"] for a in "XYZ"], -1).astype(np.float32)
    comb = ch.get("ViewLayer.Combined")
    alpha = comb[..., 3] if comb is not None and comb.ndim == 3 else None
    out = dict(pos=g("Position"), nrm=g("Normal"), z=ch["ViewLayer.Depth.Z"].astype(np.float32))
    out["alpha"] = alpha if alpha is not None else (np.linalg.norm(out["pos"], axis=-1) > 0).astype(np.float32)
    return out
