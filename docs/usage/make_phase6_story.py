#!/usr/bin/env python3
"""Build docs/phase6_story.html, the plain-language page for the Phase 6 week, from docs/usage/phase6_audit.json and the
committed images (embedded as data URIs, no external files). Numbers come from phase6_audit.py; the audit
docs/retrospective_phase6.md carries every caveat this page rounds away. Run: python3 docs/usage/make_phase6_story.py"""
import json, os, base64, io, html
from PIL import Image
import numpy as np

H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
A = json.load(open(os.path.join(H, 'phase6_audit.json')))
P6 = A['phase6_only_15_18']; WK = A['week']; P5 = A['phase5']; DAYS = A['days']; WIN = {w['key']: w for w in A['windows']}
SC = A['scores']
EX = json.load(open(os.path.join(H, 'phase6_examples.json')))

# ---------------------------------------------------------------- images (same crops as the audit's contact sheet)
def jpg(im, w=960, q=72):
    im = im.convert('RGB')
    if im.width > w: im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=q, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode(), im.size
def panels(path):
    im = Image.open(os.path.join(ROOT, path)); W, Hh = im.size
    col = np.asarray(im.convert('L')).std(axis=0)
    runs = []; s = None
    for x in range(W + 1):
        g = x < W and col[x] < 2
        if g and s is None: s = x
        if not g and s is not None: runs.append((s, x)); s = None
    b = [0] + [(r[0] + r[1]) // 2 for r in runs if r[1] - r[0] > 4 and 0 < r[0] < W - 1] + [W]
    return [im.crop((b[i], 0, b[i + 1], Hh)) for i in range(len(b) - 1)]
IMG = {}
g1 = panels('renders/web/gate1_pair_cam01.png'); g2 = panels('renders/web/gate2_pair_cam01.png')
IMG['g1_view'], _ = jpg(g1[0]); IMG['g1_cycles'], _ = jpg(g1[1]); IMG['g2_view'], _ = jpg(g2[0]); IMG['g2_cycles'], _ = jpg(g2[1])
for k, p, w in [('g0', 'renders/web/gate0_pair.png', 960), ('g3_before', 'renders/web/960/step0_before_quantfix_hero.jpg', 960), ('g3_after', 'renders/web/960/step0_uvdequant_hero.jpg', 960),
                ('r14', 'renders/web/960/round14_cam01.jpg', 960), ('r15', 'renders/web/960/round15_cam01.jpg', 960), ('r16c', 'renders/web/960/round16c_cam01.jpg', 960),
                ('gate5', 'renders/web/960/gate5_cam01.jpg', 960), ('gate5_tier0', 'renders/web/960/gate5_tier0_cam01.jpg', 960), ('gate7', 'renders/web/960/gate7_cam01.jpg', 960),
                ('gate14', 'renders/web/960/gate14_cam01.jpg', 960), ('loading', 'renders/web/960/round15_loading_screen.jpg', 960),
                ('gate5cm', 'renders/web/960/gate5cm_cam01.jpg', 442), ('gate7m', 'renders/web/960/gate7m_cam01.jpg', 442), ('iphone', 'renders/web/user/iphone16pro_hero_portrait_20260918.jpg', 442),
                ('p5hero', 'renders/final/v2/hero_cam01_3840x2160.png', 960), ('ref169', 'reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg', 960)]:
    IMG[k], _ = jpg(Image.open(os.path.join(ROOT, p)), w)

# ---------------------------------------------------------------- helpers
def esc(s): return html.escape(str(s))
def money(x): return f'${x:,.0f}'
def h1(x): return f'{x:.1f}'
SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
SERIES_D = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767']

def stacked_hbars(rows, series, title, unit='', width=360, fmt=lambda v: f'{v:g}', total_label=True, note='', lab_w=74):
    """rows: [(label, [v1..vn])]; series: names. Inline SVG with legend, 2 px gaps, direct labels on segments >= 12 % of the row max, table fallback."""
    n = len(series); maxv = max(sum(v) for _, v in rows) or 1
    bar_h = 22; gap = 8; top = 6; hgt = top + len(rows) * (bar_h + gap) + 4
    out = [f'<figure class="viz"><figcaption>{esc(title)}</figcaption>', legend(series),
           f'<svg viewBox="0 0 {width} {hgt}" width="100%" role="img" aria-label="{esc(title)}">']
    y = top
    for label, vals in rows:
        x = lab_w; tot = sum(vals)
        out.append(f'<text x="{lab_w - 6}" y="{y + 15}" text-anchor="end" class="lb">{esc(label)}</text>')
        for i, v in enumerate(vals):
            if v <= 0: continue
            w = (width - lab_w - 44) * v / maxv
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w - 2, 0.5):.1f}" height="{bar_h}" rx="3" class="s{i}"><title>{esc(label)}: {esc(series[i])} {fmt(v)}{unit}</title></rect>')
            if w >= 34: out.append(f'<text x="{x + w / 2 - 1:.1f}" y="{y + 15}" text-anchor="middle" class="dl">{fmt(v)}</text>')
            x += w
        if total_label: out.append(f'<text x="{x + 4:.1f}" y="{y + 15}" class="lb">{fmt(tot)}{unit}</text>')
        y += bar_h + gap
    out.append('</svg>')
    out.append('<details class="tbl"><summary>table view</summary><table><tr><th></th>' + ''.join(f'<th>{esc(s)}</th>' for s in series) + '<th>total</th></tr>' +
               ''.join('<tr><td>' + esc(l) + '</td>' + ''.join(f'<td>{fmt(v)}{unit}</td>' for v in vals) + f'<td>{fmt(sum(vals))}{unit}</td></tr>' for l, vals in rows) + '</table></details>')
    if note: out.append(f'<p class="note">{note}</p>')
    out.append('</figure>')
    return '\n'.join(out)

def legend(series):
    if len(series) < 2: return ''
    return '<div class="legend">' + ''.join(f'<span><i class="s{i}"></i>{esc(x)}</span>' for i, x in enumerate(series)) + '</div>'

def slider(a_src, b_src, a_lab, b_lab, sid):
    return f'''<div class="cmp" id="{sid}">
  <div class="cmp-wrap"><img src="{b_src}" alt="{esc(b_lab)}"><img class="cmp-top" src="{a_src}" alt="{esc(a_lab)}" style="clip-path:inset(0 50% 0 0)">
  <span class="tag tl">{esc(a_lab)}</span><span class="tag tr">{esc(b_lab)}</span><div class="cmp-line" style="left:50%"></div></div>
  <input type="range" min="0" max="100" value="50" aria-label="compare {esc(a_lab)} with {esc(b_lab)}">
</div>'''

def side(a_src, b_src, a_lab, b_lab):
    return f'<div class="side"><figure><img src="{a_src}" alt="{esc(a_lab)}"><figcaption>{esc(a_lab)}</figcaption></figure><figure><img src="{b_src}" alt="{esc(b_lab)}"><figcaption>{esc(b_lab)}</figcaption></figure></div>'

def G(term, gloss): return f'<span class="g" tabindex="0">{esc(term)}<span class="gl">{esc(gloss)}</span></span>'

