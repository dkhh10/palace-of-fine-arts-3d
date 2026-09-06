# helper: convert 1400px-wide viewer coords -> original pixel rects, write JSON
import json, subprocess, sys, glob, os
RAW='reference/photos/raw'
def orig(n):
    if n=='user': return 'reference/photos/user/user_wide_midday.png'
    return glob.glob(f'{RAW}/ref_{n}_*')[0]
def width(p):
    out=subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width','-of','csv=p=0',p])
    return int(out.decode().strip().split(',')[0])
def build(rows, outjson):
    rects=[]
    for n,x,y,w,h,label in rows:
        p=orig(n); s=width(p)/1400.0
        rects.append([p,int(x*s),int(y*s),max(1,int(w*s)),max(1,int(h*s)),f'{n}:{label}'])
    json.dump(rects,open(outjson,'w'),indent=0)
    return rects
if __name__=='__main__':
    rows=json.load(open(sys.argv[1]))
    build(rows, sys.argv[2])
