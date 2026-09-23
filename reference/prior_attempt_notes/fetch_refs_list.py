import json, urllib.request, urllib.parse, sys, time
UA = "PalaceRefBot/1.0 (github.com/dkhh10) research"
API = "https://commons.wikimedia.org/w/api.php"
def get(params):
    params = dict(params, format="json")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=60))
def members(cat, depth=0, seen=None, out=None):
    seen = seen if seen is not None else set(); out = out if out is not None else {}
    if cat in seen: return out
    seen.add(cat)
    cont = {}
    while True:
        d = get(dict(action="query", list="categorymembers", cmtitle=cat, cmlimit=500, cmtype="subcat|file", **cont))
        for m in d["query"]["categorymembers"]:
            if m["ns"] == 6: out.setdefault(m["title"], cat)
            elif m["ns"] == 14 and depth < 2:
                members(m["title"], depth+1, seen, out)
        if "continue" in d: cont = d["continue"]
        else: break
    return out
root = "Category:Palace of Fine Arts, San Francisco"
files = members(root)
from collections import Counter
c = Counter(files.values())
for k, v in c.most_common(): print(v, k)
print("TOTAL", len(files))
json.dump(files, open("refs/_commons_files.json", "w"), indent=1)