# ---------------------------------------------------------------- numbers
p6cost = P6['cost_usd']; wkcost = WK['cost_usd']; p5cost = P5['cost_usd']
role_rows = [(k, v['cost_usd']) for k, v in P6['by_role'].items()]
ROLE_NAMES = {'viewer engineer': 'viewer builders', 'bake engineer': 'light bakers', 'export engineer': 'exporters', 'lead': 'the lead', 'QA critic': 'critics', 'code reviewer': 'code reviewers', 'materials': 'materials', 'analysis/mechanical': 'helpers'}
day_rows = []
for d in ['2026-09-15', '2026-09-16', '2026-09-17', '2026-09-18', '2026-09-19']:
    v = DAYS[d]; before = v.get('before_start_h', 0)
    day_rows.append((d[5:].replace('-', ' Sep ').lstrip('0') if False else 'Sep ' + str(int(d[8:])), [round(v['agent_work_h'], 1), round(v['gpu_no_agent_h'], 1), round(v['waiting_on_user_h'], 1), round(v['idle_h'] + before, 1)]))
gate_rows = [(lab, [round(WIN[k]['agent_work_h'], 1), round(WIN[k]['gpu_no_agent_h'], 1), round(WIN[k]['waiting_on_user_h'], 1), round(WIN[k]['idle_h'], 1)]) for k, lab in
             [('g0', 'Gate 0'), ('g1', 'Gate 1'), ('g2', 'Gate 2'), ('g3', 'Gate 3'), ('g4', 'Gate 4'), ('6c', 'Foliage'), ('6b', 'Web'), ('p7', 'Phase 7')]]
cost_by_day = [(r[0], [round(DAYS[d]['cost_usd'])]) for r, d in zip(day_rows, ['2026-09-15', '2026-09-16', '2026-09-17', '2026-09-18', '2026-09-19'])]
act = P6['by_activity']
ACT_NAMES = {'running scripts': 'running scripts', 'reading files and logs': 'reading files and logs', 'waiting on tools': 'checking whether jobs finished', 'editing files': 'writing code and notes',
             'reasoning and reporting': 'thinking and reporting', 'viewing images': 'looking at pictures', 'coordination': 'briefing and messaging agents'}
gate_cost = {k: WIN[k]['cost_usd'] for k in WIN}
cpp = {c['step']: c for c in A['cost_per_point']}
share = lambda x: f'{100 * x / wkcost:.0f} %'

# ---------------------------------------------------------------- page
CSS = '''
:root{--bg:#fbfaf7;--ink:#161513;--ink2:#54524d;--mut:#8a8781;--card:#ffffff;--line:#e4e1da;--acc:#2a78d6;--s0:#2a78d6;--s1:#eb6834;--s2:#1baf7a;--s3:#eda100;--s4:#e87ba4;--s5:#008300;--s6:#4a3aa7;--s7:#e34948;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#171716;--ink:#f3f2ee;--ink2:#c3c2b7;--mut:#8f8d85;--card:#1f1f1d;--line:#33322f;--acc:#3987e5;--s0:#3987e5;--s1:#d95926;--s2:#199e70;--s3:#c98500;--s4:#d55181;--s5:#008300;--s6:#9085e9;--s7:#e66767;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#171716;--ink:#f3f2ee;--ink2:#c3c2b7;--mut:#8f8d85;--card:#1f1f1d;--line:#33322f;--acc:#3987e5;--s0:#3987e5;--s1:#d95926;--s2:#199e70;--s3:#c98500;--s4:#d55181;--s5:#008300;--s6:#9085e9;--s7:#e66767;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
main{max-width:720px;margin:0 auto;padding:0 16px 64px}h1{font-size:2rem;line-height:1.15;margin:40px 0 8px}h2{font-size:1.45rem;margin:48px 0 12px;line-height:1.2}h3{font-size:1.1rem;margin:28px 0 8px}
p{margin:10px 0}.lede{font-size:1.15rem;color:var(--ink2)}.kicker{color:var(--mut);font-size:.9rem;text-transform:uppercase;letter-spacing:.06em}
.tiles{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:16px 0}.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}.tile b{display:block;font-size:1.6rem;line-height:1.1}.tile span{color:var(--ink2);font-size:.9rem}
.cmp{margin:16px 0}.cmp-wrap{position:relative;overflow:hidden;border-radius:10px;background:#000}.cmp-wrap img{display:block;width:100%;height:auto}.cmp-top{position:absolute;inset:0}.cmp-line{position:absolute;top:0;bottom:0;width:2px;background:#fff;box-shadow:0 0 0 1px rgba(0,0,0,.4);pointer-events:none}
.cmp input{width:100%;margin:6px 0 0;height:36px;accent-color:var(--acc)}.tag{position:absolute;top:8px;background:rgba(0,0,0,.6);color:#fff;font-size:.8rem;padding:2px 8px;border-radius:6px;pointer-events:none}.tl{left:8px}.tr{right:8px}
.side{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:16px 0}.side figure,figure.plain{margin:0}.side img,figure.plain img{width:100%;height:auto;border-radius:8px;display:block}.side figcaption,figure.plain figcaption,.viz figcaption{font-size:.85rem;color:var(--ink2);margin-top:4px}
.viz{margin:20px 0;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}.viz figcaption{font-weight:600;color:var(--ink);margin:0 0 6px}.viz svg text{fill:var(--ink);font-size:11px}.viz svg .lg{fill:var(--ink2)}.viz svg .lb{fill:var(--ink2)}.viz svg .dl{fill:#fff;font-weight:600}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.85rem;color:var(--ink2);margin:2px 0 8px}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}.legend .s0{background:var(--s0)}.legend .s1{background:var(--s1)}.legend .s2{background:var(--s2)}.legend .s3{background:var(--s3)}.legend .s4{background:var(--s4)}.legend .s5{background:var(--s5)}.legend .s6{background:var(--s6)}.legend .s7{background:var(--s7)}
.viz svg .s0{fill:var(--s0)}.viz svg .s1{fill:var(--s1)}.viz svg .s2{fill:var(--s2)}.viz svg .s3{fill:var(--s3)}.viz svg .s4{fill:var(--s4)}.viz svg .s5{fill:var(--s5)}.viz svg .s6{fill:var(--s6)}.viz svg .s7{fill:var(--s7)}
details{margin:8px 0}summary{cursor:pointer;color:var(--acc)}table{border-collapse:collapse;width:100%;font-size:.88rem;margin:8px 0}th,td{text-align:left;padding:5px 6px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--ink2);font-weight:600}
.day{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:14px 0}.day h3{margin:0 0 6px}.day dl{margin:0}.day dt{font-weight:600;margin-top:8px;color:var(--ink2);font-size:.9rem}.day dd{margin:2px 0 0}
.g{border-bottom:1px dotted var(--acc);cursor:help;position:relative}.g .gl{display:none;position:absolute;left:0;top:1.5em;z-index:5;background:var(--ink);color:var(--bg);padding:8px 10px;border-radius:8px;font-size:.85rem;line-height:1.4;width:min(280px,80vw)}.g:hover .gl,.g:focus .gl{display:block}
code{font-size:.82rem;word-break:break-all}.proof{font-size:.85rem;color:var(--mut)}.proof a{color:var(--acc)}.verdict{border-left:4px solid var(--acc);padding:8px 14px;background:var(--card);border-radius:0 10px 10px 0}
.note{font-size:.85rem;color:var(--ink2)}.big{font-size:2.2rem;font-weight:700;line-height:1.1;margin:8px 0}.ok{color:#008300}.half{color:#c98500}.no{color:#e34948}
a{color:var(--acc)}.glossary dt{font-weight:600;margin-top:10px}.glossary dd{margin:2px 0 0}
'''
JS = '''
document.querySelectorAll('.cmp').forEach(c=>{const r=c.querySelector('input'),t=c.querySelector('.cmp-top'),l=c.querySelector('.cmp-line'),w=c.querySelector('.cmp-wrap');
const set=v=>{t.style.clipPath='inset(0 '+(100-v)+'% 0 0)';l.style.left=v+'%';r.value=v};r.addEventListener('input',()=>set(+r.value));
let d=false;const pos=e=>{const b=w.getBoundingClientRect();const x=(e.touches?e.touches[0].clientX:e.clientX)-b.left;set(Math.max(0,Math.min(100,100*x/b.width)))};
w.addEventListener('pointerdown',e=>{d=true;pos(e)});window.addEventListener('pointermove',e=>{if(d)pos(e)});window.addEventListener('pointerup',()=>d=false);w.addEventListener('touchstart',pos,{passive:true});w.addEventListener('touchmove',pos,{passive:true});});
'''

