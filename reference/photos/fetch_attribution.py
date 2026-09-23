#!/usr/bin/env python3
"""Fetch author and licence for every Wikimedia Commons photo in index_wikimedia.csv (Commons API, no auth)
and write reference/photos/ATTRIBUTION.md. Run before publishing anything derived from the photos."""
import csv, json, urllib.request, urllib.parse, re, html, os, collections
H = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(H, 'index_wikimedia.csv'))))
titles = {}
for r in rows:
    m = re.search(r'wiki/(File%3A[^\s"]+|File:[^\s"]+)', r['src'] or '')
    if m: titles[r['ref']] = urllib.parse.unquote(m.group(1)).replace('File%3A', 'File:')
meta = {}
tl = list(titles.items())
for i in range(0, len(tl), 40):
    batch = tl[i:i + 40]
    q = urllib.parse.urlencode({'action': 'query', 'titles': '|'.join(t for _, t in batch), 'prop': 'imageinfo', 'iiprop': 'extmetadata|url', 'format': 'json', 'formatversion': '2'})
    req = urllib.request.Request('https://commons.wikimedia.org/w/api.php?' + q, headers={'User-Agent': 'pfa-attribution/1.0 (github.com/dkhh10)'})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    for p in d['query']['pages']:
        ii = (p.get('imageinfo') or [{}])[0]; em = ii.get('extmetadata') or {}
        clean = lambda k: html.unescape(re.sub(r'<[^>]+>', '', (em.get(k) or {}).get('value', ''))).strip()
        meta[p['title']] = {'artist': clean('Artist'), 'license': clean('LicenseShortName'), 'license_url': clean('LicenseUrl'), 'credit': clean('Credit'), 'url': ii.get('descriptionurl', '')}
lic = collections.Counter(m['license'] or '?' for m in meta.values())
L = ['# Reference photo attribution', '', 'Every reference photo used in this project (crops under reference/photos/, the projection textures under assets/textures/pfa, the comparison sheets under renders/, and the photograph on docs/phase6_story.html) comes from Wikimedia Commons. Author and licence per file as returned by the Commons API on the date below; the licence links are the terms. Photos not on Commons: none. Fetched by reference/photos/fetch_attribution.py.', '',
     f'Licence summary: ' + ', '.join(f'{k} ({v})' for k, v in lic.most_common()), '', '| ref | file on Commons | author | licence |', '|---|---|---|---|']
for r in rows:
    t = titles.get(r['ref']); m = meta.get(t, {}) if t else {}
    L.append(f"| {r['ref']} | [{t.replace('File:', '') if t else r['file']}]({m.get('url') or r['src']}) | {m.get('artist', '?')} | [{m.get('license', '?')}]({m.get('license_url', '')}) |")
open(os.path.join(H, 'ATTRIBUTION.md'), 'w').write('\n'.join(L) + '\n')
print(len(rows), 'rows;', len(meta), 'fetched;', dict(lic))
