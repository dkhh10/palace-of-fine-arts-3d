#!/usr/bin/env python3
"""Sum token usage per session / model / subagent from the Claude Code transcript folder
for this project. Processes the .jsonl files only; never prints message content.
Rates: Anthropic list prices (claude-api skill, cached 2026-06-24):
  input / output per MTok; cache write = 2.0x input (1h TTL) or 1.25x (5m TTL); cache read = 0.1x input,
  except claude-fable-5-1 where cache read = $0.25/MTok (0.025x).
"""
import json, glob, os, collections, datetime, sys, re

PROJ = os.path.expanduser('~/.claude/projects/-Users-dk-Projects-3d-render-blender-3rd-attempt-building')
RATES = {  # input, output, cache_write_5m, cache_write_1h, cache_read  ($ per MTok)
    'claude-fable-5-1':          (10.0, 50.0, 12.5, 20.0, 0.25),
    'claude-opus-5':             (5.0, 25.0, 6.25, 10.0, 0.50),
    'claude-sonnet-5':           (2.0, 10.0, 2.5, 4.0, 0.20),
    'claude-haiku-4-5-20251001': (1.0, 5.0, 1.25, 2.0, 0.10),
    'claude-haiku-4-5':          (1.0, 5.0, 1.25, 2.0, 0.10),
}
def cost(model, u):
    r = RATES.get(model)
    if not r: return None
    return (u['input']*r[0] + u['output']*r[1] + u['cw5m']*r[2] + u['cw1h']*r[3] + u['cread']*r[4]) / 1e6

def zero(): return {'input':0,'output':0,'cw5m':0,'cw1h':0,'cread':0,'thinking':0,'requests':0}

DAILY = collections.defaultdict(lambda: collections.defaultdict(zero))
HOURLY = collections.defaultdict(lambda: collections.defaultdict(zero))
COSTSTATE = {}
def scan(path):
    """Return per-model usage dict, first/last timestamp, dedup by message id."""
    seen = {}
    first = last = None
    n_user = 0; n_tool = 0
    with open(path, 'r', errors='replace') as f:
        for line in f:
            try: o = json.loads(line)
            except Exception: continue
            ts = o.get('timestamp')
            if ts:
                if first is None or ts < first: first = ts
                if last is None or ts > last: last = ts
            t = o.get('type')
            if t == 'cost-state':
                COSTSTATE[o.get('sessionId')] = o
            if t == 'user': n_user += 1
            if t != 'assistant': continue
            m = o.get('message') or {}
            u = m.get('usage')
            if not u: continue
            mid = m.get('id') or o.get('requestId') or o.get('uuid')
            model = m.get('model', 'unknown')
            cc = u.get('cache_creation') or {}
            rec = {'model': model,
                   'input': u.get('input_tokens', 0) or 0,
                   'output': u.get('output_tokens', 0) or 0,
                   'cw5m': cc.get('ephemeral_5m_input_tokens', 0) or 0,
                   'cw1h': cc.get('ephemeral_1h_input_tokens', 0) or 0,
                   'cread': u.get('cache_read_input_tokens', 0) or 0,
                   'thinking': ((u.get('output_tokens_details') or {}).get('thinking_tokens', 0) or 0)}
            if not cc:
                rec['cw5m'] = u.get('cache_creation_input_tokens', 0) or 0
            rec['ts'] = ts
            prev = seen.get(mid)
            # streaming writes several rows per message with identical usage; keep the max output
            if prev is None or rec['output'] > prev['output']:
                seen[mid] = rec
    per_model = collections.defaultdict(zero)
    for rec in seen.values():
        pm = per_model[rec['model']]
        for k in ('input','output','cw5m','cw1h','cread','thinking'): pm[k] += rec[k]
        pm['requests'] += 1
        if rec.get('ts'):
            d = DAILY[rec['ts'][:10]][rec['model']]; h = HOURLY[rec['ts'][:13]][rec['model']]
            for k in ('input','output','cw5m','cw1h','cread','thinking'): d[k] += rec[k]; h[k] += rec[k]
            d['requests'] += 1; h['requests'] += 1
    return per_model, first, last, n_user

def add(dst, src):
    for k, v in src.items(): dst[k] += v