qa = lambda n: f'<a href="qa_round_{n}.md">QA {n}</a>'
dec = '<a href="decisions.md">decisions.md</a>'; st = '<a href="status.md">status.md</a>'
retro = '<a href="retrospective_phase6.md">the audit</a>'

body = []
body.append(f'''<p class="kicker">Palace of Fine Arts, attempt 3 · Phase 6 · 15 to 19 September 2026</p>
<h1>The model was finished. Why did the phone version take a week?</h1>
<p class="lede">On 10 September a photoreal 3D model of the Palace of Fine Arts was delivered as a Blender file. Five days later it started
becoming a web page you can walk through on an iPhone. This page tells that week day by day: what was tried, what broke, what the machine and
the people were waiting for, and what it cost. The numbers are rounded; {retro} carries every caveat.</p>''')

# ---- prologue
body.append(f'''<h2>Prologue: what existed on 10 September</h2>
<p>Phases 0 to 5 (6 to 10 September) built the palace in {G('Blender', 'free 3D modelling software; the model lives in a single .blend file')}:
the rotunda, the colonnades, the sculpture, trees and water, lit at golden hour, then {G('rendered', 'computed into a still picture by simulating light; one 4K frame of this scene takes 25 to 70 minutes on the Mac')}
from the classic viewpoint across the lagoon (the "hero" view). The work was done by AI agents: one lead session that plans, briefs and merges, and specialist agents it dispatches for a task each; a critic agent scored the result against a photograph on a 5-point rubric, where 5 means "hard to tell from a photo". Drag the handle to compare.</p>
{slider(IMG['p5hero'], IMG['ref169'], 'Cycles render, 10 Sep', 'reference photo', 'cmp-prologue')}
<div class="tiles">
<div class="tile"><b>3.61 / 5</b><span>hero score on 10 Sep, where 5 is "hard to tell from a photo"</span></div>
<div class="tile"><b>{money(p5cost)}</b><span>nominal spend of the five build days, at list prices</span></div>
<div class="tile"><b>{P5['subagents']}</b><span>AI agents dispatched, 5 lead sessions</span></div>
<div class="tile"><b>{h1(P5['agent_work_h'])} h</b><span>hours in which some agent was working, of 100 wall-clock hours</span></div>
</div>
<p class="proof">Proof: <a href="delivery.md">delivery.md</a> (v2 delivery), <a href="qa_round_10b.md">QA 10b</a> (score 3.61), <a href="retrospective.md">retrospective.md</a> (Phase 5 costs), <a href="usage/summary.md">usage/summary.md</a>.</p>
<p class="note">On the "weekly budget": the account is a subscription with a weekly usage meter. That meter is not recorded anywhere in the project,
so this page shows nominal dollars at list prices and shares of the week's spend instead. The audit explains why the one calibration that exists (a
remark on 9 September) cannot be trusted.</p>''')

# ---- why not finished
body.append(f'''<h2>Why a finished 3D model is not a finished web page</h2>
<p>The render on 10 September is a single picture that took the Mac's graphics chip 70 minutes. A walkthrough must draw sixty pictures a second,
on a phone, from any viewpoint. Nothing in the .blend file can do that directly, so the model had to be rebuilt in a second form. The work was split into gates: checkpoints where a critic agent scores the result and reviews it at full zoom before the next step may start. Four steps
did most of the work, and each has a plain name:</p>
<ul>
<li><b>Decimation.</b> The model has 30 million triangles (the tiny flat facets every 3D surface is made of). A phone can draw about 3 million per frame,
so every object was simplified to a tenth of its detail, with the fine detail transferred into a picture pasted on top ({G('normal map', 'an image that stores which way the surface bumps, so a flat triangle still catches light like the carved original')}). Gate 1.</li>
<li><b>Baking.</b> The colours, roughness and the golden-hour light and shadow were computed once in Blender and stored as images ({G('lightmaps', 'pictures of the light falling on each surface, computed once and pasted on, so the phone does not have to simulate light')}),
so the phone only has to look them up. This is the slow part: the light bake alone ran 6.5 hours overnight. Gates 2 and 3.</li>
<li><b>Texture compression.</b> Those baked images added up to 1.4 GB. A phone browser gets about 700 MB, so every image was recompressed into a
format the graphics chip reads directly ({G('KTX2', 'a container for GPU-compressed textures; the file stays small in memory, not only on disk')}) and the first thing you see was cut to 47 MB. Gate 2 and the web step.</li>
<li><b>The iPhone memory limit.</b> iOS Safari kills a page that uses too much memory. The desktop viewer sits at 1.9 GB; the phone version got
a separate, halved set of everything and a 1.5-megapixel drawing cap, and still had to be tested on the actual phone. The web step.</li>
</ul>
<p><b>Which cost the most time here?</b> Not the slow baking, which ran mostly overnight. The expensive part was the hand-offs between the three
specialists: what the baker produced, the exporter packed, and the viewer read had to agree on dozens of small conventions (which corner of a
texture is up, how coordinates are rounded, which name a tree is filed under), and every mismatch was found one step later, by looking at the
pictures, and sent back. The audit counts the loops: four rounds to pass Gate 1, two for Gate 2, two re-bakes, two bake re-runs for the trees,
six web deployments.</p>''')

# ---- who the agents are
def rolecard(name, model, n, cost, does, example, produces):
    return (f'<div class="day"><h3>{name} <span class="note">({model}; {n} in Phase 6, {money(cost)})</span></h3><dl><dt>What it does</dt><dd>{does}</dd>'
            f'<dt>One real task from the week</dt><dd>{example}</dd><dt>What it leaves behind</dt><dd>{produces}</dd></dl></div>')
R = P6['by_role']; nR = P6['subagents_by_role']
body.append('<h2>Who the agents are, and what each one actually does</h2>'
            '<p>Every agent is the same kind of thing: one AI conversation that reads files, runs commands and writes files, in a private copy of the project (a "worktree", so agents cannot overwrite each other). '
            'The job title only sets what it is briefed to do, which tools it may touch, and which model runs it. The lead is the one conversation you talk to; everything else is dispatched by it with a written brief.</p>')
body.append(rolecard('The lead', 'Fable 5.1', '6 sessions', R['lead']['cost_usd'],
    'Reads status.md and the last reports, writes a brief per task (a text file the agent starts from), dispatches agents, watches the bake queue, rebuilds the Blender master file, takes the six screenshots, merges reviewed branches, and writes the status, decisions and delivery notes. It writes no build code beyond 20-line fixes.',
    'On 17 Sep at 09:28 one request dispatched three agents for the foliage pass (bake, export, viewer), each with a brief pointing at docs/briefs/phase6c_*.md: 2,463 output tokens, most of them the three briefs, $0.34.',
    'docs/briefs (28 Phase 6 briefs), docs/status.md, docs/decisions.md (81 entries in the week), docs/delivery.md, the merge commits.'))
