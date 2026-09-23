#!/usr/bin/env python3
"""Pick one real API request per activity from the Phase 6 week transcripts and write docs/usage/phase6_examples.json
for the story page ("Inside one request"). Excerpts are short (model output only: thinking, text, tool arguments);
usage numbers are the API's own counters for that request. Run: python3 docs/usage/phase6_examples.py [--list]"""
import json, os, glob, sys, re, datetime, collections, subprocess
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.argv_backup = sys.argv[:]; sys.argv = [sys.argv[0]]
sys.path.insert(0, H)
import usage_from_transcripts as U   # runs the summary once (idempotent), gives PROJ, cost(), classify_activity, role_of_agent
sys.argv = sys.argv_backup
TZ = datetime.timedelta(hours=2)
SESS = ['6460c313', 'c47a8492', '87d95e57', '5b1d192d', '4133edbe', '3ada03f9']

def requests_of(path, role, agent):
    seen = {}; order = []; last_img = False
    with open(path, errors='replace') as f:
        for line in f:
            try: o = json.loads(line)
            except Exception: continue
            t = o.get('type')
            if t == 'user':
                m = o.get('message') or {}; cc = m.get('content')
                img = False
                if isinstance(cc, list):
                    for c in cc:
                        if isinstance(c, dict) and c.get('type') == 'tool_result':
                            inner = c.get('content')
                            if isinstance(inner, list) and any(isinstance(x, dict) and x.get('type') == 'image' for x in inner): img = True
                last_img = img; continue
            if t != 'assistant': continue
            m = o.get('message') or {}; mid = m.get('id') or o.get('uuid'); u = m.get('usage')
            r = seen.get(mid)
            if r is None:
                r = {'ts': o.get('timestamp'), 'role': role, 'agent': agent, 'model': m.get('model'), 'thinking': '', 'text': '', 'tools': [], 'image_in': last_img, 'u': None}
                seen[mid] = r; order.append(mid)
            for c in m.get('content') or []:
                if not isinstance(c, dict): continue
                if c.get('type') == 'thinking': r['thinking'] += c.get('thinking') or ''
                elif c.get('type') == 'text': r['text'] += c.get('text') or ''
                elif c.get('type') == 'tool_use': r['tools'].append((c.get('name'), c.get('input') or {}))
            if u and (r['u'] is None or (u.get('output_tokens') or 0) >= (r['u'].get('output_tokens') or 0)): r['u'] = u
    out = []
    for mid in order:
        r = seen[mid]; u = r['u'] or {}
        cc = u.get('cache_creation') or {}
        r['usage'] = {'input': u.get('input_tokens', 0) or 0, 'output': u.get('output_tokens', 0) or 0, 'thinking': ((u.get('output_tokens_details') or {}).get('thinking_tokens', 0) or 0),
                      'cache_read': u.get('cache_read_input_tokens', 0) or 0, 'cache_write': (cc.get('ephemeral_1h_input_tokens', 0) or 0) + (cc.get('ephemeral_5m_input_tokens', 0) or 0) + (0 if cc else (u.get('cache_creation_input_tokens', 0) or 0))}
        r['usage']['cost'] = U.cost(r['model'], {'input': r['usage']['input'], 'output': r['usage']['output'], 'cw5m': r['usage']['cache_write'] if not cc else (cc.get('ephemeral_5m_input_tokens', 0) or 0), 'cw1h': (cc.get('ephemeral_1h_input_tokens', 0) or 0), 'cread': r['usage']['cache_read']}) or 0
        cmds = [(n, (i.get('command') or i.get('file_path') or i.get('description') or '') if isinstance(i, dict) else '') for n, i in r['tools']]
        r['activity'] = U.classify_activity([n for n, _ in r['tools']], r['image_in'], cmds)
        out.append(r)
    return out

ALL = []
for s in SESS:
    main = glob.glob(os.path.join(U.PROJ, s + '*.jsonl'))[0]; sid = os.path.basename(main)[:-6]
    ALL += requests_of(main, 'lead', 'lead')
    for sa in sorted(glob.glob(os.path.join(U.PROJ, sid, 'subagents', '*.jsonl'))):
        meta = {}
        mp = sa[:-6] + '.meta.json'
        if os.path.exists(mp): meta = json.load(open(mp))
        ALL += requests_of(sa, U.role_of_agent(meta.get('description')), (meta.get('description') or '')[:60])
ALL = [r for r in ALL if r['ts'] and '2026-09-15' <= r['ts'][:10] <= '2026-09-18' and r['usage']['output'] > 0]

def loc(ts): return (datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).replace(tzinfo=None) + TZ).strftime('%d Sep %H:%M')
def head(s, n): s = re.sub(r'\s+', ' ', (s or '').replace('\u2014', ',')).strip(); return s[:n] + ('...' if len(s) > n else '')   # em dashes in quoted output become commas (page rule)

