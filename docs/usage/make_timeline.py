#!/usr/bin/env python3
"""Build docs/timeline.html (self-contained SVG, no external deps) from docs/usage/sessions.json
plus the gate / QA-round record in docs/retrospective.md (hard-coded below, local time +02:00)."""
import json, os, datetime
H = os.path.dirname(__file__)
d = json.load(open(os.path.join(H, 'sessions.json')))
TZ = datetime.timedelta(hours=2)
def loc(ts): return (datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).replace(tzinfo=None) + TZ)
sessions = [(i+1, loc(s['first']), loc(s['last']), s['cost_usd']) for i, s in enumerate(d['sessions'])]
# cumulative project cost by hour (local)
hourly = []
acc = 0.0
for h, c in sorted(d['hourly_cost_usd'].items()):
    t = datetime.datetime.fromisoformat(h + ':00:00') + TZ
    acc += c; hourly.append((t, round(acc, 2)))
daily = [(k, v['cost_usd']) for k, v in d['daily'].items()]
events = [  # (local datetime, label, hero score or None, kind)
 ('2026-09-06 13:35', 'Phase 0', None, 'gate'),
 ('2026-09-06 14:30', 'API limit', None, 'stop'),
 ('2026-09-06 20:43', 'Phase 1 gate', None, 'gate'),
 ('2026-09-07 08:22', 'QA r1 / Phase 2 gate', 2.17, 'qa'),
 ('2026-09-07 14:47', 'restart 1', None, 'stop'),
 ('2026-09-07 17:17', 'QA r2 / Phase 3 gate', 2.94, 'qa'),
 ('2026-09-07 19:32', 'restart 2', None, 'stop'),
 ('2026-09-07 20:23', 'watchdog kills 3 renders', None, 'kill'),
 ('2026-09-07 20:49', 'QA r3', 3.28, 'qa'),
 ('2026-09-07 22:40', 'checkpoint (machine closed)', None, 'stop'),
 ('2026-09-08 04:50', 'QA r4', 3.28, 'qa'),
 ('2026-09-08 08:20', 'QA r5', 3.28, 'qa'),
 ('2026-09-08 09:56', 'restart 3 (4K killed at 94 min)', None, 'stop'),
 ('2026-09-09 14:19', 'QA r6', 3.22, 'qa'),
 ('2026-09-09 17:54', 'QA r7', 3.44, 'qa'),
 ('2026-09-09 19:38', 'restart 4 (context 384k)', None, 'stop'),
 ('2026-09-09 23:33', 'QA r8 (projection)', 3.67, 'qa'),
 ('2026-09-10 01:10', 'QA r9 / Phase 5', 3.67, 'qa'),
 ('2026-09-10 04:00', 'flythrough cut, resume wiped frames', None, 'kill'),
 ('2026-09-10 05:12', 'v1 4K hero', None, 'gate'),
 ('2026-09-10 06:32', 'user finds the arch block', None, 'kill'),
 ('2026-09-10 09:10', 'QA r10 FAIL', 3.56, 'qa'),
 ('2026-09-10 10:31', 'QA r10b PASS', 3.61, 'qa'),
 ('2026-09-10 13:39', 'v2 delivered', None, 'gate'),
]
ev = [(datetime.datetime.fromisoformat(t), l, s, k) for t, l, s, k in events]
t0 = datetime.datetime(2026, 9, 6, 10, 0); t1 = datetime.datetime(2026, 9, 10, 16, 0)
W, HH = 1400, 640; L, R, T, B = 70, 70, 40, 60
def X(t): return L + (t - t0).total_seconds() / (t1 - t0).total_seconds() * (W - L - R)
def iso(t): return t.strftime('%Y-%m-%d %H:%M')
data = {
 'sessions': [{'n': n, 'a': iso(a), 'b': iso(b), 'x0': round(X(a),1), 'x1': round(X(b),1), 'cost': c} for n, a, b, c in sessions],
 'events': [{'t': iso(t), 'x': round(X(t),1), 'label': l, 'score': s, 'kind': k} for t, l, s, k in ev],
 'cost': [{'t': iso(t), 'x': round(X(t),1), 'c': c} for t, c in hourly],
 'daily': daily,
 'days': [{'x': round(X(datetime.datetime(2026,9,dd,0,0)),1), 'label': f'Sep {dd}'} for dd in range(6, 11)],
 'W': W, 'H': HH, 'L': L, 'R': R, 'T': T, 'B': B, 'total': d['grand_cost_usd'],
}
html = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PFA attempt 3 — project timeline</title>
<style>
:root{--bg:#fbfaf7;--fg:#1e1e1e;--mute:#6b6b6b;--grid:#e3e0d8;--sess:#d8cfbf;--qa:#b3552a;--gate:#2b6a8f;--stop:#8c8c8c;--kill:#c0392b;--cost:#4a8a5c}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--fg:#ecebe6;--mute:#a0a0a0;--grid:#2c2c29;--sess:#3a3730;--qa:#e8865c;--gate:#6fb0d8;--stop:#8c8c8c;--kill:#e06060;--cost:#7ec98f}}
body{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);font:14px/1.45 -apple-system,Helvetica,Arial,sans-serif}
h1{font-size:20px;margin:0 0 4px}p{margin:4px 0 12px;color:var(--mute);max-width:1100px}
.wrap{overflow-x:auto}svg{display:block;min-width:900px;max-width:1400px;width:100%}
.lbl{font-size:11px;fill:var(--mute)}.ax{stroke:var(--grid)}.ev text{font-size:10.5px;fill:var(--fg)}
table{border-collapse:collapse;margin-top:16px;font-size:12.5px}td,th{border-bottom:1px solid var(--grid);padding:3px 10px;text-align:left}
.leg span{display:inline-block;margin-right:16px}.leg i{display:inline-block;width:12px;height:12px;vertical-align:-2px;margin-right:5px;border-radius:2px}
</style></head><body>
<h1>Palace of Fine Arts, attempt 3 — sessions, gates, QA rounds, hero score, cumulative cost</h1>
<p>Local time (+02:00), 2026-09-06 to 2026-09-10. Hero score from docs/qa_round_*.md; cumulative nominal API cost from docs/usage/sessions.json (list rates, this project only; total $__TOTAL__). Sessions are the six Claude Code transcripts; grey bands are the gaps between them.</p>
<div class="leg"><span><i style="background:var(--sess)"></i>lead session</span><span><i style="background:var(--qa)"></i>QA round (hero score)</span><span><i style="background:var(--gate)"></i>phase gate / delivery</span><span><i style="background:var(--stop)"></i>stop, restart, checkpoint</span><span><i style="background:var(--kill)"></i>kill / defect</span><span><i style="background:var(--cost)"></i>cumulative cost, $</span></div>
<div class="wrap"><svg id="tl" viewBox="0 0 __W__ __H__" xmlns="http://www.w3.org/2000/svg"></svg></div>
<table id="tbl"><thead><tr><th>#</th><th>session</th><th>start</th><th>end</th><th>wall h</th><th>cost</th></tr></thead><tbody></tbody></table>
<script>
const D=__DATA__;
const svg=document.getElementById('tl');const NS='http://www.w3.org/2000/svg';
function el(n,a,txt){const e=document.createElementNS(NS,n);for(const k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;svg.appendChild(e);return e;}
const W=D.W,H=D.H,L=D.L,R=D.R,T=D.T,B=D.B;
const sessY=T+10,sessH=22;            // session lane
const sT=T+60,sB=H-B-140;             // score lane (y range 2..4)
const cT=sT,cB=sB;                    // cost lane shares vertical space, right axis
const evY=H-B-120;                    // event lane
const scoreY=s=>sB-(s-2)/(4-2)*(sB-sT);
const maxC=Math.ceil(D.total/250)*250;const costY=c=>cB-c/maxC*(cB-cT);
// day grid
for(const d of D.days){el('line',{x1:d.x,x2:d.x,y1:T,y2:H-B,class:'ax','stroke-dasharray':'3 3'});el('text',{x:d.x+4,y:T-8,class:'lbl'},d.label);}
// gaps between sessions
for(let i=0;i<D.sessions.length-1;i++){const a=D.sessions[i],b=D.sessions[i+1];if(b.x0-a.x1>2)el('rect',{x:a.x1,y:sessY,width:b.x0-a.x1,height:sessH,fill:'var(--grid)',opacity:.5});}
// sessions
for(const s of D.sessions){el('rect',{x:s.x0,y:sessY,width:Math.max(2,s.x1-s.x0),height:sessH,fill:'var(--sess)',rx:3});el('text',{x:s.x0+4,y:sessY+15,class:'lbl'},'S'+s.n+' $'+Math.round(s.cost));}
el('text',{x:L,y:sessY-4,class:'lbl'},'lead sessions');
// score axis
for(const s of [2,2.5,3,3.5,4]){el('line',{x1:L,x2:W-R,y1:scoreY(s),y2:scoreY(s),class:'ax'});el('text',{x:L-8,y:scoreY(s)+4,class:'lbl','text-anchor':'end'},s.toFixed(1));}
el('text',{x:L-8,y:sT-10,class:'lbl','text-anchor':'end'},'hero /5');
el('line',{x1:L,x2:W-R,y1:scoreY(4),y2:scoreY(4),stroke:'var(--qa)','stroke-dasharray':'6 4',opacity:.6});
el('text',{x:W-R-4,y:scoreY(4)-4,class:'lbl','text-anchor':'end'},'definition of done 4.0');
// cost axis (right)
for(let c=0;c<=maxC;c+=250){el('text',{x:W-R+8,y:costY(c)+4,class:'lbl'},'$'+c);}
el('text',{x:W-R+8,y:cT-10,class:'lbl'},'cost, cumulative');
// cost line
let p='';for(const q of D.cost){p+=(p?'L':'M')+q.x+' '+costY(q.c)+' ';}
el('path',{d:p,fill:'none',stroke:'var(--cost)','stroke-width':2});
// score line
const qa=D.events.filter(e=>e.score!=null);let sp='';for(const e of qa){sp+=(sp?'L':'M')+e.x+' '+scoreY(e.score)+' ';}
el('path',{d:sp,fill:'none',stroke:'var(--qa)','stroke-width':2.5});
for(const e of qa){el('circle',{cx:e.x,cy:scoreY(e.score),r:4.5,fill:'var(--qa)'});el('text',{x:e.x,y:scoreY(e.score)-9,class:'lbl','text-anchor':'middle',fill:'var(--fg)'},e.score.toFixed(2));}
// events lane with staggered labels
const col={qa:'var(--qa)',gate:'var(--gate)',stop:'var(--stop)',kill:'var(--kill)'};
let lastX=-1e9,row=0;
D.events.forEach((e,i)=>{row=(e.x-lastX<70)?(row+1)%5:0;lastX=e.x;const y=evY+row*20;
 el('line',{x1:e.x,x2:e.x,y1:T+sessH+14,y2:y+6,stroke:col[e.kind],opacity:.35});
 el('circle',{cx:e.x,cy:y+6,r:4,fill:col[e.kind]});
 const g=el('g',{class:'ev'});const t=document.createElementNS(NS,'text');t.setAttribute('x',e.x+7);t.setAttribute('y',y+10);t.textContent=e.label+' · '+e.t.slice(5,16);g.appendChild(t);
});
// table
const tb=document.querySelector('#tbl tbody');
for(const s of D.sessions){const a=new Date(s.a.replace(' ','T')),b=new Date(s.b.replace(' ','T'));const h=((b-a)/36e5).toFixed(1);const tr=document.createElement('tr');tr.innerHTML='<td>'+s.n+'</td><td>lead session</td><td>'+s.a+'</td><td>'+s.b+'</td><td>'+h+'</td><td>$'+s.cost.toFixed(0)+'</td>';tb.appendChild(tr);}
const dr=document.createElement('tr');dr.innerHTML='<td></td><td>daily cost (UTC days)</td><td colspan="4">'+D.daily.map(x=>x[0].slice(5)+' $'+x[1].toFixed(0)).join(' · ')+'</td>';tb.appendChild(dr);
</script>
</body></html>'''
html = html.replace('__DATA__', json.dumps(data)).replace('__W__', str(W)).replace('__H__', str(HH)).replace('__TOTAL__', f'{d["grand_cost_usd"]:,.0f}')
open(os.path.join(H, '..', 'timeline.html'), 'w').write(html)
print('wrote docs/timeline.html', len(html), 'bytes')