sessions = []
grand = collections.defaultdict(zero)
for main in sorted(glob.glob(os.path.join(PROJ, '*.jsonl'))):
    sid = os.path.basename(main)[:-6]
    pm, first, last, n_user = scan(main)
    sess = {'session_id': sid, 'first': first, 'last': last, 'main_user_turns': n_user,
            'main': {m: dict(v) for m, v in pm.items()}, 'subagents': []}
    tot = collections.defaultdict(zero)
    for m, v in pm.items(): add(tot[m], v)
    sadir = os.path.join(PROJ, sid, 'subagents')
    for sa in sorted(glob.glob(os.path.join(sadir, '*.jsonl'))):
        meta = {}
        mp = sa[:-6] + '.meta.json'
        if os.path.exists(mp):
            try: meta = json.load(open(mp))
            except Exception: meta = {}
        spm, sf, sl, _ = scan(sa)
        entry = {'agent': os.path.basename(sa)[6:-6], 'agentType': meta.get('agentType'),
                 'description': meta.get('description'), 'spawnDepth': meta.get('spawnDepth'),
                 'first': sf, 'last': sl, 'usage': {m: dict(v) for m, v in spm.items()}}
        entry['cost_usd'] = round(sum((cost(m, v) or 0) for m, v in spm.items()), 2)
        entry['models'] = sorted(spm.keys())
        sess['subagents'].append(entry)
        for m, v in spm.items(): add(tot[m], v)
    # sessions' first/last must include subagents
    for e in sess['subagents']:
        if e['first'] and (sess['first'] is None or e['first'] < sess['first']): sess['first'] = e['first']
        if e['last'] and (sess['last'] is None or e['last'] > sess['last']): sess['last'] = e['last']
    sess['total_by_model'] = {m: dict(v) for m, v in tot.items()}
    sess['cost_by_model_usd'] = {m: round(cost(m, v) or 0, 2) for m, v in tot.items()}
    sess['cost_usd'] = round(sum(sess['cost_by_model_usd'].values()), 2)
    if sess['first'] and sess['last']:
        f = datetime.datetime.fromisoformat(sess['first'].replace('Z','+00:00'))
        l = datetime.datetime.fromisoformat(sess['last'].replace('Z','+00:00'))
        sess['wall_hours'] = round((l - f).total_seconds()/3600, 2)
    for m, v in tot.items(): add(grand[m], v)
    sessions.append(sess)

sessions.sort(key=lambda s: s['first'] or '')
out = {'generated': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'source': PROJ, 'rates_usd_per_mtok': {k: dict(zip(('input','output','cache_write_5m','cache_write_1h','cache_read'), v)) for k, v in RATES.items()},
       'sessions': sessions,
       'grand_total_by_model': {m: dict(v) for m, v in grand.items()},
       'grand_cost_by_model_usd': {m: round(cost(m, v) or 0, 2) for m, v in grand.items()}}
out['grand_cost_usd'] = round(sum(out['grand_cost_by_model_usd'].values()), 2)
out['daily'] = {d: {'cost_usd': round(sum((cost(m, v) or 0) for m, v in mm.items()), 2),
                    'by_model': {m: dict(v) for m, v in mm.items()}} for d, mm in sorted(DAILY.items())}
out['hourly_cost_usd'] = {h: round(sum((cost(m, v) or 0) for m, v in mm.items()), 2) for h, mm in sorted(HOURLY.items())}
# Claude Code's own running cost-state (its internal pricing table; includes Haiku side calls not in the transcripts)
out['claude_code_cost_state'] = {}
for s_ in sessions:
    cs = COSTSTATE.get(s_['session_id'])
    if cs:
        s_['claude_code_cost_state_usd'] = round(cs.get('totalCostUSD', 0), 2)
        s_['claude_code_api_hours'] = round(cs.get('totalAPIDuration', 0)/3.6e6, 2)
        s_['claude_code_tool_hours'] = round(cs.get('totalToolDuration', 0)/3.6e6, 2)
        s_['claude_code_lines'] = (cs.get('totalLinesAdded'), cs.get('totalLinesRemoved'))
        out['claude_code_cost_state'][s_['session_id']] = {'totalCostUSD': cs.get('totalCostUSD'), 'modelUsage': cs.get('modelUsage')}
json.dump(out, open(os.path.join(os.path.dirname(__file__), 'sessions.json'), 'w'), indent=1)

