import json, urllib.request, urllib.parse, os, re, time, csv
UA = "PalaceRefBot/1.0 (github.com/dkhh10) research"
API = "https://commons.wikimedia.org/w/api.php"
def get(params):
    params = dict(params, format="json")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for i in range(3):
        try: return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e: time.sleep(2)
    return {}
files = json.load(open("refs/_commons_files.json"))
SKIP = ("Long Now", "presidential debate", "in art", "Pioneer Mother", "Pergola of the Palace of Fine Arts at the Panama")
ORDER = ["Rotunda", "Palace of Fine Arts, San Francisco$", "Pergola", "Lagoon", "Sculpture", "at night", "Panama-Pacific"]
def catkey(c):
    for i, k in enumerate(ORDER):
        if re.search(k, c): return i
    return 99
titles = [t for t, c in files.items() if not any(s in c for s in SKIP)]
titles = [t for t in titles if t.lower().endswith((".jpg", ".jpeg", ".png"))]
titles.sort(key=lambda t: (catkey(files[t]), t))
print("candidates", len(titles))
info = {}
for i in range(0, len(titles), 40):
    batch = titles[i:i+40]
    d = get(dict(action="query", prop="imageinfo", titles="|".join(batch), iiprop="url|size|extmetadata", iiurlwidth=1400))
    for p in d.get("query", {}).get("pages", {}).values():
        if "imageinfo" not in p: continue
        ii = p["imageinfo"][0]
        em = ii.get("extmetadata", {})
        desc = re.sub("<[^>]+>", "", em.get("ImageDescription", {}).get("value", ""))[:200]
        info[p["title"]] = dict(thumb=ii.get("thumburl"), url=ii.get("url"), w=ii.get("width"), h=ii.get("height"),
                                desc=desc, date=em.get("DateTimeOriginal", {}).get("value", "")[:10], cat=files[p["title"]])
print("info", len(info))
# filter: min width 1200, and prefer landscape+portrait both. cap per category
caps = {0: 110, 1: 90, 2: 45, 3: 20, 4: 20, 5: 12, 6: 10}
counts = {}
os.makedirs("refs/raw", exist_ok=True)
rows = []
n = 0
for t in titles:
    if t not in info or not info[t]["thumb"] or (info[t]["w"] or 0) < 1200: continue
    k = catkey(info[t]["cat"]); 
    if counts.get(k, 0) >= caps.get(k, 10): continue
    counts[k] = counts.get(k, 0) + 1
    n += 1
    slug = re.sub(r"[^A-Za-z0-9]+", "_", t.replace("File:", "").rsplit(".", 1)[0])[:50].strip("_")
    catslug = ["rotunda", "main", "pergola", "lagoon", "sculpture", "night", "ppie1915"][k] if k < 7 else "misc"
    fn = f"refs/raw/ref_{n:03d}_{catslug}_{slug}.jpg"
    if not os.path.exists(fn):
        try:
            req = urllib.request.Request(info[t]["thumb"], headers={"User-Agent": UA})
            open(fn, "wb").write(urllib.request.urlopen(req, timeout=60).read())
        except Exception as e:
            print("fail", t, e); continue
    rows.append(dict(ref=n, file=os.path.basename(fn), cat=catslug, w=info[t]["w"], h=info[t]["h"], date=info[t]["date"], desc=info[t]["desc"], src="https://commons.wikimedia.org/wiki/" + urllib.parse.quote(t)))
with open("refs/index.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("downloaded", len(rows), counts)