body.append(rolecard('Viewer builder', 'Opus 5, high effort', nR.get('viewer engineer', 0), R['viewer engineer']['cost_usd'],
    'Writes the web application in JavaScript with the three.js library: code that downloads the packed model files, builds materials from the baked images, applies the colour treatment, draws the water reflection, fog and bloom, handles walking and the six camera presets, streams the download tiers, plus a screenshot tool that captures the six viewpoints the same way every time. It also measures: frame times, memory, and pixel boxes against the render.',
    'On 17 Sep at 09:41 one request wrote the foliage module (leaf shader with bent normals and translucency, the near-tree switch, impostor modulation): 12,487 output tokens in a single file write, $0.40.',
    'web/src/*.js (the viewer), web/tools/*.sh and *.mjs (captures), web/test (207 tests by the foliage pass), renders/web/round*_cam0N.png (captures), web/README.md.'))
body.append(rolecard('Light baker', 'Opus 5, extra-high effort', nR.get('bake engineer', 0), R['bake engineer']['cost_usd'],
    'Writes and runs the Blender scripts that compute images from the model: lightmaps (light and shadow per surface), material maps (colour, roughness, bumps), the reflection probe, the sky, the tree impostors. Each is a headless Blender job on the graphics chip, run one at a time through a queue script with a status file, and verified afterwards (value ranges, clipped pixels, coverage). It also diagnoses defects in the maps, such as the black ceiling that turned out to be inverted surfaces.',
    'On 16 Sep at 00:19 one request wrote the queue worker script that ran the 65 overnight lightmap jobs: 16,131 output tokens, $0.52. Then it polled the queue for eight hours.',
    'export/bake_*.py, export/bake_queue.sh, export/out/gate3/*.exr and *.ktx2 (the images, not committed), the manifest entries that say how to decode them, export/README.md.'))
body.append(rolecard('Exporter', 'Opus 5, high effort', nR.get('export engineer', 0), R['export engineer']['cost_usd'],
    'Turns the Blender model into web files: chooses which objects ship, simplifies each mesh to its triangle budget, lays out the texture coordinates the bakes need, writes glTF files, packs them with gltfpack and the textures with toktx, and writes the manifests that tell the viewer what exists (later, the download tiers and the phone variant). It writes the checks that the packed files still carry what was put in.',
    'On 15 Sep at 12:08 one request wrote the Gate 1 export-set builder, 692 lines of Python, in one go: 21,167 output tokens, $0.63: the largest piece of output any request produced in the week (the most expensive requests were something else, see "Inside one request").',
    'export/export_set.py, gate*_set.py, gltf_pack.sh, tiers.py, verify_glb.py, export/out/*.glb and manifest.json (not committed), docs/briefs/phase6_budget.md.'))
body.append(rolecard('Critic', 'Opus 5, extra-high effort', nR.get('QA critic', 0), R['QA critic']['cost_usd'],
    'Takes the six captured viewpoints, cuts the hero into six full-resolution tiles and looks at each, writes a probe script that measures pixel boxes (brightness, hue, saturation, grain) against the render, runs the name sweep, and writes the round report with a verdict, scores per viewpoint, and one owner per defect. It never runs Blender or the browser.',
    'On 16 Sep at 16:48 one request, right after viewing a tile, wrote the 247-line measurement probe for round 13: 7,451 output tokens, $0.24. The whole round cost $9.59.',
    'docs/qa_round_11 to 19 (13 reports in Phase 6), scripts/qa_r1N_probe.py, renders/web/round1N_gate.png (the composite).'))
body.append(rolecard('Code reviewer', 'Opus 5', nR.get('code reviewer', 0), R['code reviewer']['cost_usd'],
    'Reads the difference between a branch and main, runs nothing heavier than a test, and writes a review with numbered findings: fix now, or carry. The lead merges only after the fix-now items are closed. Cheap ($2 to $7 each) and the source of most of the bugs caught in the week.',
    'On 16 Sep at 17:11 one request read the viewer diff for the impostor round and reasoned about it: 7,065 output tokens of which 6,913 were thinking, $0.25. That review found the swapped blend weights.',
    'docs/reviews/phase6_*_review.md (32 in Phase 6).'))
body.append('<p class="note">Also in the week: one materials agent (the dome cap and coffer material round in Blender, ' + money(R.get('materials', {}).get('cost_usd', 0)) +
            ') and three Sonnet helpers for mechanical passes (' + money(R.get('analysis/mechanical', {}).get('cost_usd', 0)) + ').</p>')

# ---- the week day by day
def daycard(title, sub, attempted, worked, failed, waiting, cost_line, proof):
    return f'''<div class="day"><h3>{title}</h3><p class="note">{sub}</p><dl>
<dt>Attempted</dt><dd>{attempted}</dd><dt>Worked</dt><dd>{worked}</dd><dt>Failed and redone</dt><dd>{failed}</dd><dt>Waiting</dt><dd>{waiting}</dd><dt>Cost</dt><dd>{cost_line}</dd></dl><p class="proof">Proof: {proof}</p></div>'''
D = lambda d: DAYS[d]
def costline(d, extra=''):
    v = D(d); return f'{h1(v["agent_work_h"])} agent-hours, {money(v["cost_usd"])} nominal ({share(v["cost_usd"])} of the week\'s {money(wkcost)}), {v["subagents_started"]} agents dispatched.{extra}'
body.append('<h2>The week, day by day</h2>')
body.append(stacked_hbars(day_rows, ['agent working', 'chip busy, nobody watching', 'blocked on the user', 'idle, user away'], 'Where each day\'s 24 hours went (hours)', ' h', fmt=lambda v: f'{v:g}',
                          note='Priority when things overlap: agent work first, then the graphics chip, then user waits. "Idle" on 15 Sep is the morning before the first prompt. Source: phase6_audit.py, per-day table.'))
body.append(daycard('Monday 15 September', 'Gates 0, 1 and 2 in one day: 12 hours of near-continuous work',
    f'Build the pipeline end to end on one column and one capital (Gate 0); simplify every object and prove the geometry matches (Gate 1); bake colours and surface into images (Gate 2). Three specialists (bake, export, viewer), a critic and a code reviewer per merge.',
    f'All three gates passed the same day, each branch merged (folded into the main code) after a code review. The vertical slice matched the render to within one pixel of position. The full scene came in at 2.84 million triangles against a 3 million budget. The user made the three scale-up decisions ("go") within seven minutes of being asked.',
    f'Gate 1 failed three times before passing: a backdrop material with an invalid texture slot made 151 000 triangles vanish, three sculpted panels were torn by a bad simplifier, 127 placeholder tree boards hid the building, then 1 379 shrubs were drawn at the world origin. Gate 2 failed once (7 of 12 stone materials shipped without their bump detail), then the replacement detail maps shipped empty, then too faint; three fixes in one evening.',
    f'Graphics chip {h1(D("2026-09-15")["gpu_busy_total_h"])} h busy (ornament bake queue 1.6 h at noon, material bakes in the afternoon), always with an agent polling it. The user was needed for 7 minutes. The overnight light bake started at 22:10.',
    costline('2026-09-15'),
    f'{st} entries of 15 Sep, {qa(11)} to {qa("11d")}, {qa(12)}, {qa("12b")}, commits 70bfe73, 57addb8, 19412e4.'))
