#!/usr/bin/env python3
"""Prompt-cache analysis from docs/usage/turns_all.json (written by usage_from_transcripts.py --turns).
Answers: which cache lifetime each role used, how many requests found a cold cache and re-wrote their whole
context, what that cost against a warm cache, and what a longer lifetime would have cost or saved.
Writes docs/usage/cache_analysis.json and prints the tables. Rates from usage_from_transcripts.RATES.
A 'miss' = a request whose cache_write exceeds 20k tokens and whose cache_read is under 20 % of it (the prefix
was re-written, not extended)."""
import json, os, sys, datetime, collections
H = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0]]; sys.path.insert(0, H)
import usage_from_transcripts as U
D = json.load(open(os.path.join(H, 'turns_all.json')))
T = D['turns']
def rate(model): return U.RATES.get(model) or (0, 0, 0, 0, 0)
def win(r, a, b): return a <= r['ts'][:10] <= b
WINDOWS = {'phase6 (09-15..18)': ('2026-09-15', '2026-09-18'), 'phase5 (09-06..10)': ('2026-09-06', '2026-09-10'), 'whole project': ('2026-09-01', '2026-12-31')}
OUT = {}
for name, (a, b) in WINDOWS.items():
    rs = [r for r in T if win(r, a, b) and r['model'] in U.RATES]
    ttl = collections.defaultdict(lambda: collections.Counter())
    miss = collections.defaultdict(lambda: collections.Counter())
    for r in rs:
        k = r['role']
        ttl[k]['cw5m'] += r['cw5m']; ttl[k]['cw1h'] += r['cw1h']; ttl[k]['cread'] += r['cread']; ttl[k]['cost'] += r['cost_usd']; ttl[k]['n'] += 1
        cw = r['cw5m'] + r['cw1h']
        if cw > 20000 and r['cread'] < 0.2 * cw:
            i, o, w5, w1, rd = rate(r['model'])
            write_cost = (r['cw5m'] * w5 + r['cw1h'] * w1) / 1e6
            warm_cost = cw * rd / 1e6
            miss[k]['n'] += 1; miss[k]['tokens'] += cw; miss[k]['write_cost'] += write_cost; miss[k]['extra_vs_warm'] += write_cost - warm_cost
    tot_cost = sum(v['cost'] for v in ttl.values()) or 1
    OUT[name] = {'roles': {k: {'requests': v['n'], 'cache_write_5m_M': round(v['cw5m'] / 1e6, 2), 'cache_write_1h_M': round(v['cw1h'] / 1e6, 2), 'cache_read_M': round(v['cread'] / 1e6, 1), 'cost': round(v['cost'], 2),
                                'misses': miss[k]['n'], 'miss_tokens_M': round(miss[k]['tokens'] / 1e6, 2), 'miss_write_cost': round(miss[k]['write_cost'], 2), 'extra_vs_warm': round(miss[k]['extra_vs_warm'], 2),
                                'extra_share_of_role_cost_pct': round(100 * miss[k]['extra_vs_warm'] / (v['cost'] or 1))} for k, v in sorted(ttl.items(), key=lambda x: -x[1]['cost'])},
                 'total_cost': round(tot_cost, 2), 'misses': sum(m['n'] for m in miss.values()), 'miss_write_cost': round(sum(m['write_cost'] for m in miss.values()), 2),
                 'extra_vs_warm': round(sum(m['extra_vs_warm'] for m in miss.values()), 2), 'extra_share_pct': round(100 * sum(m['extra_vs_warm'] for m in miss.values()) / tot_cost, 1)}
    # simulate: same conversations, cache lifetime 5 min vs 1 h for every agent, from the gaps between consecutive requests
    by = collections.defaultdict(list)
    for r in rs: by[(r['sid'], r['agent'])].append(r)
    sim = {}
    for ttl_s, wname in ((300, '5 min'), (3600, '1 h')):
        cost = 0.0; misses = 0
        for key, seq in by.items():
            seq.sort(key=lambda r: r['ts']); prev = None
            for r in seq:
                i, o, w5, w1, rd = rate(r['model']); ctx = r['cread'] + r['cw5m'] + r['cw1h']
                t = datetime.datetime.fromisoformat(r['ts'].replace('Z', '+00:00'))
                gap = (t - prev).total_seconds() if prev else 1e9
                prev = t
                new = r['cw5m'] + r['cw1h'] if (r['cread'] > 0 and r['cread'] >= 0.2 * (r['cw5m'] + r['cw1h'])) else min(r['cw5m'] + r['cw1h'], 20000)
                wrate = w5 if ttl_s == 300 else w1
                if gap > ttl_s:   # cold: whole context written at the write rate
                    cost += ctx * wrate / 1e6; misses += 1
                else:             # warm: prefix read, only the new part written
                    cost += (ctx - new) * rd / 1e6 + new * wrate / 1e6
                cost += r['output'] * o / 1e6 + r['input'] * i / 1e6
        sim[wname] = {'cost': round(cost, 2), 'misses': misses}
    OUT[name]['simulated_same_gaps'] = sim
json.dump(OUT, open(os.path.join(H, 'cache_analysis.json'), 'w'), indent=1)
for name, v in OUT.items():
    print(f"\n== {name}: total ${v['total_cost']:,.0f}; misses {v['misses']} requests, re-written for ${v['miss_write_cost']:,.0f}, of which ${v['extra_vs_warm']:,.0f} ({v['extra_share_pct']} %) is the premium over a warm cache; simulated {v['simulated_same_gaps']}")
    print('| role | requests | cache write 5m (M) | cache write 1h (M) | cache read (M) | cost | misses | miss tokens (M) | premium vs warm | share of role cost |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for k, x in v['roles'].items():
        print(f"| {k} | {x['requests']} | {x['cache_write_5m_M']} | {x['cache_write_1h_M']} | {x['cache_read_M']} | {x['cost']:,.0f} | {x['misses']} | {x['miss_tokens_M']} | {x['extra_vs_warm']:,.0f} | {x['extra_share_of_role_cost_pct']} % |")
