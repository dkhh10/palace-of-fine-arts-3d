#!/usr/bin/env python3
"""Phase 6 audit numbers (docs/retrospective_phase6.md and docs/phase6_story.html).
Reads docs/usage/turns_all.json (written by `usage_from_transcripts.py --turns`), git, and the
docs/reviews and docs/qa_round_*.md files. Writes docs/usage/phase6_audit.json and phase6_audit.md.
All times local (+02:00, Vienna). Nothing here reads message text; only timestamps, tool names,
command heads and usage counters.

Attribution rules (stated in the retrospective as limits):
- An agent is ACTIVE from one API request to the next when the gap is <= ACTIVE_GAP seconds, and during
  any blocking tool call. Gaps longer than that are WAITS, attributed by the last command before the gap:
  GPU/tool wait if it launched or polled a Blender, bake-queue or Chrome job (or a CPU tool: toktx, gltfpack,
  npm); the lead waiting on agents if a subagent was active meanwhile; waiting on the user if the gap ends at
  a human prompt and the lead's last message asked a question; idle otherwise.
- Wall-clock partition per window, one minute at a time, priority: agent work > GPU busy > waiting on user > idle.
  GPU busy = the union of GPU waits found above and the documented detached bake queues (DOCUMENTED_GPU).
- Tokens per request are attributed to the window that contains the request timestamp.
"""
import json, os, re, sys, glob, datetime, collections, subprocess

H = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(H))
TZ = datetime.timedelta(hours=2)
ACTIVE_GAP = 180
def loc(ts): return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).replace(tzinfo=None) + TZ
def L(s): return datetime.datetime.fromisoformat(s)

D = json.load(open(os.path.join(H, 'turns_all.json')))
TURNS = D['turns']; CALLS = D['tool_calls']; PROMPTS = D['human_prompts']; AGENTS = D['agents']
for r in TURNS: r['t'] = loc(r['ts'])
for c in CALLS: c['t0'] = loc(c['start']); c['t1'] = loc(c['end'])
for p in PROMPTS: p['t'] = loc(p['ts'])

GPU_PAT = re.compile(r'blender_run|chrome_run|bake_queue|gate\d[a-z]?\.sh|screenshot|MacOS/Blender|--background|until|status\.json|pgrep|sleep \d|watchdog|wait|Blender', re.I)
CPU_TOOL_PAT = re.compile(r'toktx|gltfpack|npm (test|run)|ktx|vite', re.I)

