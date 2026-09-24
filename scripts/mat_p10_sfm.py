"""Phase 10 r1, step 1 -- registration: load the probe's sparse model, regenerate its 1600 px images, dump to npz.

    .venv-p10/bin/python scripts/mat_p10_sfm.py images      # rebuild work/images (the probe's exact resize)
    .venv-p10/bin/python scripts/mat_p10_sfm.py dump        # work/sfm.npz: cameras, poses, points, observations

No bpy.  The sparse model is the recon probe's model 2 (docs/recon_probe/REPORT.md: 71 images, 11,452 points,
0.43 px), read from the MAIN checkout (gitignored, on disk only).  The images it was built from were written by
docs/recon_probe/build_set.py into a work/ folder that is not kept, so they are regenerated here with the same
three calls (exif_transpose, RGB, thumbnail 1600) -- the camera intrinsics are only valid at that size.
"""
import sys, os, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
RAW = MAIN / "reference" / "photos" / "raw"
SPARSE = MAIN / "docs" / "recon_probe" / "sparse" / "2"
SETJ = MAIN / "docs" / "recon_probe" / "set.json"
WORK = ROOT / "assets" / "textures" / "projection2" / "work"
IMG = WORK / "images"


def load():
    import pycolmap
    return pycolmap.Reconstruction(str(SPARSE))


def cmd_images():
    from PIL import Image, ImageOps
    rec = load()
    meta = json.load(open(SETJ))["kept"]
    IMG.mkdir(parents=True, exist_ok=True)
    bad = 0
    for im in rec.images.values():
        src = meta[im.name]["src"]
        p = Image.open(RAW / src)
        p = ImageOps.exif_transpose(p).convert("RGB")
        p.thumbnail((1600, 1600))
        cam = rec.cameras[im.camera_id]
        if p.size != (cam.width, cam.height):
            bad += 1
            print("SIZE MISMATCH", im.name, p.size, (cam.width, cam.height))
        p.save(IMG / im.name, quality=95)
    print(f"images: {len(rec.images)} written, {bad} size mismatches")


def cmd_dump():
    rec = load()
    ims = sorted(rec.images.values(), key=lambda i: i.name)
    names, K, dist, R, t, wh = [], [], [], [], [], []
    obs = []                       # (image index, point id, x, y)
    for k, im in enumerate(ims):
        cam = rec.cameras[im.camera_id]
        f, cx, cy, k1 = cam.params
        names.append(im.name)
        K.append([[f, 0, cx], [0, f, cy], [0, 0, 1]])
        dist.append(k1)
        T = im.cam_from_world() if callable(im.cam_from_world) else im.cam_from_world
        M = np.asarray(T.matrix())
        R.append(M[:, :3]); t.append(M[:, 3])
        wh.append((cam.width, cam.height))
        for p2 in im.points2D:
            if p2.has_point3D():
                obs.append((k, p2.point3D_id, p2.xy[0], p2.xy[1]))
    pids = sorted(rec.points3D.keys())
    xyz = np.array([rec.points3D[i].xyz for i in pids])
    rgb = np.array([rec.points3D[i].color for i in pids])
    err = np.array([rec.points3D[i].error for i in pids])
    trk = np.array([rec.points3D[i].track.length() for i in pids])
    np.savez(WORK / "sfm.npz", names=np.array(names), K=np.array(K), dist=np.array(dist), R=np.array(R),
             t=np.array(t), wh=np.array(wh), pid=np.array(pids), xyz=xyz, rgb=rgb, err=err, trk=trk,
             obs=np.array(obs))
    C = np.array([-r.T @ tt for r, tt in zip(R, t)])
    print(f"dump: {len(names)} cams, {len(pids)} points, {len(obs)} observations; "
          f"cam centre spread {np.ptp(C, 0).round(2)}; point spread {np.ptp(xyz, 0).round(2)}")


if __name__ == "__main__":
    {"images": cmd_images, "dump": cmd_dump}[sys.argv[1]]()