body.append(daycard('Tuesday 16 September', 'The light bake, a forced restart, and the viewer gets its light',
    f'Finish the overnight light bake (65 jobs), review it, wire the baked light into the viewer, score it (Gate 3), then the viewer proper: fog, bloom, water, far trees as flat pictures, walking (Gate 4).',
    f'The bake finished before dawn (6.5 hours) with every map usable but one. The critic accepted the lightmaps: the hero frame landed at 97 % of the render\'s brightness. Gate 4 round one closed the two biggest lighting defects.',
    f'The packer had silently stripped the second set of texture coordinates from every file since Gate 1, so the baked light could not attach; found only now and re-packed. The dark hero turned out to be a rounding of those coordinates the viewer had to undo. The rotunda ceiling map was black (its surfaces faced inward) and was re-baked. A merge was blocked because the reflection probe had never been uploaded, so a "closed" defect was reopened and re-measured.',
    f'The lead had passed its own context limit and asked for a restart at 05:34; the user restarted it at 08:48 (3.2 h). The user left twice (09:19 and 17:28) with the next steps written down: {h1(D("2026-09-16")["idle_h"])} h idle. Graphics chip {h1(D("2026-09-16")["gpu_busy_total_h"])} h.',
    costline('2026-09-16'),
    f'{st} entries of 16 Sep, {qa(13)}, {qa(14)}, {dec} entries "Gate 3 hand-off" and "Gate 4 round 5", commits f8c9002, cc14323.'))
body.append(daycard('Wednesday 17 September', 'Parity reached at 01:23; then the foliage pass the user asked for',
    f'Finish Gate 4 (water with real ripples, per-bush lighting), declare the desktop viewer at parity with the render (6a), then a two-round pass on trees and shrubs (6c) because the user found them wrong at close range.',
    f'The critic scored every station within 0.5 of its render score, none below 2.5: the viewer was at parity. The foliage pass gave the tree crowns interiors and brought the shrubs down to the reference brightness.',
    f'The user opened the delivered viewer and saw the test scene: the page\'s default settings were still the Gate 0 development ones. The per-bush light bake had to be run twice (the first used an opaque stand-in that brightened everything by 64 %). The tree bake and the tree export anchored trees at different points, up to 3.4 m apart; far trees were placed 300 m off; both redone.',
    f'Blocked on the user {h1(D("2026-09-17")["waiting_on_user_h"])} h (the 01:23 result waited until 07:10 for a reader). User away {h1(D("2026-09-17")["idle_h"])} h, including 12:54 to 23:16 with QA 17 finishing on its own.',
    costline('2026-09-17'),
    f'{qa(15)}, {qa(16)}, {qa(17)}, {dec} "FINAL JUDGEMENT OF 6a" and "Delivery defect found by the user", commits 212ca27, 5e1fffa, 47a2f7e.'))
body.append(daycard('Thursday 18 September', 'The web deployment, a phone that showed the wrong scene, and a 17-hour question',
    f'Split the 640 MB of assets into three download tiers so the first picture arrives under 50 MB; build a halved set for the iPhone; deploy to a free host; score it on the live address (6b).',
    f'Published to the web host ("deployed") at 18:41. First frame 46.8 MB, three tiers stream the rest, no file over the host\'s 25 MB cap. The phone tier draws the whole scene in 500 MB of memory. The user\'s iPhone 16 Pro showed the hero scene at 20:59.',
    f'The phone version had no building: its seven geometry files were in neither publish list (found by the critic, fixed, redeployed). The phone canvas filled only 70 % of the screen. The bare address drew the test scene on the user\'s phone because the default asset path pointed at an unpublished folder (fixed, deploy 5). Then a sixth deploy so the phone\'s water reflects the building.',
    f'Blocked on the user {h1(D("2026-09-18")["waiting_on_user_h"])} h: the lead had asked its three deployment questions (which iPhone, which host, whether a low-resolution first look is acceptable) at 23:24 the night before, ten hours after the user had left, and got the answer at 16:57. Agents worked {h1(D("2026-09-18")["agent_work_h"])} h.',
    costline('2026-09-18'),
    f'{qa(18)}, {qa("18b")}, {dec} entries "6b" and "Post-close fix", commits 900a846, 98ab252, 1c4b0f5, d40a125, deploy logs renders/logs/6b_deploy_1..6.log.'))
body.append(daycard('Friday 19 September', 'Phase 7: the trees the user saw on the phone; then the next phase starts',
    f'The user sent two screenshots at 08:47: far trees jagged and black-cored on the desktop, close trees flat on the phone. One viewer round on the live site, then a score.',
    f'Both defects closed on the desktop and on the phone by 09:56; the mobile score rose from 2.9 to 3.2 on the hero. Payload unchanged.',
    f'Nothing redone inside Phase 7. Phase 8 (five further art items) started at 12:25 the same day and is outside this page, but it is inside the same week and budget: {money(WIN["p8"]["cost_usd"])} more that day.',
    f'Blocked on the user {h1(D("2026-09-19")["waiting_on_user_h"])} h (overnight until 08:43, then 09:58 to 12:25 after Phase 7 closed).',
    costline('2026-09-19', f' Of this, Phase 7 itself: {money(WIN["p7"]["cost_usd"])}.'),
    f'{qa(19)}, {dec} "PHASE 7 APPROVED" and "PHASE 7 DONE WITH RESIDUALS", commits 91f08b4, 6253d32, user screenshots renders/web/user/phase7_*.png.'))

# ---- gates
body.append('<h2>Each gate: before and after at the hero viewpoint</h2><p>Every gate ends with a critic\'s report and a full-resolution tile review. Each slider shows the same viewpoint; the left image is the viewer.</p>')
body.append(stacked_hbars(gate_rows, ['agent working', 'chip busy, unwatched', 'blocked on the user', 'idle'], 'Wall clock per gate (hours)', ' h', fmt=lambda v: f'{v:g}',
                          note='Gate windows run from one verdict commit to the next; "Web" spans 17 Sep 12:56 to 19 Sep 00:00 and holds the 17.6-hour question. Source: phase6_audit.py, per-window table.'))
def gate(title, img_html, s1, s2, proof, cost, scores):
    return f'<h3>{title}</h3>{img_html}<p>{s1} {s2}</p><p class="proof">Cost {cost}. {scores} Proof: {proof}</p>'
body.append(gate('Gate 0, the vertical slice (15 Sep 09:43 to 11:50)', f'<figure class="plain"><img src="{IMG["g0"]}" alt="Gate 0 pair: viewer, Cycles, difference"><figcaption>One column and one capital: viewer (left), Blender render (middle), difference (right).</figcaption></figure>',
    'Before scaling up, the whole pipeline was run on one column and one capital, and the viewer\'s picture was compared with a Blender render of the same slice: position matched to the pixel, the sky\'s brightness to 1 % and the lit column to within 8 %.',
    'It was hard because the viewer had to reproduce Blender\'s exact colour treatment (a 65-step colour cube baked from Blender itself) before any comparison meant anything.',
    f'<a href="../renders/web/gate0_pair.png">gate0_pair.png</a>, {dec} "Gate 0 verdict", commit 70bfe73.', money(gate_cost['g0']), 'No station scores at this gate.'))
body.append(gate('Gate 1, geometry freeze (15 Sep 11:50 to 16:58)', slider(IMG['g1_view'], IMG['g1_cycles'], 'viewer, grey geometry', 'Blender render', 'cmp-g1'),
    'Every object was simplified to a phone budget and drawn in plain grey so the critic could judge shape alone: the silhouette matched the render to 0.075 % of the frame height.',
    'It took four critic rounds because each export defect hid the next one: an invalid texture slot, torn panels, placeholder boards in the way, then shrubs drawn at the origin.',
    f'{qa(11)}, {qa("11b")}, {qa("11c")}, {qa("11d")}, commit 57addb8.', money(gate_cost['g1']), 'Geometry rows only: hero 3.5 (render 3.61).'))
