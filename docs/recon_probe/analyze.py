import pycolmap as p, os, json, numpy as np, csv, re
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
W=os.path.dirname(os.path.abspath(__file__)); S=json.load(open(f"{W}/set.json"))['kept']
R="/Users/dk/Projects/3d render blender 3rd attempt building/reference/photos/index_wikimedia.csv"
desc={r['file']:r['desc'].replace('\n',' ')[:70] for r in csv.DictReader(open(R,encoding='utf-8'))}
models=[]
for d in sorted(os.listdir(f"{W}/sparse")):
    if not d.isdigit(): continue
    r=p.Reconstruction(f"{W}/sparse/{d}")
    names=[im.name for im in r.images.values() if im.has_pose]
    tl=[len(pt.track.elements) for pt in r.points3D.values()]
    cats={}
    for n in names: cats[S[n]['cat']]=cats.get(S[n]['cat'],0)+1
    models.append(dict(id=d,reg=len(names),pts=r.num_points3D(),track=float(np.mean(tl)) if tl else 0,
        reproj=r.compute_mean_reprojection_error(),cats=cats,names=names))
models.sort(key=lambda m:-m['reg'])
reg=set(n for m in models for n in m['names'])
for m in models: print(f"| {m['id']} | {m['reg']} | {m['pts']} | {m['track']:.2f} | {m['reproj']:.3f} | {m['cats']} |")
print("registered total",len(reg),"of",len(S))
un=sorted([n for n in S if n not in reg],key=lambda n:-S[n]['w']*S[n]['h'])[:10]
for n in un: print(n,S[n]['w'],S[n]['h'],'|',desc.get(S[n]['src'],''))
json.dump([{k:v for k,v in m.items()} for m in models],open(f"{W}/models.json","w"),indent=1)
if not models: raise SystemExit
big=models[0]; r=p.Reconstruction(f"{W}/sparse/{big['id']}")
os.makedirs(f"{W}/ply",exist_ok=True); r.export_PLY(f"{W}/ply/model_{big['id']}.ply")
X=np.array([pt.xyz for pt in r.points3D.values()]); err=np.array([pt.error for pt in r.points3D.values()])
C=np.array([im.projection_center() for im in r.images.values() if im.has_pose])
cc=[S[im.name]['cat'] for im in r.images.values() if im.has_pose]
# up vector: mean camera "down" direction in world ~ -(R^T * [0,1,0]) ; image y points down
ups=[]
for im in r.images.values():
    if not im.has_pose: continue
    Rm=im.cam_from_world().rotation.matrix(); ups.append(-Rm.T@np.array([0,1,0]))
up=np.mean(ups,0); up/=np.linalg.norm(up)
med=np.median(X,0); Xc=X-med; Cc=C-med
a=np.cross(up,[1,0,0]); a/=np.linalg.norm(a); b=np.cross(up,a)
keep=np.linalg.norm(Xc,axis=1)<np.percentile(np.linalg.norm(Xc,axis=1),95)
def proj(V,u,v): return V@u,V@v
# azimuth spread of cameras around point-cloud centre (horizontal plane)
az=np.degrees(np.arctan2(Cc@b,Cc@a)); azs=np.sort(az%360); gaps=np.diff(np.r_[azs,azs[0]+360])
print("camera azimuth coverage: max gap %.1f deg -> covered arc %.1f deg"%(gaps.max(),360-gaps.max()))
print("azimuth percentiles 5/50/95 (relative):",np.percentile(((az-np.median(az)+180)%360)-180,[5,50,95]).round(1))
col={'rotunda':'tab:red','main':'tab:blue'}
fig,ax=plt.subplots(1,2,figsize=(9.6,4.8),dpi=100)
for k,(u,v,t) in enumerate([(a,b,'top-down (plane ⊥ mean camera up)'),(a,up,'side (horizontal axis a vs up)')]):
    ax[k].scatter(*proj(Xc[keep],u,v),s=0.3,c='0.4',alpha=0.4)
    for c in set(cc):
        m=np.array([x==c for x in cc]); ax[k].scatter(*proj(Cc[m],u,v),s=12,c=col.get(c,'k'),label=f"cam {c}")
    ax[k].set_title(t,fontsize=9); ax[k].set_aspect('equal'); ax[k].legend(fontsize=7)
fig.suptitle(f"model {big['id']}: {big['reg']} cams, {big['pts']} pts (arbitrary SfM units)",fontsize=10)
fig.tight_layout(); os.makedirs(f"{W}/plots",exist_ok=True); fig.savefig(f"{W}/plots/model_{big['id']}_top_side.png")
print("plot", f"{W}/plots/model_{big['id']}_top_side.png")
