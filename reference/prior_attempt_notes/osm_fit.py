import json, math
from PIL import Image, ImageDraw, ImageFont
import numpy as np
out = json.load(open("refs/site_local.json"))
def fit_circle(P):
    P = np.array(P); x, y = P[:,0], P[:,1]
    A = np.c_[2*x, 2*y, np.ones(len(x))]; b = x**2 + y**2
    c, res, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0], c[1]; r = math.sqrt(c[2] + cx**2 + cy**2)
    d = np.hypot(x-cx, y-cy)
    return cx, cy, r, d.min(), d.max()
for name in ("roof306 h20", "roof310 h19", "b302 h20m"):
    ring = out[name][0]
    cx, cy, r, dmin, dmax = fit_circle(ring)
    angs = sorted(math.degrees(math.atan2(y-cy, x-cx)) for x, y in ring)
    print(f"{name}: circle center=({cx:.1f},{cy:.1f}) r={r:.1f} dist range [{dmin:.1f},{dmax:.1f}] angle range [{angs[0]:.0f},{angs[-1]:.0f}]")
# rotunda zoom
rp = out["rotunda"][0]
S = 12; W = 1000; ox = oy = W/2
img = Image.new("RGB", (W, W), (250, 250, 248)); dr = ImageDraw.Draw(img)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
for r in range(5, 45, 5):
    dr.ellipse([ox-r*S, oy-r*S, ox+r*S, oy+r*S], outline=(225, 225, 225)); dr.text((ox+r*S+2, oy+2), f"{r}", fill=(180,180,180), font=font)
for k in range(8):
    a = math.radians(k*45); dr.line([(ox, oy), (ox+40*S*math.cos(a), oy-40*S*math.sin(a))], fill=(230,230,230))
    a = math.radians(k*45+22.5); dr.line([(ox, oy), (ox+40*S*math.cos(a), oy-40*S*math.sin(a))], fill=(240,240,240))
P = [(ox + x*S, oy - y*S) for x, y in rp]
dr.line(P + [P[0]], fill=(200, 60, 40), width=2)
for i, p in enumerate(P):
    dr.ellipse([p[0]-2, p[1]-2, p[0]+2, p[1]+2], fill=(0,0,0))
    if i % 4 == 0: dr.text((p[0]+3, p[1]-12), str(i), fill=(0,0,120), font=font)
for name in out:
    if name.startswith("w3") or name.startswith("b317"):
        for ring in out[name]:
            Q = [(ox + x*S, oy - y*S) for x, y in ring]; dr.line(Q + [Q[0]], fill=(0, 140, 0), width=1)
for name in ("roof306 h20", "roof310 h19", "b302 h20m", "lagoon0"):
    for ring in out[name]:
        Q = [(ox + x*S, oy - y*S) for x, y in ring]; dr.line(Q + [Q[0]], fill=(120, 120, 200), width=1)
dr.text((10, 10), "rotunda OSM outline, 12 px/m, +x east (lagoon) right, +y north up", fill=(0,0,0), font=font)
img.save("refs/site_rotunda_zoom.png")
# print polar coordinates of the rotunda nodes
for i, (x, y) in enumerate(rp):
    print(f"{i:3d} r={math.hypot(x,y):5.1f} ang={math.degrees(math.atan2(y,x)):7.1f}")