# ---- summary.md ----
L = []
L.append('# Token usage summary (from Claude Code transcripts)\n')
L.append(f'Generated {out["generated"][:19]}Z by `docs/usage/usage_from_transcripts.py` from `{PROJ}` '
         f'({len(sessions)} main sessions, {sum(len(s["subagents"]) for s in sessions)} subagent transcripts). '
         'Usage is deduplicated by API message id. Tokens in thousands (k) unless stated.\n')
L.append('Also in this folder: `daily.json` and `sessions_all.json` are raw `ccusage` exports (account-wide, every project, its own price table; `sessions_all.json` has no project field, which is why this script exists). `make_timeline.py` renders `docs/timeline.html` from `sessions.json`.\n')
L.append('## Rates used (Anthropic list, USD per million tokens)\n')
L.append('| model | input | output | cache write 5m | cache write 1h | cache read |')
L.append('|---|---|---|---|---|---|')
for k, v in RATES.items():
    if k == 'claude-haiku-4-5': continue
    L.append(f'| {k} | {v[0]:.2f} | {v[1]:.2f} | {v[2]:.2f} | {v[3]:.2f} | {v[4]:.2f} |')
L.append('\nSource: claude-api skill pricing table (cached 2026-06-24). Cache write = 2x input for the 1-hour TTL '
         'Claude Code uses, 1.25x for 5-minute; cache read = 0.1x input except Fable 5.1 at $0.25/MTok. '
         'Nominal API cost only; the account runs on a subscription, so no invoice matches these numbers.\n')
def k(n): return f'{n/1000:,.0f}'
L.append('## Grand total by model\n')
L.append('| model | requests | input k | output k | thinking k (of output) | cache write 1h k | cache write 5m k | cache read k | cost USD |')
L.append('|---|---|---|---|---|---|---|---|---|')
for m, v in sorted(grand.items(), key=lambda x: -(cost(x[0], x[1]) or 0)):
    L.append(f'| {m} | {v["requests"]} | {k(v["input"])} | {k(v["output"])} | {k(v["thinking"])} | {k(v["cw1h"])} | {k(v["cw5m"])} | {k(v["cread"])} | {cost(m, v) or 0:,.2f} |')
L.append(f'\n**Grand total nominal cost: ${out["grand_cost_usd"]:,.2f}**\n')
L.append('## Sessions\n')
L.append('| # | session | first (UTC) | last (UTC) | wall h | user turns | subagents | cost USD | cost by model |')
L.append('|---|---|---|---|---|---|---|---|---|')
for i, s in enumerate(sessions, 1):
    cbm = ', '.join(f'{m.replace("claude-","").replace("-20251001","")} {c:,.0f}' for m, c in sorted(s['cost_by_model_usd'].items(), key=lambda x: -x[1]) if c >= 1)
    L.append(f'| {i} | {s["session_id"][:8]} | {(s["first"] or "")[:16]} | {(s["last"] or "")[:16]} | {s.get("wall_hours","")} | {s["main_user_turns"]} | {len(s["subagents"])} | {s["cost_usd"]:,.2f} | {cbm} |')
L.append('\n## Cross-check: Claude Code internal cost-state per session\n')
L.append('Claude Code keeps its own running tally in the transcript (`cost-state` rows, its internal price table, and it includes Haiku side calls such as web search and title generation that leave no assistant usage rows). Reported for comparison; the list-rate figures above are the ones cited elsewhere.\n')
L.append('| session | Claude Code totalCostUSD | API-call hours | tool hours | lines +/- | this script USD |')
L.append('|---|---|---|---|---|---|')
for i, s_ in enumerate(sessions, 1):
    if 'claude_code_cost_state_usd' in s_:
        L.append(f'| {i} {s_["session_id"][:8]} | {s_["claude_code_cost_state_usd"]:,.2f} | {s_["claude_code_api_hours"]} | {s_["claude_code_tool_hours"]} | {s_["claude_code_lines"][0]}/{s_["claude_code_lines"][1]} | {s_["cost_usd"]:,.2f} |')