body.append(gate('Gate 2, materials (15 Sep 16:58 to 21:55)', slider(IMG['g2_view'], IMG['g2_cycles'], 'viewer, materials, no shadow', 'Blender render', 'cmp-g2'),
    'Colour, roughness and surface bumps were baked into images for 60 material sets and the viewer drew them under plain sunlight, no shadows yet, so this comparison is deliberately brighter than the render.',
    'It was hard because half the stone shipped without its bump detail, and the replacement detail layer arrived empty, then too faint, before the third version passed at 100 % zoom.',
    f'{qa(12)}, {qa("12b")}, {st} "Detail re-derivation merged", commit 19412e4.', money(gate_cost['g2']), 'Material rows only; no station average.'))
body.append(gate('Gate 3, the light bake (15 Sep 21:55 to 16 Sep 15:09)', slider(IMG['g3_after'], IMG['g3_before'], 'lightmaps, after the fix', 'lightmaps, first attempt', 'cmp-g3'),
    'The golden-hour light and shadow were computed overnight (65 jobs, 6.5 hours) and pasted onto every surface; on the first attempt the hero came out dark and blue-banded, and after the fix it landed at 97 % of the render\'s brightness.',
    'It was hard because the file packer had quietly stripped the coordinates the light needed and rounded the rest, two behaviours nobody had checked at Gate 0.',
    f'{qa(13)}, {dec} "Gate 3 hand-off" and "Gate 4 round 5 (lead)", commit f8c9002.', money(gate_cost['g3']), 'QA 13 stations: 3.39 / 2.69 / 2.69 / 2.31 / 2.89 / 2.33 (lightmaps alone, not the final look).'))
body.append(gate('Gate 4, the viewer proper (16 Sep 15:09 to 17 Sep 01:23)', slider(IMG['r15'], IMG['r14'], 'round 15, parity', 'round 14', 'cmp-g4'),
    'Fog, bloom, real water ripples, far trees as picture cards and walking were added; between round 14 and round 15 the water stopped being a mirror and the score reached parity with the render at every station.',
    'It was hard because the 45 frames-per-second target could not be met with the water reflection and bloom both on (35.5 fps), so a faster preset was documented instead.',
    f'{qa(14)}, {qa(15)}, {dec} "FINAL JUDGEMENT OF 6a", commit 212ca27.', money(gate_cost['g4']), 'QA 15 stations: 3.72 / 3.00 / 2.56 / 2.88 / 2.94 / 2.83 against the render\'s 3.67 / 2.94 / 2.56 / 2.81 / 3.06 / 2.67.'))
body.append(gate('Foliage pass, 6c (17 Sep 01:23 to 12:56)', slider(IMG['r16c'], IMG['r15'], 'after the foliage pass', 'before', 'cmp-6c'),
    'The user found the trees wrong at close range, so crowns got interiors and translucent leaves, shrubs got a denser near set, and far trees switch to real meshes when you walk up.',
    'It was hard because a tree is baked in one place and exported in another, and the two disagreed about where the tree stood, twice.',
    f'{qa(16)}, {qa(17)}, {dec} "6c CLOSED WITH RESIDUALS", commit 47a2f7e.', money(gate_cost['6c']), 'QA 17: hero 3.78, station 2 up 0.25, the rest unchanged.'))
body.append(gate('Web deployment, 6b (17 Sep 12:56 to 18 Sep 23:35)', slider(IMG['gate5'], IMG['gate5_tier0'], 'after all tiers loaded', 'first frame, 47 MB', 'cmp-6b'),
    'The assets were split into three download tiers so the first picture arrives under 50 MB and sharpens as the rest streams in; a halved set was built for the phone; the site went live on a free host.',
    'It was hard because the phone list of files and the desktop list of files were built separately, and the deployment trusted one of them: the phone tier had no building until the critic looked.',
    f'{qa(18)}, {qa("18b")}, {dec} "6b DONE WITH RESIDUALS", commits 900a846, 98ab252, 1c4b0f5.', money(gate_cost['6b']), 'Desktop unchanged at 3.78; the phone scored for the first time: 2.9 / 3.0 / 2.3 / 2.7 / 2.5 / 2.4.'))
body.append(gate('Phase 7, the trees on the live site (19 Sep 08:43 to 09:56)', slider(IMG['gate7'], IMG['gate5'], 'after Phase 7', 'before', 'cmp-p7'),
    'Far tree edges lost their jagged halo and black cores, and the phone draws real tree meshes within 45 m instead of flat cards.',
    'It was cheap because everything needed was already exported; only the viewer changed.',
    f'{qa(19)}, {dec} "PHASE 7 DONE WITH RESIDUALS", commit 6253d32.', money(gate_cost['p7']), 'Desktop 3.78; phone 3.2 / 3.3 / 2.3 / 2.7 / 2.8 / 2.4.'))
body.append(side(IMG['gate5cm'], IMG['gate7m'], 'phone tier, 18 Sep (headless capture)', 'phone tier, 19 Sep, after Phase 7'))

# ---- result
RESULT_SIDE = side(IMG['iphone'], IMG['gate7'], "the user's iPhone 16 Pro, iOS Safari, 5G, 18 Sep 20:59", 'desktop, the end of the week (19 Sep)')
body.append(f'''<h2>The result</h2>
<p><b>Live viewer:</b> <a href="https://pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev">pfa-walkthrough.3d-render-blender-3rd-attempt-building.workers.dev</a>
(keys 1 to 6 jump to the six viewpoints; walk with the W, A, S and D keys; the phone picks its own download tier).</p>
{RESULT_SIDE}
<div class="tiles">
<div class="tile"><b>46.8 MB</b><span>downloaded before the first picture (limit 50 MB); 581 MB in total over 74 s</span></div>
<div class="tile"><b>8.8 s</b><span>to the first picture on the lead's connection; the phone's own timing was never recorded</span></div>
<div class="tile"><b>500 to 562 MB</b><span>phone memory (limit 700 MB); desktop 1.86 GB</span></div>
<div class="tile"><b>35.5 fps</b><span>frames per second on the desktop at 2560 by 1440 pixels with the full look; target was 45</span></div>
</div>
<table><tr><th>viewpoint</th><th>Blender render (10 Sep)</th><th>viewer, desktop (19 Sep)</th><th>viewer, phone (19 Sep)</th><th>live site today (21 Sep, after Phases 8 and 9)</th></tr>
{''.join(f"<tr><td>{n}</td><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for n,a,b,c,d in zip(['1 hero, lagoon','2 north-east','3 colonnade','4 ceiling','5 south lawn','6 aerial'], SC['phase5_parity_baseline'], SC['p7_qa19_desktop'], SC['p7_qa19_mobile'], ['4.05','3.51','3.08','3.05','3.24','3.07']))}
</table>
<p class="note">Scores are the critic's per-viewpoint averages on the 5-point rubric. The viewer was scored against Blender renders of the same viewpoints, not against the photograph, so "3.78 versus 3.61" means "as good as the render, plus the water and trees it improved", not "closer to a photo". The 21 Sep column is from {qa(25)}, outside this week.</p>
<h3>Was the definition of done met?</h3>
<div class="verdict"><p><b>Mostly, with two honest gaps.</b> The desktop viewer reached parity with the render at all six viewpoints (met), reflects the rotunda, clamps the walk to the ground, shows a loading bar, and its speed and memory were measured (met), but it runs at 35 not 45 frames per second (target missed, documented). The web version loads under 50 MB, streams the rest, and passed a scoring round on the live address (met). The phone version loads on the user's iPhone 16 Pro (met by the user's screenshot); that it <i>walks</i> on the phone was only tested on the Mac in phone mode (not evidenced). Safari on macOS was tested through a WebKit engine build, not Safari itself (not evidenced). The rule that the critic also scores against the photograph was not followed. Full table: {retro}, section 5.</p></div>''')