# ---- windows: (key, label, start, end, citation) local time; ends are the commit times of the gate verdicts
WINDOWS = [
 ('g0', 'Gate 0 vertical slice', '2026-09-15 09:43', '2026-09-15 11:50', 'first prompt 07:43Z (11484ff4) -> 70bfe73 Gate 0 merged 11:50'),
 ('g1', 'Gate 1 geometry freeze', '2026-09-15 11:50', '2026-09-15 16:58', '70bfe73 -> 57addb8 QA 11d GATE 1 PASS'),
 ('g2', 'Gate 2 material bake', '2026-09-15 16:58', '2026-09-15 21:55', '57addb8 -> 19412e4 QA 12b GATE 2 PASS'),
 ('g3', 'Gate 3 lightmap bake', '2026-09-15 21:55', '2026-09-16 15:09', '19412e4 -> f8c9002 QA 13 lightmaps accepted'),
 ('g4', 'Gate 4 viewer (6a)', '2026-09-16 15:09', '2026-09-17 01:23', 'f8c9002 -> 212ca27 QA 15 parity'),
 ('6c', '6c foliage pass', '2026-09-17 01:23', '2026-09-17 12:56', '212ca27 -> 47a2f7e QA 17 6c closed'),
 ('6b', '6b web deployment (+6d)', '2026-09-17 12:56', '2026-09-19 00:00', '47a2f7e -> 98ab252 QA 18b (19:48) -> d40a125 6d (23:06) -> session 6 final stop'),
 ('p7', 'Phase 7 foliage look', '2026-09-19 00:00', '2026-09-19 09:56', 'user prompt 08:43 -> 6253d32 QA 19'),
 ('p8', 'Phase 8 (beyond Phase 6, same day)', '2026-09-19 09:56', '2026-09-20 00:00', '6253d32 -> end of 09-19'),
]
WEEK = ('2026-09-15 00:00', '2026-09-20 00:00')
# Hand classification of the no-agent gaps (from the stop states in docs/status.md and the human-prompt timestamps);
# applied in the partition after agent work and GPU. 'user' = blocked on a decision or evidence the user owed;
# 'idle' = the user was away and nothing was blocked on them (the next step was written down).
HAND_GAPS = [
 ('2026-09-15 00:00', '2026-09-15 09:43', 'before', 'Phase 6 had not started (first prompt 09:43)'),
 ('2026-09-16 05:34', '2026-09-16 08:48', 'user', 'restart required by the 350k-context rule; lead stopped at the checkpoint (status.md l.644) and the user restarted at 08:48 ("why do you ask me to restart?")'),
 ('2026-09-16 09:31', '2026-09-16 13:51', 'idle', 'user left 09:19 ("leave in 10 mins"); resume procedure written (status.md l.668); session 3 opened 13:51'),
 ('2026-09-16 17:31', '2026-09-16 22:31', 'idle', 'user left 17:28; stop state written (status.md l.808); session 4 opened 22:31'),
 ('2026-09-17 01:26', '2026-09-17 07:10', 'user', '6a final judgement delivered 01:23; open for the user: default preset and the iPhone (status.md "Open for the user"); user returned 07:10 ("what should i do now?")'),
 ('2026-09-17 08:21', '2026-09-17 08:56', 'idle', 'user left 08:16; session 5 opened 08:56'),
 ('2026-09-17 13:00', '2026-09-17 23:16', 'idle', 'user left 12:54 (QA 17 in flight, told to finish); session 6 opened 23:16'),
 ('2026-09-18 19:51', '2026-09-18 20:42', 'user', '6b done 19:48; owed from the user: Safari screenshot + iPhone walk (status.md l.918); user reported the test-scene defect from the phone ~20:42'),
 ('2026-09-18 21:01', '2026-09-18 22:59', 'user', 'post-close fix deployed 20:43; still owed from the user: phone evidence; user returned 22:59 ("what else needs to get done?")'),
 ('2026-09-18 23:35', '2026-09-19 08:43', 'user', 'final stop state: "Open decision for the user only" (status.md l.928); user returned 08:43 with the two foliage defects'),
 ('2026-09-19 09:58', '2026-09-19 12:25', 'user', 'Phase 7 closed 09:56; nothing scheduled, the user decides (status.md l.941); user returned 12:25 ("Is the job completed or what\'s next?")'),
]
PHASE5 = ('2026-09-06 12:00', '2026-09-10 16:00')   # docs/retrospective.md §2: 09-06 12:41 -> 09-10 15:39 local (v2 delivered 13:39 + notes)
DAYS = ['2026-09-15', '2026-09-16', '2026-09-17', '2026-09-18', '2026-09-19']

# documented detached GPU work that no single agent turn covers (local); cited in the retrospective
DOCUMENTED_GPU = [
 ('2026-09-15 12:27', '2026-09-15 14:03', 'Gate 1 ORN slot-bake queue, 33 jobs, 5 766 s (status.md l.578; launch = export engineer background command 10:27Z)'),
 ('2026-09-15 22:10', '2026-09-16 04:40', 'Gate 3 lightmap queue, 65 jobs in 6 h 30 m, detached overnight (status.md l.644/648)'),
]

# scores per gate end (docs/qa_round_*.md verdict tables); Phase 5 baseline 10b hero 3.61 (retrospective.md), parity table used 3.67 (round 9)
SCORES = {
 'phase5_10b': [3.61, 2.94, 2.56, 2.81, 3.06, 2.67],
 'phase5_parity_baseline': [3.67, 2.94, 2.56, 2.81, 3.06, 2.67],
 'g1_qa11_geometry_only': [3.50, 3.00, 2.60, 3.00, 2.90, 2.80],
 'g3_qa13': [3.39, 2.69, 2.69, 2.31, 2.89, 2.33],
 'g4_qa14': [3.61, 2.94, 2.56, 2.88, 2.83, 2.56],
 'g4_qa15': [3.72, 3.00, 2.56, 2.88, 2.94, 2.83],
 '6c_qa17': [3.78, 3.25, 2.63, 2.88, 2.94, 2.83],
 '6b_qa18b_desktop': [3.78, 3.25, 2.63, 2.88, 2.94, 2.83],
 '6b_qa18b_mobile': [2.9, 3.0, 2.3, 2.7, 2.5, 2.4],
 'p7_qa19_desktop': [3.78, 3.25, 2.63, 2.88, 3.06, 2.83],
 'p7_qa19_mobile': [3.2, 3.3, 2.3, 2.7, 2.8, 2.4],
}

def in_win(t, w): return L(w[0]) <= t < L(w[1])