if '--list' in sys.argv_backup:
    for act in ['reasoning and reporting', 'editing files', 'reading files and logs', 'viewing images', 'waiting on tools', 'coordination', 'running scripts']:
        rs = [r for r in ALL if r['activity'] == act]
        rs.sort(key=lambda r: -r['usage']['output'])
        print('=====', act, len(rs))
        for r in rs[:6]:
            print(f"  {loc(r['ts'])} {r['role']:16} out {r['usage']['output']:5} think {r['usage']['thinking']:5} cread {r['usage']['cache_read']:7} cw {r['usage']['cache_write']:6} ${r['usage']['cost']:.2f} | tools {[n for n,_ in r['tools']]} | {head(r['thinking'],90)} | {head(r['text'],80)}")
    sys.exit()

# ---- chosen examples (timestamp UTC prefix + role), one per activity, plus two special cases
PICK = [
 ('reasoning',   '2026-09-15T09:55', 'lead',            'The lead answers "what do you recommend?" on the three scale-up decisions'),
 ('editing',     '2026-09-15T10:08', 'export engineer', 'The export engineer writes the Gate 1 export-set builder in one go'),
 ('reading',     '2026-09-16T13:11', 'code reviewer',   'A code reviewer reads a branch diff and reasons about it'),
 ('viewing',     '2026-09-16T12:48', 'QA critic',       'The Gate 3 critic looks at a picture and writes what it measured'),
 ('waiting',     None,               'bake engineer',   'A bake engineer polls the bake queue'),
 ('coordination','2026-09-17T05:28', 'lead',            'The lead dispatches three agents for the foliage pass'),
 ('running',     '2026-09-17T07:40', 'export engineer', 'The export engineer runs a check script and finds the anchor bug'),
 ('reporting',   None,               'bake engineer',   'A subagent hands its final report back to the lead'),
 ('cache_miss_poll', None,           'bake engineer',   'The same poll after the 5-minute cache has expired: the whole context is written again'),
 ('cache_expiry','2026-09-18T20:59', 'lead',            'The lead resumes after an evening away: the whole context is re-written into the cache'),
]
def find(kind, ts, role):
    rs = [r for r in ALL if r['role'] == role]
    if kind in ('waiting', 'cache_miss_poll'):
        rs = [r for r in rs if r['activity'] == 'waiting on tools' and any(n == 'Bash' and 'status.json' in (i.get('command') or '') for n, i in r['tools'])]
        rs = [r for r in rs if (r['usage']['cache_read'] > 0) == (kind == 'waiting')]
        rs.sort(key=lambda r: r['usage']['cost']); return rs[len(rs) // 2] if rs else None
    if kind == 'reporting':
        rs = [r for r in ALL if r['role'] != 'lead' and not r['tools'] and re.search(r'\b(DONE|COMPLETE|done)\b', r['text'][:600]) and r['usage']['output'] > 600]
        rs.sort(key=lambda r: -len(r['text'])); return rs[0] if rs else None
    if kind == 'viewing':
        rs = [r for r in rs if r['image_in']]
        rs.sort(key=lambda r: -len(r['text'])); return rs[0] if rs else None
    rs = [r for r in rs if r['ts'].startswith(ts)]
    rs.sort(key=lambda r: -r['usage']['output']); return rs[0] if rs else None
EX = []
for kind, ts, role, title in PICK:
    r = find(kind, ts, role)
    if not r: print('MISSING', kind); continue
    tool = ''
    for n, i in r['tools']:
        if n == 'Write': tool = f"Write {os.path.relpath(i.get('file_path',''), ROOT)} ({(i.get('content') or '').count(chr(10)) + 1} lines)"; break
        if n == 'Edit': tool = f"Edit {os.path.relpath(i.get('file_path',''), ROOT)}"; break
        if n == 'Bash': tool = 'Bash: ' + head(i.get('command', ''), 220); break
        if n == 'Agent': tool = 'Agent: ' + head(i.get('description', ''), 60) + ' | brief: ' + head(i.get('prompt', ''), 160); break
        if n == 'SendMessage': tool = 'SendMessage to ' + head(str(i.get('to', '')), 30) + ': ' + head(i.get('message') or i.get('content') or '', 160); break
        if n == 'Read': tool = 'Read ' + os.path.relpath(i.get('file_path', ''), ROOT); break
    EX.append({'kind': kind, 'title': title, 'when': loc(r['ts']), 'role': r['role'], 'agent': r['agent'], 'model': (r['model'] or '').replace('claude-', ''), 'activity': r['activity'],
               'usage': r['usage'], 'tools': [n for n, _ in r['tools']], 'tool': tool, 'thinking': head(r['thinking'], 420), 'text': head(r['text'], 1100),
               'thinking_chars': len(r['thinking']), 'text_chars': len(r['text']), 'tool_chars': sum(len(json.dumps(i)) for _, i in r['tools'])})
# ---- how output splits between thinking, prose and tool arguments (code, commands), by characters, whole Phase 6
# thinking text is not stored in the transcripts (only its token count), so: thinking share = thinking tokens / output tokens,
# and the visible remainder is split between prose and tool arguments by character count.
comp = collections.Counter(); comp_role = collections.defaultdict(collections.Counter)
for r in ALL:
    tc = sum(len(json.dumps(i)) for _, i in r['tools']); pc = len(r['text']); vis = (tc + pc) or 1
    visible = r['usage']['output'] - r['usage']['thinking']
    for k, v in (('thinking', r['usage']['thinking']), ('prose', visible * pc / vis), ('tool arguments (code, commands, briefs)', visible * tc / vis)):
        comp[k] += v; comp_role[r['role']][k] += v
tot = sum(comp.values()) or 1
# cache misses: requests that re-wrote more than 100k tokens of context (the 5-minute cache of a subagent, or the lead's 1-hour cache, had expired)
miss = collections.defaultdict(lambda: {'count': 0, 'cost': 0.0, 'tokens': 0}); rolecost = collections.Counter()
for r in ALL:
    rolecost[r['role']] += r['usage']['cost']
    if r['usage']['cache_write'] > 100000:
        m = miss[r['role']]; m['count'] += 1; m['cost'] += r['usage']['cost']; m['tokens'] += r['usage']['cache_write']
MISS = {k: {'count': v['count'], 'cost': round(v['cost'], 2), 'share_of_role_cost': round(100 * v['cost'] / (rolecost[k] or 1)), 'tokens': v['tokens']} for k, v in miss.items()}
MISS['all'] = {'count': sum(v['count'] for v in miss.values()), 'cost': round(sum(v['cost'] for v in miss.values()), 2), 'share_of_role_cost': round(100 * sum(v['cost'] for v in miss.values()) / (sum(rolecost.values()) or 1)), 'tokens': sum(v['tokens'] for v in miss.values())}
rs = sorted(ALL, key=lambda r: -r['usage']['cost']); tot_cost = sum(r['usage']['cost'] for r in rs) or 1
warm = [r for r in rs if r['usage']['cache_write'] <= 100000]
CONC = {'requests': len(rs), 'total_cost': round(tot_cost, 2), 'mean_cost': round(tot_cost / len(rs), 3),
        'top8': [{'cost': round(r['usage']['cost'], 2), 'role': r['role'], 'when': loc(r['ts']), 'output': r['usage']['output'], 'cache_write': r['usage']['cache_write'], 'cache_read': r['usage']['cache_read']} for r in rs[:8]],
        'top1pct_share': round(100 * sum(r['usage']['cost'] for r in rs[:len(rs) // 100]) / tot_cost), 'top10pct_share': round(100 * sum(r['usage']['cost'] for r in rs[:len(rs) // 10]) / tot_cost),
        'under_025_count': sum(1 for r in rs if r['usage']['cost'] < 0.25), 'under_025_cost': round(sum(r['usage']['cost'] for r in rs if r['usage']['cost'] < 0.25)),
        'most_expensive_warm': {'cost': round(warm[0]['usage']['cost'], 2), 'role': warm[0]['role'], 'when': loc(warm[0]['ts']), 'output': warm[0]['usage']['output']},
        'largest_output': {'cost': round(max(rs, key=lambda r: r['usage']['output'])['usage']['cost'], 2), 'output': max(r['usage']['output'] for r in rs)}}
OUT = {'concentration': CONC, 'examples': EX, 'output_split_tokens': {k: int(v) for k, v in comp.items()}, 'output_split_share': {k: round(100 * v / tot, 1) for k, v in comp.items()},
       'output_split_by_role': {role: {k: round(100 * v / (sum(c.values()) or 1)) for k, v in c.items()} for role, c in comp_role.items()},
       'cache_misses': MISS, 'requests': len(ALL), 'median_cache_read': sorted(r['usage']['cache_read'] for r in ALL)[len(ALL) // 2], 'median_output': sorted(r['usage']['output'] for r in ALL)[len(ALL) // 2],
       'median_cost': round(sorted(r['usage']['cost'] for r in ALL)[len(ALL) // 2], 3)}
json.dump(OUT, open(os.path.join(H, 'phase6_examples.json'), 'w'), indent=1)
for e in EX: print(e['kind'], e['when'], e['role'], e['usage'], '|', e['tool'][:100], '|', e['thinking'][:120], '|', e['text'][:100])
print(OUT['output_split_share'], OUT['median_cache_read'], OUT['median_output'], OUT['median_cost'])