# ---- tokens picture
role_series = [ROLE_NAMES.get(k, k) for k, _ in role_rows]
body.append('<h2>What the week cost, in one picture</h2>')
body.append(f'<p class="big">{money(p6cost)} nominal for Phase 6 (15 to 18 Sep), {money(wkcost)} for the whole week including Phase 7 and the start of Phase 8.</p>')
body.append(stacked_hbars([('Phase 6', [round(v) for _, v in role_rows])], role_series, 'Who spent it (Phase 6, nominal dollars at list prices)', '', fmt=lambda v: f'{v:,.0f}',
                          note=f'{P6["requests"]:,} AI requests by {P6["subagents"]} agents and 6 lead sessions; {P6["output_tokens"]/1e6:.1f} million words-worth of output tokens, {P6["cache_read_tokens"]/1e9:.2f} billion re-read from cache. A token is roughly three quarters of a word; the price of re-reading cached context is a tenth or less of new text, which is why 96 % of all tokens are cache reads and only a fifth of the cost.'))
body.append('<details><summary>The detail: by day, by model, by activity, and the limits of this attribution</summary>')
body.append(stacked_hbars(cost_by_day, ['nominal USD'], 'By day (whole week)', '', fmt=lambda v: f'{v:,.0f}', total_label=False))
body.append(stacked_hbars([('Phase 6', [round(P6['by_model'].get(m, {}).get('cost_usd', 0)) for m in ['claude-opus-5', 'claude-fable-5-1', 'claude-sonnet-5']])], ['Opus 5 (builders, critics, reviewers)', 'Fable 5.1 (the lead)', 'Sonnet 5 (helpers)'], 'By model', '', fmt=lambda v: f'{v:,.0f}'))
body.append(stacked_hbars([(ACT_NAMES.get(k, k), [round(v['cost_usd'])]) for k, v in act.items()], ['nominal USD'], 'By what the request was doing (Phase 6)', '', fmt=lambda v: f'{v:,.0f}', total_label=False, lab_w=182,
                          note='One label per request by a fixed priority (pictures > waiting > editing > coordination > reading > running > thinking). A fifth of the money went to turns whose job was to check whether a job had finished.'))
body.append(f'''<p class="note"><b>Limits.</b> These are list-price dollars computed from the transcripts, not an invoice; the subscription's weekly meter is not recorded anywhere.
Claude Code's own running tally for the same sessions is 8 to 30 % higher because it prices small side calls the transcripts do not carry. A request that did two things is
counted once. Thinking tokens ({P6['thinking_tokens']/1e6:.1f} million) are inside every bar. See {retro}, section 2.</p></details>''')

# ---- inside one request
def excard(e):
    u = e['usage']
    parts = [('context re-read from cache', u['cache_read']), ('context newly written', u['cache_write']), ('thinking', u['thinking']), ('visible output', u['output'] - u['thinking'])]
    bar = stacked_hbars([('tokens', [v for _, v in parts])], [n for n, _ in parts], e['title'], '', fmt=lambda v: f'{v:,.0f}', total_label=False)
    tool = '<dt>Tool call</dt><dd><code>' + esc(e['tool']) + '</code></dd>' if e['tool'] else ''
    text = '<dt>What it wrote (first lines)</dt><dd>' + esc(e['text']) + '</dd>' if e['text'] else ''
    cost = money(u['cost']) if u['cost'] >= 1 else '$%.2f' % u['cost']
    return ('<div class="day">' + bar + '<dl><dt>Who, when</dt><dd>' + esc(e['role']) + ' on ' + esc(e['model']) + ', ' + esc(e['when']) + '; cost ' + cost + '</dd>' + tool + text +
            '<dt>Thinking</dt><dd>' + f"{u['thinking']:,}" + ' tokens, billed as output; the text of thinking is not stored in the transcript, only its size.</dd></dl></div>')
sp = EX['output_split_share']; cm = EX['cache_misses']
body.append('<h2>Inside one request: what the tokens are</h2>'
            '<p>An agent works in a loop: it sends everything it has seen so far (the brief, every file it read, every result) plus one new instruction, and gets back a reply that ends in either a tool call or a message. '
            'Each trip is one request and is billed in tokens (about three quarters of a word each). Three kinds of tokens are in every request:</p><ul>'
            f"<li><b>Context re-read.</b> The whole conversation so far goes in again, every time. In Phase 6 the typical request re-read {EX['median_cache_read']:,} tokens (about 140 pages). Because it is unchanged, it comes from a cache at a tenth or less of the price of new text.</li>"
            '<li><b>Context newly written.</b> Whatever is new since the last request (a file just read, a command result, a picture) is written into the cache once, at a premium.</li>'
            f"<li><b>Output.</b> What the model produces: its private reasoning (\"thinking\"), the prose you read, and the arguments of the tool it calls, which is where the code, the shell commands and the briefs live. The typical request produced {EX['median_output']:,} output tokens and cost ${EX['median_cost']:.2f}.</li></ul>")
body.append(stacked_hbars([('output', [round(sp['thinking']), round(sp['tool arguments (code, commands, briefs)']), round(sp['prose'])])], ['thinking', 'code, commands and briefs (tool arguments)', 'prose you read'],
                          'What the output tokens of Phase 6 were (share, %)', ' %', fmt=lambda v: f'{v:g}', total_label=False,
                          note='Thinking from the API counter; the visible remainder split between tool arguments and prose by character count. Source: phase6_examples.py.'))
C = EX['concentration']
body.append(f"<p><b>How {money(C['total_cost'])} adds up from requests that cost cents.</b> {C['requests']:,} requests at a mean of ${C['mean_cost']:.2f}. {C['under_025_count']:,} of them cost under 25 cents and together make {money(C['under_025_cost'])}; the most expensive 1 % carries {C['top1pct_share']} % of the money, the top 10 % carries {C['top10pct_share']} %. "
            f"The eight most expensive requests of the phase were not the productive ones: every one was a context re-write after a cold cache, the top two at {money(C['top8'][0]['cost'])} and {money(C['top8'][1]['cost'])}, both by the lead on 16 Sep with a 528,000-token context, producing {C['top8'][0]['output']:,} and {C['top8'][1]['output']:,} output tokens. "
            f"The most expensive request on a warm cache cost {money(C['most_expensive_warm']['cost'])}. The request that produced the most ({C['largest_output']['output']:,} tokens, a whole 692-line script) cost ${C['largest_output']['cost']:.2f}.</p>")
body.append('<p><b>What those tokens became.</b> Lines added to the project on all branches over the four days (docs/usage/phase6_lines.sh): 19,300 in the export and packing scripts, 11,000 in the viewer JavaScript, 6,100 in the bake scripts, 4,900 in the viewer tools and tests, 3,800 in the critic probes, 1,800 each in reviews and briefs, 1,600 in QA reports, 1,100 in the status, decisions and delivery notes. About 55,000 lines that a person could read, plus 820,000 lines of machine-generated capture metadata.</p>')
body.append('<p>Almost none of what the agents produce is prose for a person. Three fifths is code, shell commands and briefs; a third is reasoning that nobody reads. Here are real requests from the week, one per kind of work, with their exact counts.</p>')
for e in EX['examples']:
    if e['kind'] not in ('cache_miss_poll', 'cache_expiry'): body.append(excard(e))
body.append('<h3>The expensive kind of nothing: cache misses</h3>'
            '<p>A subagent\'s cache lives five minutes; the lead\'s, one hour. A poll that sleeps ten minutes and then asks "is the bake done?" comes back to a cold cache and re-writes its entire context at the premium price. '
            f"The same 267-token question then costs two dollars instead of a few cents. In Phase 6, {cm['all']['count']} requests re-wrote more than 100 000 tokens each: {money(cm['all']['cost'])}, {cm['all']['share_of_role_cost']} % of the phase. "
            f"For the light bakers it was {cm['bake engineer']['share_of_role_cost']} % of everything they cost, because they watched hour-long bakes with ten-minute sleeps.</p>")