# ---- per-agent activity intervals and waits
by_agent = collections.defaultdict(list)
for r in TURNS: by_agent[(r['sid'], r['agent'])].append(r)
calls_by_agent = collections.defaultdict(list)
for c in CALLS: calls_by_agent[(c['sid'], c['agent'])].append(c)
active = []      # (t0, t1, key)
waits = []       # dicts: agent, role, t0, t1, kind
prompt_times = sorted(p['t'] for p in PROMPTS)
def prompt_in(t0, t1): return any(t0 <= pt <= t1 + datetime.timedelta(seconds=60) for pt in prompt_times)
for key, rs in by_agent.items():
    rs.sort(key=lambda r: r['t'])
    cs = sorted(calls_by_agent.get(key, []), key=lambda c: c['t0'])
    for c in cs:
        if c['tool'] == 'AskUserQuestion':
            if c['dur_s'] and c['dur_s'] > 60:
                waits.append({'sid': key[0], 'agent': key[1], 'role': rs[0]['role'] if rs else '?', 't0': c['t0'], 't1': c['t1'], 'kind': 'waiting on user', 'last_cmd': 'AskUserQuestion'})
            continue   # a blocking question to the user is a wait, not work
        if c['dur_s'] and c['dur_s'] > 0: active.append((c['t0'], c['t1'], key))
    for i, r in enumerate(rs):
        t0 = r['t'] - datetime.timedelta(seconds=20)
        active.append((t0, r['t'], key))
        if i + 1 < len(rs):
            gap = (rs[i + 1]['t'] - r['t']).total_seconds()
            if gap <= ACTIVE_GAP:
                active.append((r['t'], rs[i + 1]['t'], key))
            else:
                # what was this agent waiting for?
                last = r.get('last_cmd') or ''
                tools = set(r.get('tools') or [])
                # a blocking tool call may cover part of the gap
                blocking = [c for c in cs if c['t0'] >= r['t'] - datetime.timedelta(seconds=5) and c['t0'] <= rs[i + 1]['t']]
                covered = max((c['t1'] for c in blocking), default=r['t'])
                w0 = max(covered, r['t']); w1 = rs[i + 1]['t']
                if (w1 - w0).total_seconds() < 60: continue
                if 'Monitor' in tools or GPU_PAT.search(last):
                    kind = 'gpu wait' if not CPU_TOOL_PAT.search(last) or GPU_PAT.search(last) else 'cpu tool wait'
                elif CPU_TOOL_PAT.search(last):
                    kind = 'cpu tool wait'
                elif 'AskUserQuestion' in tools or (r.get('asks') and prompt_in(w0, w1)):
                    kind = 'waiting on user'
                elif prompt_in(w0, w1):
                    kind = 'idle until user returned'
                else:
                    kind = 'waiting on agents' if r['role'] == 'lead' else 'other wait'
                waits.append({'sid': r['sid'], 'agent': r['agent'], 'role': r['role'], 't0': w0, 't1': w1, 'kind': kind, 'last_cmd': last[:80]})
active.sort()

def minutes_between(a, b):
    t = a.replace(second=0, microsecond=0)
    while t < b:
        yield t
        t += datetime.timedelta(minutes=1)

def cover(intervals, t):
    return any(a <= t < b for a, b, *_ in intervals)

# ---- GPU busy intervals from launches: foreground = the blocking tool call; background = launch -> the agent's next
# task notification (capped at the registered maximum or 2 h); plus the documented detached queues.
GPU_IV = []
for a_ in AGENTS:
    key = (a_['sid'], a_['agent'])
    notes = sorted(loc(t) for t in a_.get('notifications', []))
    cs = calls_by_agent.get(key, [])
    for l in a_.get('launches', []):
        t0 = loc(l['ts'])
        if not l['background']:
            m = [c for c in cs if abs((c['t0'] - t0).total_seconds()) < 2]
            t1 = max((c['t1'] for c in m), default=t0 + datetime.timedelta(seconds=30))
        else:
            nxt = next((n for n in notes if n > t0), None)
            cap = t0 + datetime.timedelta(seconds=min(l['max_s'] or 7200, 7200))
            t1 = min(nxt, cap) if nxt else cap
        GPU_IV.append((t0, t1, key))
GPU_IV += [(L(a), L(b), ('doc', c)) for a, b, c in DOCUMENTED_GPU]
GPU_IV.sort()