L.append(f'| total | {sum(s_.get("claude_code_cost_state_usd",0) for s_ in sessions):,.2f} | | | | {out["grand_cost_usd"]:,.2f} |')
L.append('\n## Daily nominal cost (this project only, UTC)\n')
L.append('| day | cost USD | fable-5-1 | opus-5 | other |')
L.append('|---|---|---|---|---|')
for d, dd in out['daily'].items():
    bm = dd['by_model']
    f_ = cost('claude-fable-5-1', bm.get('claude-fable-5-1', zero())) or 0
    o_ = cost('claude-opus-5', bm.get('claude-opus-5', zero())) or 0
    L.append(f'| {d} | {dd["cost_usd"]:,.2f} | {f_:,.2f} | {o_:,.2f} | {dd["cost_usd"]-f_-o_:,.2f} |')
L.append('\n## Subagents per session (by model, count and cost)\n')
for i, s in enumerate(sessions, 1):
    c = collections.Counter(); cst = collections.Counter(); types = collections.Counter()
    for e in s['subagents']:
        key = ','.join(x.replace('claude-','').replace('-20251001','') for x in e['models']) or 'none'
        c[key] += 1; cst[key] += e['cost_usd']; types[e['agentType']] += 1
    L.append(f'- Session {i} ({s["session_id"][:8]}): ' + '; '.join(f'{n} x {key} (${cst[key]:,.0f})' for key, n in c.most_common()) + f'. Types: {dict(types)}')
def role_of(desc):
    d=(desc or '').lower()
    if d.startswith('code review') or d.startswith('review'): return 'code review'
    if 'critic' in d or d.startswith('qa round') or 'hero tiles' in d or 'hero re-check' in d: return 'QA critic'
    if re.search(r'phase ?5|deliver|flythrough plan', d): return 'phase 5 prep'
    if re.search(r'research|crop|catalog|colour', d): return 'research'
    for k, pat in (('lighting','light'),('architecture','arch'),('environment','env'),('materials','mat'),('ornament','orn')):
        if pat in d: return k
    return 'other'
L.append('\n## Agents dispatched by role (subagent transcripts, classified from their spawn descriptions)\n')
roles=['research','architecture','ornament','materials','environment','lighting','QA critic','code review','phase 5 prep','other']
L.append('| session | ' + ' | '.join(roles) + ' | total |')
L.append('|---|' + '---|'*(len(roles)+1))
G=collections.Counter(); GC=collections.Counter()
for i, s_ in enumerate(sessions, 1):
    c=collections.Counter(); cc=collections.Counter()
    for e in s_['subagents']:
        r=role_of(e['description']); c[r]+=1; cc[r]+=e['cost_usd']; G[r]+=1; GC[r]+=e['cost_usd']
    L.append(f'| {i} | ' + ' | '.join(f'{c[r]} (${cc[r]:.0f})' if c[r] else '-' for r in roles) + f' | {sum(c.values())} (${sum(cc.values()):.0f}) |')
L.append('| all | ' + ' | '.join(f'{G[r]} (${GC[r]:.0f})' if G[r] else '-' for r in roles) + f' | {sum(G.values())} (${sum(GC.values()):.0f}) |')
L.append('\nLead (main thread) cost per session, same rates: ' + ', '.join(f'session {i} ${sum((cost(m,u) or 0) for m,u in s_["main"].items()):.0f}' for i, s_ in enumerate(sessions,1)) + '.')
L.append('\n## Subagent list (cost >= $5)\n')
L.append('| session | agent | type | model(s) | first | last | output k | cache read k | cost USD | description |')
L.append('|---|---|---|---|---|---|---|---|---|---|')
for i, s in enumerate(sessions, 1):
    for e in sorted(s['subagents'], key=lambda e: -e['cost_usd']):
        if e['cost_usd'] < 5: continue
        outk = sum(v['output'] for v in e['usage'].values()); crk = sum(v['cread'] for v in e['usage'].values())
        L.append(f'| {i} | {e["agent"][:9]} | {e["agentType"]} | {",".join(x.replace("claude-","").replace("-20251001","") for x in e["models"])} | {(e["first"] or "")[5:16]} | {(e["last"] or "")[5:16]} | {k(outk)} | {k(crk)} | {e["cost_usd"]:,.2f} | {(e["description"] or "")[:60]} |')
open(os.path.join(os.path.dirname(__file__), 'summary.md'), 'w').write('\n'.join(L) + '\n')
print('\n'.join(L[:40]))

