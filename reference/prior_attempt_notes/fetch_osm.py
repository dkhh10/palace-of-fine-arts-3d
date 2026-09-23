import json, urllib.request, urllib.parse, math
q = '''[out:json][timeout:60];
(
  way(around:400,37.80290,-122.44860)["building"];
  way(around:400,37.80290,-122.44860)["natural"="water"];
  way(around:400,37.80290,-122.44860)["water"];
  way(around:400,37.80290,-122.44860)["historic"];
  way(around:400,37.80290,-122.44860)["tourism"];
  way(around:400,37.80290,-122.44860)["man_made"];
  way(around:400,37.80290,-122.44860)["leisure"];
  relation(around:400,37.80290,-122.44860)["natural"="water"];
);
out geom tags;'''
req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": "PalaceRefBot/1.0 (github.com/dkhh10)"})
d = json.load(urllib.request.urlopen(req, timeout=120))
json.dump(d, open("refs/_osm.json", "w"))
print(len(d["elements"]), "elements")
for e in d["elements"]:
    t = e.get("tags", {})
    name = t.get("name", ""); 
    g = e.get("geometry") or []
    print(e["type"], e["id"], name[:40], {k: v for k, v in t.items() if k in ("building", "natural", "water", "historic", "tourism", "man_made", "leisure", "height", "building:levels")}, "nodes", len(g))