def partition(w, detail=False):
    """Minute partition of window w."""
    t0, t1 = L(w[0]), L(w[1])
    act = [(a, b) for a, b, k in active if b >= t0 and a <= t1]
    gpu = [(a, b) for a, b, k in GPU_IV if b >= t0 and a <= t1]
    gpu += [(x['t0'], x['t1']) for x in waits if x['kind'] == 'gpu wait' and x['t1'] >= t0 and x['t0'] <= t1]
    usr = [(x['t0'], x['t1']) for x in waits if x['kind'] == 'waiting on user' and x['role'] == 'lead' and x['t1'] >= t0 and x['t0'] <= t1]
    usr += [(L(a), L(b)) for a, b, k, _ in HAND_GAPS if k == 'user' and L(b) >= t0 and L(a) <= t1]
    before = [(L(a), L(b)) for a, b, k, _ in HAND_GAPS if k == 'before' and L(b) >= t0 and L(a) <= t1]
    cnt = collections.Counter(); lead_wait = 0
    # sort for a faster cover: bucket by minute
    def idx(iv):
        d = collections.defaultdict(bool)
        for a, b in iv:
            for m in minutes_between(max(a, t0), min(b, t1)): d[m] = True
        return d
    A, G, U, B = idx(act), idx(gpu), idx(usr), idx(before)
    for m in minutes_between(t0, t1):
        if A.get(m): cnt['agent work'] += 1
        elif G.get(m): cnt['gpu busy, no agent active'] += 1
        elif U.get(m): cnt['waiting on user'] += 1
        elif B.get(m): cnt['before start'] += 1
        else: cnt['idle'] += 1
    total = (t1 - t0).total_seconds() / 60
    gpu_raw = sum(1 for m in minutes_between(t0, t1) if G.get(m))
    return {'wall_h': round(total / 60, 2), 'agent_work_h': round(cnt['agent work'] / 60, 2), 'gpu_no_agent_h': round(cnt['gpu busy, no agent active'] / 60, 2),
            'gpu_busy_total_h': round(gpu_raw / 60, 2), 'waiting_on_user_h': round(cnt['waiting on user'] / 60, 2), 'idle_h': round(cnt['idle'] / 60, 2), 'before_start_h': round(cnt['before start'] / 60, 2)}

def tokens_in(w, key=None):
    tot = collections.Counter(); cost = collections.Counter(); n = 0
    for r in TURNS:
        if not in_win(r['t'], w): continue
        k = key(r) if key else 'all'
        cost[k] += r['cost_usd']; tot[k] += r['output']; n += 1
    return cost, tot, n

def usage_sum(rows):
    u = collections.Counter()
    for r in rows:
        for k in ('input', 'output', 'cw5m', 'cw1h', 'cread', 'thinking'): u[k] += r[k]
        u['cost'] += r['cost_usd']; u['requests'] += 1
    return u

OUT = {'generated': datetime.datetime.now().isoformat(timespec='seconds'), 'active_gap_s': ACTIVE_GAP, 'windows': [], 'days': {}, 'documented_gpu': DOCUMENTED_GPU, 'hand_gaps': HAND_GAPS, 'scores': SCORES}

# ---- per window
prev_hero = SCORES['phase5_10b'][0]
for key, label, a, b, cite in WINDOWS:
    w = (a, b)
    part = partition(w)
    rows = [r for r in TURNS if in_win(r['t'], w)]
    u = usage_sum(rows)
    byrole = collections.defaultdict(list)
    for r in rows: byrole[r['role']].append(r)
    role_cost = {k: round(usage_sum(v)['cost'], 2) for k, v in byrole.items()}
    bymodel = collections.defaultdict(list)
    for r in rows: bymodel[r['model']].append(r)
    model_cost = {k: round(usage_sum(v)['cost'], 2) for k, v in bymodel.items()}
    agents = sorted({(r['sid'], r['agent']) for r in rows if r['agent'] != 'lead'})
    ag_hours = 0.0
    for a_ in AGENTS:
        if a_['agent'] == 'lead' or not a_['first']: continue
        f, l = loc(a_['first']), loc(a_['last'])
        s, e = max(f, L(a)), min(l, L(b))
        if e > s: ag_hours += (e - s).total_seconds() / 3600
    lead_rows = [r for r in rows if r['role'] == 'lead']
    lead_span = 0.0
    if lead_rows:
        ls = sorted(r['t'] for r in lead_rows); lead_span = (ls[-1] - ls[0]).total_seconds() / 3600
    wk = collections.Counter()
    for x in waits:
        s, e = max(x['t0'], L(a)), min(x['t1'], L(b))
        if e > s: wk[(x['role'], x['kind'])] += (e - s).total_seconds() / 3600
    OUT['windows'].append({'key': key, 'label': label, 'start': a, 'end': b, 'citation': cite, **part,
        'requests': u['requests'], 'output_tokens': u['output'], 'thinking_tokens': u['thinking'], 'cache_read_tokens': u['cread'],
        'cache_write_tokens': u['cw5m'] + u['cw1h'], 'cost_usd': round(u['cost'], 2), 'cost_by_role': role_cost, 'cost_by_model': model_cost,
        'subagents': len(agents), 'subagent_hours_sum': round(ag_hours, 2), 'lead_thread_span_h': round(lead_span, 2),
        'waits_h_by_role_kind': {f'{k[0]} | {k[1]}': round(v, 2) for k, v in sorted(wk.items(), key=lambda x: -x[1]) if v >= 0.05}})