# ---------------------------------------------------------------------------------------------
# Per-turn detail (added 2026-09-21 for the Phase 6 retrospective, docs/retrospective_phase6.md).
# Everything above is unchanged and still runs first. This block only runs with `--turns OUT.json
# [--since YYYY-MM-DD] [--until YYYY-MM-DD]` and writes one record per API request (deduplicated by
# message id, same rule as scan()) for the lead thread and every subagent, plus every tool call with
# its wall duration, every human prompt (timestamp and length only, never the text) and per-agent
# metadata. Activity is a heuristic classification of what the request was for (see classify_activity);
# its limits are stated in the retrospective, not hidden here.
# ---------------------------------------------------------------------------------------------
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
GPU_LAUNCH = re.compile(r'(?<![\w/.-])(scripts/|\./)?(blender_run\.sh|chrome_run\.sh)\s+\d+\s+--|bake_queue\.sh\s+--gate|web/tools/gate\d[a-z]?\.sh|node\s+\S*screenshot\.mjs|MacOS/Blender\s+--background', re.I)
GPU_RUN = re.compile(r'(?<![\w/.-])(scripts/|\./)?(blender_run\.sh|chrome_run\.sh)\s+\d+|bake_queue\.sh\s+--|web/tools/gate\d[a-z]?\.sh|screenshot\.mjs|MacOS/Blender\s+--background|blender\s+--background|node .*screenshot', re.I)
READ_ONLY = re.compile(r'^\s*(cd [^&]*&&\s*)?(cat|head|tail|grep|rg|sed -n|ls|wc|find|stat|du|git (log|status|diff|show|branch|ls-files)|python3 -c "import json;\s*print|jq|pgrep|file)\b')
EDIT_CMD = re.compile(r'cat\s*>>?\s*[^|]|sed -i|applypatch|git (add|commit|merge|checkout -b|rebase|cherry-pick)|tee ', re.I)
WAIT_CMD = re.compile(r'status\.json|pgrep|sleep \d|wait\b|blender_run\.sh|chrome_run\.sh|tail -f|watchdog', re.I)

def classify_activity(tools, image_in, cmds):
    """tools: list of tool names in the assistant message; image_in: the request carried an image
    (a tool result with an image block preceded it); cmds: Bash/Monitor command strings.
    Priority: viewing images > waiting > editing files > coordination > reading > running > reasoning."""
    if image_in or any(t == 'Read' and c.lower().endswith(IMAGE_EXT) for t, c in cmds if t == 'Read'):
        return 'viewing images'
    names = set(tools)
    bash = [c for t, c in cmds if t in ('Bash', 'Monitor')]
    if 'Monitor' in names or any(GPU_RUN.search(c) for c in bash) or any(WAIT_CMD.search(c) and len(c) < 400 for c in bash):
        return 'waiting on tools'
    if names & {'Edit', 'Write', 'MultiEdit', 'NotebookEdit'} or any(EDIT_CMD.search(c) for c in bash):
        return 'editing files'
    if names & {'Agent', 'SendMessage', 'AskUserQuestion', 'TaskStop'}:
        return 'coordination'
    if 'Read' in names or any(READ_ONLY.search(c) for c in bash):
        return 'reading files and logs'
    if names:
        return 'running scripts'
    return 'reasoning and reporting'

def role_of_agent(desc):
    d = (desc or '').lower()
    if d.startswith('code review') or d.startswith('review') or 'delta review' in d or ' review' in d[:30]: return 'code reviewer'
    if 'qa round' in d or 'critic' in d or d.startswith('qa '): return 'QA critic'
    if 'bake' in d: return 'bake engineer'
    if 'export' in d or 'env:' in d or ' env ' in d: return 'export engineer'
    if 'viewer' in d: return 'viewer engineer'
    if 'materials' in d or 'mat r' in d or d.startswith('mat '): return 'materials'
    if 'perf' in d or 'research' in d or 'analysis' in d or 'inventory' in d or 'sonnet' in d or 'crop' in d or 'catalog' in d: return 'analysis/mechanical'
    for k, pat in (('lighting', 'light'), ('architecture', 'arch'), ('environment', 'env'), ('ornament', 'orn'), ('phase 5 prep', 'flythrough'), ('phase 5 prep', 'deliver')):
        if pat in d: return k
    return 'other'

