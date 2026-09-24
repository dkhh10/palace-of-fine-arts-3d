import csv, os, re, json
from PIL import Image, ImageOps
R="/Users/dk/Projects/3d render blender 3rd attempt building/reference/photos"
W=os.path.dirname(os.path.abspath(__file__))
rows=list(csv.DictReader(open(f"{R}/index_wikimedia.csv",encoding="utf-8")))
files=set(os.listdir(f"{R}/raw"))
byfile={r['file']:r for r in rows}
kept,detail,excl=[],[],[]
hist=re.compile(r'1915|exposition|postcard|panama|ppie',re.I)
det=re.compile(r'capital|detail|statue|close[- ]?up|sculpt|figure|relief|frieze|urn',re.I)
for f in sorted(files):
    if not re.search(r'\.(jpe?g|png)$',f,re.I): continue
    r=byfile.get(f,{})
    cat=r.get('cat') or (f.split('_')[2] if f.count('_')>2 else '?')
    desc=(r.get('desc') or '')+' '+f
    if cat in('night','ppie1915') or hist.search(desc) or re.search(r'\bnight\b',desc,re.I): excl.append((f,cat)); continue
    if det.search(desc): detail.append((f,cat)); continue
    kept.append((f,cat))
os.makedirs(f"{W}/images",exist_ok=True)
meta={}
for f,cat in kept:
    im=Image.open(f"{R}/raw/{f}"); ex=im.getexif()
    W0,H0=im.size
    im=ImageOps.exif_transpose(im).convert("RGB"); im.thumbnail((1600,1600))
    out=os.path.splitext(f)[0]+".jpg"
    exif=im.getexif() if False else None
    # focal from EXIF
    sub=ex.get_ifd(0x8769) if ex else {}
    f35=sub.get(41989); fmm=sub.get(37386)
    im.save(f"{W}/images/{out}",quality=92)
    meta[out]=dict(src=f,cat=cat,w=W0,h=H0,f35=float(f35) if f35 else None,fmm=float(fmm) if fmm else None)
json.dump(dict(kept=meta,detail=detail,excluded=excl),open(f"{W}/set.json","w"),indent=1)
from collections import Counter
print("kept",len(kept),Counter(c for _,c in kept)); print("detail",len(detail)); print("excluded",len(excl),Counter(c for _,c in excl))
print("with f35",sum(1 for m in meta.values() if m['f35']),"with fmm",sum(1 for m in meta.values() if m['fmm']))
print("unindexed", len([f for f in files if f not in byfile]))