# ---- per day (week) and the week total, plus Phase 5 on the same measures
for d in DAYS:
    w = (d + ' 00:00', (L(d + ' 00:00') + datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M'))
    rows = [r for r in TURNS if in_win(r['t'], w)]
    u = usage_sum(rows)
    part = partition(w)
    byrole = collections.defaultdict(list)
    for r in rows: byrole[r['role']].append(r)
    bymodel = collections.defaultdict(list)
    for r in rows: bymodel[r['model']].append(r)
    byact = collections.defaultdict(list)
    for r in rows: byact[r['activity']].append(r)
    OUT['days'][d] = {**part, 'requests': u['requests'], 'output_tokens': u['output'], 'thinking_tokens': u['thinking'], 'cache_read_tokens': u['cread'],
                      'cache_write_tokens': u['cw5m'] + u['cw1h'], 'cost_usd': round(u['cost'], 2),
                      'cost_by_role': {k: round(usage_sum(v)['cost'], 2) for k, v in byrole.items()},
                      'cost_by_model': {k: round(usage_sum(v)['cost'], 2) for k, v in bymodel.items()},
                      'cost_by_activity': {k: round(usage_sum(v)['cost'], 2) for k, v in byact.items()},
                      'output_by_activity': {k: usage_sum(v)['output'] for k, v in byact.items()},
                      'subagents_started': sum(1 for a_ in AGENTS if a_['agent'] != 'lead' and a_['first'] and loc(a_['first']).strftime('%Y-%m-%d') == d),
                      'human_prompts': sum(1 for p in PROMPTS if p['t'].strftime('%Y-%m-%d') == d)}

def block(w, name):
    rows = [r for r in TURNS if in_win(r['t'], w)]
    u = usage_sum(rows)
    part = partition(w)
    res = {'window': list(w), **part, 'requests': u['requests'], 'input_tokens': u['input'], 'output_tokens': u['output'], 'thinking_tokens': u['thinking'],
           'cache_read_tokens': u['cread'], 'cache_write_tokens': u['cw5m'] + u['cw1h'], 'cost_usd': round(u['cost'], 2)}
    for dim, f in (('role', lambda r: r['role']), ('model', lambda r: r['model']), ('activity', lambda r: r['activity']), ('day', lambda r: r['t'].strftime('%Y-%m-%d')),
                   ('role_model', lambda r: f"{r['role']} | {r['model']}"), ('role_activity', lambda r: f"{r['role']} | {r['activity']}")):
        g = collections.defaultdict(list)
        for r in rows: g[f(r)].append(r)
        res['by_' + dim] = {k: {'requests': len(v), 'output': usage_sum(v)['output'], 'thinking': usage_sum(v)['thinking'], 'cache_read': usage_sum(v)['cread'],
                                'cache_write': usage_sum(v)['cw5m'] + usage_sum(v)['cw1h'], 'cost_usd': round(usage_sum(v)['cost'], 2)} for k, v in sorted(g.items(), key=lambda x: -usage_sum(x[1])['cost'])}
    ag = [a_ for a_ in AGENTS if a_['agent'] != 'lead' and a_['first'] and in_win(loc(a_['first']), w)]
    res['subagents'] = len(ag)
    res['subagents_by_role'] = dict(collections.Counter(a_['role'] for a_ in ag))
    res['subagents_by_model'] = dict(collections.Counter(a_['model'] for a_ in ag))
    res['human_prompts'] = sum(1 for p in PROMPTS if in_win(p['t'], w))
    res['images_viewed_requests'] = sum(1 for r in rows if r['activity'] == 'viewing images')
    wk = collections.Counter()
    for x in waits:
        s, e = max(x['t0'], L(w[0])), min(x['t1'], L(w[1]))
        if e > s: wk[x['kind']] += (e - s).total_seconds() / 3600
    res['wait_hours_by_kind_all_agents'] = {k: round(v, 2) for k, v in wk.most_common()}
    lead_sessions = sorted({r['sid'] for r in rows if r['role'] == 'lead'})
    res['lead_sessions'] = lead_sessions
    OUT[name] = res
block(WEEK, 'week')
block(PHASE5, 'phase5')
block(('2026-09-15 00:00', '2026-09-19 00:00'), 'phase6_only_15_18')

# ---- lead thread: cache re-read at session starts (restart cost), per session in the week
restarts = []
for sid in OUT['week']['lead_sessions']:
    rows = sorted([r for r in TURNS if r['sid'] == sid and r['role'] == 'lead'], key=lambda r: r['t'])
    if not rows: continue
    t0 = rows[0]['t']; first15 = [r for r in rows if (r['t'] - t0).total_seconds() <= 900]
    restarts.append({'sid': sid[:8], 'start': t0.strftime('%m-%d %H:%M'), 'end': rows[-1]['t'].strftime('%m-%d %H:%M'), 'requests': len(rows),
                     'first15min_cache_write': sum(r['cw5m'] + r['cw1h'] for r in first15), 'first15min_cost': round(sum(r['cost_usd'] for r in first15), 2),
                     'lead_cost': round(sum(r['cost_usd'] for r in rows), 2), 'max_context_tokens': max(r['cread'] + r['cw5m'] + r['cw1h'] + r['input'] for r in rows)})
OUT['lead_sessions_week'] = restarts

# ---- rework: reviews and verdicts, QA rounds per gate, git commit subjects with rework words
rev = []
for f in sorted(glob.glob(os.path.join(ROOT, 'docs/reviews/phase6*_review.md')) + glob.glob(os.path.join(ROOT, 'docs/reviews/phase7*_review.md'))):
    s = open(f, errors='replace').read()
    m = re.search(r'MERGE WITH FIXES|MERGE AFTER FIXES|MERGE BLOCKED|SEND BACK|DO NOT MERGE|\bMERGE\b', s)
    fixnow = len(re.findall(r'(?i)fix[- ]now', s))
    rev.append({'file': os.path.basename(f), 'verdict': m.group(0) if m else '?', 'fix_now_mentions': fixnow, 'lines': s.count('\n')})
OUT['reviews'] = rev
OUT['review_verdicts'] = dict(collections.Counter(r['verdict'] for r in rev))
qa = []
for f in sorted(glob.glob(os.path.join(ROOT, 'docs/qa_round_1[1-9]*.md'))):
    s = open(f, errors='replace').read(); head = s.split('\n', 1)[0]
    qa.append({'file': os.path.basename(f), 'title': head[:160], 'lines': s.count('\n')})
OUT['qa_rounds'] = qa
def git(*args):
    return subprocess.run(['git', '-C', ROOT] + list(args), capture_output=True, text=True).stdout
RW = re.compile(r'fix|re-(bake|export|pack|capture|run|derive|review|sync|lay|measure)|revert|WIP|again|correct|blocker|send back|withdrawn|refuted', re.I)
commits = {}
for d in DAYS:
    subj = [l for l in git('log', '--all', f'--since={d}T00:00:00', f'--until={d}T23:59:59', '--format=%s').split('\n') if l]
    merges = [l for l in git('log', 'main', '--merges', f'--since={d}T00:00:00', f'--until={d}T23:59:59', '--format=%h').split('\n') if l]
    commits[d] = {'all_branches': len(subj), 'rework_words': sum(1 for l in subj if RW.search(l)), 'merges_into_main': len(merges)}
OUT['commits_by_day'] = commits
p5 = [l for l in git('log', '--all', '--since=2026-09-06T00:00:00', '--until=2026-09-10T23:59:59', '--format=%s').split('\n') if l]
OUT['commits_phase5'] = {'all_branches': len(p5), 'rework_words': sum(1 for l in p5 if RW.search(l)),
                         'merges_into_main': len([l for l in git('log', 'main', '--merges', '--since=2026-09-06T00:00:00', '--until=2026-09-10T23:59:59', '--format=%h').split('\n') if l])}

# ---- cost per point of station score
def mean6(v): return round(sum(v) / 6, 3)
steps = [('g1', 'phase5_10b', 'g1_qa11_geometry_only'), ('g3', 'g1_qa11_geometry_only', 'g3_qa13'), ('g4', 'g3_qa13', 'g4_qa15'), ('6c', 'g4_qa15', '6c_qa17'), ('6b', '6c_qa17', '6b_qa18b_desktop'), ('p7', '6b_qa18b_desktop', 'p7_qa19_desktop')]
wcost = {w['key']: w['cost_usd'] for w in OUT['windows']}
wcost['g3'] += wcost['g2']  # Gate 2 has no station scores; its cost is carried into the Gate 3 step
cpp = []
for k, a, b in steps:
    dh = round(SCORES[b][0] - SCORES[a][0], 2); dm = round(mean6(SCORES[b]) - mean6(SCORES[a]), 3)
    cpp.append({'step': k, 'from': a, 'to': b, 'hero_delta': dh, 'mean6_delta': dm, 'cost_usd': round(wcost[k], 2),
                'usd_per_hero_point': (round(wcost[k] / dh) if dh > 0 else None), 'usd_per_mean6_point': (round(wcost[k] / dm) if dm > 0 else None)})
OUT['cost_per_point'] = cpp

# ---- global intervals with no agent active (>= 30 min) in the week, for the hand classification in the retrospective
gaps = []
t0, t1 = L(WEEK[0]), L(WEEK[1])
A = collections.defaultdict(bool)
for a, b, k in active:
    for m in minutes_between(max(a, t0), min(b, t1)): A[m] = True
cur = None
for m in minutes_between(t0, t1):
    if not A.get(m):
        if cur is None: cur = m
    else:
        if cur is not None and (m - cur).total_seconds() >= 1800:
            nxt = next((p for p in PROMPTS if cur <= p['t'] <= m + datetime.timedelta(minutes=2)), None)
            lead_prev = [r for r in TURNS if r['role'] == 'lead' and r['t'] <= cur]
            lp = max(lead_prev, key=lambda r: r['t']) if lead_prev else None
            gpu_here = any(a <= m and b >= cur for a, b, k in GPU_IV)
            gaps.append({'start': cur.strftime('%m-%d %H:%M'), 'end': m.strftime('%m-%d %H:%M'), 'hours': round((m - cur).total_seconds() / 3600, 2),
                         'ended_by_human_prompt': bool(nxt), 'lead_last_asked': bool(lp and lp.get('asks')), 'lead_last_tools': (lp or {}).get('tools'), 'gpu_running': gpu_here})
        cur = None
OUT['no_agent_gaps_week'] = gaps
json.dump(OUT, open(os.path.join(H, 'phase6_audit.json'), 'w'), indent=1, default=str)

# ---- markdown tables
M = []
M.append(f"# Phase 6 audit tables (generated {OUT['generated']} by docs/usage/phase6_audit.py from turns_all.json; local time +02:00)\n")
M.append('## Wall clock per window (hours; partition priority agent work > GPU busy > waiting on user > idle)\n')
M.append('| window | span | wall | agent work | GPU busy, no agent | GPU busy total (overlaps) | waiting on user | idle | subagents | sum of subagent lifetimes | requests | cost USD |')
M.append('|---|---|---|---|---|---|---|---|---|---|---|---|')
for w in OUT['windows']:
    M.append(f"| {w['label']} | {w['start'][5:]} -> {w['end'][5:]} | {w['wall_h']} | {w['agent_work_h']} | {w['gpu_no_agent_h']} | {w['gpu_busy_total_h']} | {w['waiting_on_user_h']} | {w['idle_h']} | {w['subagents']} | {w['subagent_hours_sum']} | {w['requests']} | {w['cost_usd']:,.0f} |")
M.append('\n## Waits by role and kind per window (hours, overlapping)\n')
for w in OUT['windows']:
    M.append(f"- {w['label']}: " + '; '.join(f'{k} {v}' for k, v in w['waits_h_by_role_kind'].items()))
M.append('\n## Per day\n')
M.append('| day | wall | agent work | GPU no agent | GPU total | waiting on user | idle | subagents started | human prompts | requests | output k | cache read M | cost USD |')
M.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for d, v in OUT['days'].items():
    M.append(f"| {d} | {v['wall_h']} | {v['agent_work_h']} | {v['gpu_no_agent_h']} | {v['gpu_busy_total_h']} | {v['waiting_on_user_h']} | {v['idle_h']} | {v['subagents_started']} | {v['human_prompts']} | {v['requests']} | {v['output_tokens']/1000:,.0f} | {v['cache_read_tokens']/1e6:,.1f} | {v['cost_usd']:,.0f} |")
for name in ('week', 'phase6_only_15_18', 'phase5'):
    b = OUT[name]
    M.append(f"\n## {name}: {b['window'][0]} -> {b['window'][1]}\n")
    M.append(f"wall {b['wall_h']} h, agent work {b['agent_work_h']} h, GPU busy (no agent) {b['gpu_no_agent_h']} h, GPU busy total {b['gpu_busy_total_h']} h, waiting on user {b['waiting_on_user_h']} h, idle {b['idle_h']} h; "
             f"{b['requests']} requests, output {b['output_tokens']/1e6:.2f} M, thinking {b['thinking_tokens']/1e6:.2f} M, cache read {b['cache_read_tokens']/1e6:,.0f} M, cache write {b['cache_write_tokens']/1e6:.1f} M, cost ${b['cost_usd']:,.0f}; "
             f"{b['subagents']} subagents {b['subagents_by_role']}; models {b['subagents_by_model']}; human prompts {b['human_prompts']}; image-viewing requests {b['images_viewed_requests']}; waits by kind {b['wait_hours_by_kind_all_agents']}\n")
    for dim in ('role', 'model', 'activity', 'day', 'role_model'):
        M.append(f'| {dim} | requests | output k | thinking k | cache read M | cache write M | cost USD | share |')
        M.append('|---|---|---|---|---|---|---|---|')
        tot = sum(v['cost_usd'] for v in b['by_' + dim].values()) or 1
        for k, v in b['by_' + dim].items():
            M.append(f"| {k} | {v['requests']} | {v['output']/1000:,.0f} | {v['thinking']/1000:,.0f} | {v['cache_read']/1e6:,.1f} | {v['cache_write']/1e6:,.2f} | {v['cost_usd']:,.0f} | {100*v['cost_usd']/tot:.0f} % |")
        M.append('')
M.append('## Gaps with no agent active (>= 30 min) in the week\n')
M.append('| start | end | hours | ended by a human prompt | lead had asked a question | lead last tools | GPU running |'); M.append('|---|---|---|---|---|---|---|')
for g in gaps: M.append(f"| {g['start']} | {g['end']} | {g['hours']} | {g['ended_by_human_prompt']} | {g['lead_last_asked']} | {g['lead_last_tools']} | {g['gpu_running']} |")
M.append('')
M.append('## Lead sessions in the week (restart cost = cache written in the first 15 minutes)\n')
M.append('| session | start | end | lead requests | first-15-min cache write k | first-15-min cost | lead cost | max context tokens |')
M.append('|---|---|---|---|---|---|---|---|')
for r in restarts:
    M.append(f"| {r['sid']} | {r['start']} | {r['end']} | {r['requests']} | {r['first15min_cache_write']/1000:,.0f} | {r['first15min_cost']} | {r['lead_cost']} | {r['max_context_tokens']:,} |")
M.append('\n## Reviews (docs/reviews/phase6*, phase7*)\n')
M.append(f"verdicts: {OUT['review_verdicts']}; fix-now mentions total {sum(r['fix_now_mentions'] for r in rev)}\n")
M.append('| review | verdict | fix-now mentions | lines |'); M.append('|---|---|---|---|')
for r in rev: M.append(f"| {r['file']} | {r['verdict']} | {r['fix_now_mentions']} | {r['lines']} |")
M.append('\n## QA rounds 11-19\n')
for q in qa: M.append(f"- {q['file']} ({q['lines']} lines): {q['title']}")
M.append('\n## Commits per day (all branches) and rework-flavoured subjects\n')
M.append('| day | commits | rework words | merges into main |'); M.append('|---|---|---|---|')
for d, v in commits.items(): M.append(f"| {d} | {v['all_branches']} | {v['rework_words']} | {v['merges_into_main']} |")
M.append(f"| Phase 5 (09-06..09-10) | {OUT['commits_phase5']['all_branches']} | {OUT['commits_phase5']['rework_words']} | {OUT['commits_phase5']['merges_into_main']} |")
M.append('\n## Cost per point of station score\n')
M.append('| step | from | to | hero delta | mean-of-six delta | cost USD | USD per hero point | USD per mean-of-six point |'); M.append('|---|---|---|---|---|---|---|---|')
for c in cpp: M.append(f"| {c['step']} | {c['from']} | {c['to']} | {c['hero_delta']:+.2f} | {c['mean6_delta']:+.3f} | {c['cost_usd']:,.0f} | {c['usd_per_hero_point'] or 'n/a (no gain)'} | {c['usd_per_mean6_point'] or 'n/a (no gain)'} |")
open(os.path.join(H, 'phase6_audit.md'), 'w').write('\n'.join(M) + '\n')
print('\n'.join(M[:60]))