for e in EX['examples']:
    if e['kind'] in ('cache_miss_poll', 'cache_expiry'): body.append(excard(e))

# ---- compare with phase 5
body.append('<h2>This week against the build week</h2>')
cmp_rows = [('wall clock, h', [round(P5['wall_h']), round(P6['wall_h'])]), ('agent work, h', [round(P5['agent_work_h']), round(P6['agent_work_h'])]), ('chip busy, h', [round(P5['gpu_busy_total_h']), round(P6['gpu_busy_total_h'])]),
            ('blocked on user, h', [round(P5['waiting_on_user_h']), round(P6['waiting_on_user_h'])]), ('idle, h', [round(P5['idle_h']), round(P6['idle_h'] + 9.7)]), ('agents', [P5['subagents'], P6['subagents']]), ('cost, $ x 10', [round(P5['cost_usd'] / 10), round(P6['cost_usd'] / 10)])]
def paired(rows, series, title, note=''):
    width = 360; lab_w = 120; bar_h = 14; maxv = max(max(v) for _, v in rows) or 1; top = 6; hgt = top + len(rows) * (2 * bar_h + 10) + 6
    out = [f'<figure class="viz"><figcaption>{esc(title)}</figcaption>', legend(series), f'<svg viewBox="0 0 {width} {hgt}" width="100%" role="img" aria-label="{esc(title)}">']
    y = top
    for label, vals in rows:
        out.append(f'<text x="{lab_w - 6}" y="{y + bar_h + 4}" text-anchor="end" class="lb">{esc(label)}</text>')
        for i, v in enumerate(vals):
            w = (width - lab_w - 40) * v / maxv
            out.append(f'<rect x="{lab_w}" y="{y + i * (bar_h + 2)}" width="{max(w, 1):.1f}" height="{bar_h}" rx="3" class="s{i}"><title>{esc(label)} {esc(series[i])}: {v}</title></rect><text x="{lab_w + w + 4:.1f}" y="{y + i * (bar_h + 2) + 11}" class="lb">{v}</text>')
        y += 2 * bar_h + 10
    out.append('</svg><details class="tbl"><summary>table view</summary><table><tr><th></th>' + ''.join(f'<th>{esc(s)}</th>' for s in series) + '</tr>' + ''.join('<tr><td>' + esc(l) + '</td>' + ''.join(f'<td>{v}</td>' for v in vals) + '</tr>' for l, vals in rows) + '</table></details>')
    if note: out.append(f'<p class="note">{note}</p>')
    return '\n'.join(out) + '</figure>'
body.append(paired(cmp_rows, ['build week (6 to 10 Sep)', 'Phase 6 (15 to 18 Sep)'], 'Same measures, same scripts',
                   note='Cost shown in tens of dollars so it fits one axis. The build week lost its hours to renders killed by a watchdog and three flat polish rounds; this week lost them to hand-off defects found one gate late and to questions asked after the user had left.'))
body.append(f'''<p>Both weeks cost about the same nominal money ({money(p5cost)} against {money(p6cost)}) and both took about four working days. The build week bought a
score of 3.61 from nothing; this week bought the same score in a medium that runs on a phone. Per point of score gained it was expensive
({money(cpp["g4"]["cost_usd"])} for the only gate that raised the hero score, +0.33), but a walkthrough is not a score, and the points it did gain came from things a still
picture cannot show: rippling water and trees you can walk up to.</p>
<h3>So: what took the time, what did it cost, was it worth it?</h3>
<p><b>Time.</b> 86 hours from the first prompt to the last deploy, of which 34 were agents working, 25 the graphics chip baking (mostly under a watching agent), 30 waiting for
the user, 21 with the user away and nothing blocked. Of the working hours, the largest slices went to a pipeline whose three halves disagreed about small conventions,
each found one gate late.</p>
<p><b>Cost.</b> {money(p6cost)} nominal, 88 % of it Opus 5 builders and critics, 12 % the lead. Whatever the subscription meter said, it was the same order as the build week.</p>
<p><b>Worth it.</b> The stated goal, a walkthrough at parity with the render that loads on an iPhone in under 50 MB, exists at the link above and was scored on the live address. Two
of its promises (a measured walk on the phone itself, Safari proper) were never evidenced, and one rule (score against the photo) was skipped. The user thought it worth
continuing: Phases 7, 8 and 9 followed in the same week and lifted the hero to 4.05.</p>''')

# ---- glossary
body.append('''<h2>Glossary</h2><dl class="glossary">
<dt>Blender, Cycles</dt><dd>Free 3D software; Cycles is its light simulator, which produced the reference renders.</dd>
<dt>Render</dt><dd>A still picture computed by simulating light; minutes to hours per frame. A viewer draws sixty frames a second and cannot simulate light, so light is baked.</dd>
<dt>Triangle</dt><dd>The flat facet every 3D surface is built from. Decimation reduces their number.</dd>
<dt>Normal map, lightmap, texture</dt><dd>Images pasted on surfaces: a texture carries colour, a normal map carries the small bumps, a lightmap carries the baked light and shadow.</dd>
<dt>Bake</dt><dd>Computing something once in Blender (light, colour, bumps) and storing it as an image for the viewer to look up.</dd>
<dt>KTX2, meshopt, gltfpack</dt><dd>Compression formats and the tool that applies them so the files stay small on the wire and in the graphics chip's memory. The packer's defaults caused three of the week's loops.</dd>
<dt>Gate</dt><dd>A checkpoint where a critic agent scores the work on a 5-point rubric and reviews it at 100 % zoom; work moves on only on a pass.</dd>
<dt>Hero</dt><dd>The main viewpoint, from across the lagoon, the one the photograph shows.</dd>
<dt>Deploy, merge</dt><dd>Deploy: publish the built site to the web host. Merge: fold a specialist's branch of changes into the main code after review.</dd>
<dt>Token</dt><dd>The unit AI models read and write in, about three quarters of a word. Re-reading cached context is much cheaper than new text.</dd>
<dt>Nominal cost</dt><dd>What the tokens would cost at public list prices. The account is a subscription, so no invoice matches.</dd>
<dt>Lead, subagent, critic, reviewer</dt><dd>The lead (one AI session) plans and merges; it dispatches specialist subagents (bake, export, viewer), a critic per gate, and a code reviewer before every merge.</dd>
<dt>Tier</dt><dd>A download batch: tier 0 is what you get before the first picture (47 MB), tiers 1 and 2 stream afterwards.</dd>
</dl>
<p class="note">Sources: the git history on every branch, docs/status.md, docs/decisions.md, docs/qa_round_11 to 19, docs/reviews, docs/delivery.md, the render and capture folders, and the Claude Code transcripts (token counts, models, tool calls, timestamps) read by docs/usage/usage_from_transcripts.py. Built by docs/usage/make_phase6_story.py from docs/usage/phase6_audit.json. Times are local (Vienna).</p>''')

page = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Five Days to a Phone</title><meta name="description" content="Why turning the delivered Palace of Fine Arts model into an iPhone web walkthrough took a week, and what it cost.">
<style>{CSS}</style></head><body><main>{''.join(body)}</main><script>{JS}</script></body></html>'''
out = os.path.join(ROOT, 'docs', 'phase6_story.html')
open(out, 'w').write(page)
print(out, f'{os.path.getsize(out)/1e6:.2f} MB')