def turn_records(path, sid, agent, role, model_hint):
    """One record per deduplicated API request + tool calls + human prompts for one transcript."""
    seen = {}; order = []
    pending = {}   # tool_use id -> (ts, name, cmd)
    tool_calls = []; prompts = []; notifications = []; launches = []
    last_result_had_image = False
    with open(path, 'r', errors='replace') as f:
        for line in f:
            try: o = json.loads(line)
            except Exception: continue
            t = o.get('type'); ts = o.get('timestamp')
            if t == 'user':
                m = o.get('message') or {}; cc = m.get('content')
                had_image = False; is_result = False
                if isinstance(cc, list):
                    for c in cc:
                        if not isinstance(c, dict): continue
                        if c.get('type') == 'tool_result':
                            is_result = True
                            inner = c.get('content')
                            if isinstance(inner, list) and any(isinstance(x, dict) and x.get('type') == 'image' for x in inner):
                                had_image = True
                            tid = c.get('tool_use_id')
                            if tid in pending:
                                s, name, cmd = pending.pop(tid)
                                try:
                                    dur = (datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')) - datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))).total_seconds()
                                except Exception: dur = None
                                tool_calls.append({'sid': sid, 'agent': agent, 'role': role, 'tool': name, 'start': s, 'end': ts,
                                                   'dur_s': dur, 'gpu': bool(GPU_RUN.search(cmd or '')), 'cmd_head': (cmd or '')[:120]})
                        elif c.get('type') == 'image':
                            had_image = True
                if is_result:
                    last_result_had_image = had_image
                elif not o.get('isMeta'):
                    txt = cc if isinstance(cc, str) else (cc[0].get('text', '') if isinstance(cc, list) and cc and isinstance(cc[0], dict) and cc[0].get('type') == 'text' else '')
                    kind = (o.get('origin') or {}).get('kind') if isinstance(o.get('origin'), dict) else None
                    if txt.startswith('<task-notification') or kind == 'task-notification':
                        notifications.append(ts)
                    if txt and not txt.startswith('<task-notification') and not txt.startswith('<local-command') and not txt.startswith('<command-') and kind not in ('peer', 'task-notification') and 'Subagent hand-back' not in txt[:300]:
                        prompts.append({'sid': sid, 'agent': agent, 'ts': ts, 'chars': len(txt), 'image': had_image})
                    last_result_had_image = had_image
                continue
            if t != 'assistant': continue
            m = o.get('message') or {}
            u = m.get('usage')
            mid = m.get('id') or o.get('requestId') or o.get('uuid')
            tools = []; cmds = []; thinking_chars = 0; text_chars = 0; asks = False
            for c in m.get('content') or []:
                if not isinstance(c, dict): continue
                if c.get('type') == 'tool_use':
                    tools.append(c.get('name'))
                    inp = c.get('input') or {}
                    cmd = inp.get('command') or inp.get('file_path') or inp.get('description') or ''
                    cmds.append((c.get('name'), cmd if isinstance(cmd, str) else ''))
                    if c.get('id'): pending[c['id']] = (ts, c.get('name'), inp.get('command') or '')
                    if c.get('name') == 'Bash' and GPU_LAUNCH.search(inp.get('command') or ''):
                        mm = re.search(r'(?:blender_run|chrome_run)\.sh\s+(\d+)', inp.get('command') or '')
                        launches.append({'ts': ts, 'background': bool(inp.get('run_in_background')), 'max_s': int(mm.group(1)) if mm else None,
                                         'cmd_head': re.sub(r'\s+', ' ', inp.get('command') or '')[:140]})
                elif c.get('type') == 'thinking': thinking_chars += len(c.get('thinking') or '')
                elif c.get('type') == 'text':
                    text_chars += len(c.get('text') or '')
                    if '?' in (c.get('text') or '')[-600:]: asks = True
            rec = seen.get(mid)
            if rec is None:
                rec = {'sid': sid, 'agent': agent, 'role': role, 'model': m.get('model', model_hint or 'unknown'), 'ts': ts,
                       'input': 0, 'output': 0, 'cw5m': 0, 'cw1h': 0, 'cread': 0, 'thinking': 0,
                       'tools': [], 'cmds': [], 'image_in': last_result_had_image, 'thinking_chars': 0, 'text_chars': 0}
                seen[mid] = rec; order.append(mid)
            # streaming writes several rows per message: merge the content blocks, keep the max usage
            rec['tools'] += tools; rec['cmds'] += cmds; rec['thinking_chars'] += thinking_chars; rec['text_chars'] += text_chars
            rec['asks'] = rec.get('asks', False) or asks
            rec['last_cmd'] = (cmds[-1][1] if cmds else rec.get('last_cmd', ''))[:160]
            if u:
                cc = u.get('cache_creation') or {}
                cand = {'input': u.get('input_tokens', 0) or 0, 'output': u.get('output_tokens', 0) or 0,
                        'cw5m': cc.get('ephemeral_5m_input_tokens', 0) or (0 if cc else (u.get('cache_creation_input_tokens', 0) or 0)),
                        'cw1h': cc.get('ephemeral_1h_input_tokens', 0) or 0, 'cread': u.get('cache_read_input_tokens', 0) or 0,
                        'thinking': ((u.get('output_tokens_details') or {}).get('thinking_tokens', 0) or 0)}
                if cand['output'] >= rec['output']:
                    rec.update(cand)
    out = []
    for mid in order:
        r = seen[mid]
        r['activity'] = classify_activity(r['tools'], r['image_in'], r['cmds'])
        r['cost_usd'] = cost(r['model'], r) or 0.0
        r['tools'] = sorted(set(x for x in r['tools'] if x))
        del r['cmds']
        out.append(r)
    return out, tool_calls, prompts, {'notifications': notifications, 'launches': launches}

def write_turns(out_path, since=None, until=None):
    turns = []; calls = []; prompts = []; agents = []
    for main in sorted(glob.glob(os.path.join(PROJ, '*.jsonl'))):
        sid = os.path.basename(main)[:-6]
        tr, tc, pr, ex = turn_records(main, sid, 'lead', 'lead', None)
        first = min((r['ts'] for r in tr if r['ts']), default=None); last = max((r['ts'] for r in tr if r['ts']), default=None)
        if since and last and last[:10] < since: continue
        if until and first and first[:10] > until: continue
        agents.append({'sid': sid, 'agent': 'lead', 'role': 'lead', 'model': (tr[0]['model'] if tr else None), 'description': 'lead thread', 'first': first, 'last': last, 'requests': len(tr), **ex})
        turns += tr; calls += tc; prompts += pr
        for sa in sorted(glob.glob(os.path.join(PROJ, sid, 'subagents', '*.jsonl'))):
            meta = {}
            mp = sa[:-6] + '.meta.json'
            if os.path.exists(mp):
                try: meta = json.load(open(mp))
                except Exception: meta = {}
            aid = os.path.basename(sa)[6:-6]
            role = role_of_agent(meta.get('description'))
            tr, tc, pr, ex = turn_records(sa, sid, aid, role, meta.get('model'))
            agents.append({'sid': sid, 'agent': aid, 'role': role, 'model': (tr[0]['model'] if tr else meta.get('model')), 'description': meta.get('description'),
                           'first': min((r['ts'] for r in tr if r['ts']), default=None), 'last': max((r['ts'] for r in tr if r['ts']), default=None), 'requests': len(tr), **ex})
            turns += tr; calls += tc; prompts += pr
    def inwin(ts): return ts and (not since or ts[:10] >= since) and (not until or ts[:10] <= until)
    turns = [r for r in turns if inwin(r['ts'])]; calls = [c for c in calls if inwin(c['start'])]; prompts = [p for p in prompts if inwin(p['ts'])]
    json.dump({'generated': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'since': since, 'until': until, 'rates': out['rates_usd_per_mtok'],
               'activity_rule': 'priority: viewing images > waiting on tools > editing files > coordination > reading files and logs > running scripts > reasoning and reporting; one activity per API request; thinking tokens carried separately',
               'agents': agents, 'turns': turns, 'tool_calls': calls, 'human_prompts': prompts}, open(out_path, 'w'))
    print(f'turns: {len(turns)} requests, {len(calls)} tool calls, {len(prompts)} human prompts, {len(agents)} agents -> {out_path}')

if '--turns' in sys.argv:
    a = sys.argv; i = a.index('--turns')
    since = a[a.index('--since') + 1] if '--since' in a else None
    until = a[a.index('--until') + 1] if '--until' in a else None
    write_turns(a[i + 1], since, until)
