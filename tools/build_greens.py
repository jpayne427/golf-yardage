"""Build greens.json (front/middle/back of each green) from OpenStreetMap.

Uses golf=hole lines (drawn tee -> green) and golf=green polygons inside the
Bandon Dunes resort. Front/back are where the line of play, extended through
the green's center, crosses the green's edge. Entries already in greens.json
that were not generated here (no "src": "osm") are kept as-is.
"""
import json, math, re, time, traceback, urllib.parse, urllib.request

BBOX = (43.14, -124.44, 43.25, -124.35)  # south, west, north, east
COURSES = [  # (id, name pattern) - first match wins; None = ignore
    (None, r"preserve|shorty|punchbowl|practice|range"),
    ("sheep", r"sheep"),
    ("trails", r"trails"),
    ("oldmac", r"old\s*mac"),
    ("pacific", r"pacific"),
    ("dunes", r"bandon dunes"),
]
ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
             "https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]

def overpass():
    s, w, n, e = BBOX
    q = f"""[out:json][timeout:90];
    ( way["golf"="hole"]({s},{w},{n},{e});
      way["golf"="green"]({s},{w},{n},{e});
      relation["golf"="green"]({s},{w},{n},{e});
      way["leisure"="golf_course"]({s},{w},{n},{e});
      relation["leisure"="golf_course"]({s},{w},{n},{e}); );
    out geom;"""
    errors = []
    for attempt in range(2):
        for url in ENDPOINTS:
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": q}).encode(), headers={
                    "User-Agent": "golf-yardage-builder (github.com/jpayne427/golf-yardage)",
                    "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.load(r)["elements"]
            except Exception as ex:  # try the next mirror
                body = ""
                if hasattr(ex, "read"):
                    try: body = ex.read()[:300].decode("utf-8", "replace")
                    except Exception: pass
                errors.append(f"{url}: {ex} {body}".strip())
        time.sleep(20)
    raise RuntimeError("Overpass failed:\n" + "\n".join(errors))

# local flat projection (metres) around the resort
LAT0 = (BBOX[0] + BBOX[2]) / 2
KX, KY = 111320 * math.cos(math.radians(LAT0)), 110540
def xy(p): return (p[1] * KX, p[0] * KY)
def ll(q): return [round(q[1] / KY, 6), round(q[0] / KX, 6)]

def rings(el):
    if el["type"] == "way":
        return [[(g["lat"], g["lon"]) for g in el.get("geometry", [])]]
    out = []
    for m in el.get("members", []):
        if m.get("role") in ("outer", "") and m.get("geometry"):
            out.append([(g["lat"], g["lon"]) for g in m["geometry"]])
    return out

def inside(pt, ring):
    x, y = pt; c = False
    for i in range(len(ring)):
        x1, y1 = ring[i]; x2, y2 = ring[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c

def area(ring):
    return abs(sum(ring[i][0] * ring[i - 1][1] - ring[i - 1][0] * ring[i][1] for i in range(len(ring)))) / 2

def centroid(ring):
    a = cx = cy = 0
    for i in range(len(ring)):
        x1, y1 = ring[i - 1]; x2, y2 = ring[i]
        f = x1 * y2 - x2 * y1; a += f; cx += (x1 + x2) * f; cy += (y1 + y2) * f
    if abs(a) < 1e-9:
        return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    return (cx / (3 * a), cy / (3 * a))

def axis_hits(c, d, ring):
    """t values where the line c + t*d crosses the polygon edges."""
    ts = []
    for i in range(len(ring)):
        (x1, y1), (x2, y2) = ring[i - 1], ring[i]
        ex, ey = x2 - x1, y2 - y1
        den = d[0] * ey - d[1] * ex
        if abs(den) < 1e-12: continue
        t = ((x1 - c[0]) * ey - (y1 - c[1]) * ex) / den
        u = ((x1 - c[0]) * d[1] - (y1 - c[1]) * d[0]) / den
        if 0 <= u <= 1: ts.append(t)
    return ts

def course_id(name):
    for cid, pat in COURSES:
        if re.search(pat, name or "", re.I): return cid, True
    return None, False

def main():
    els = overpass()
    courses, greens, holes = [], [], []
    for el in els:
        t = el.get("tags", {})
        if t.get("leisure") == "golf_course":
            cid, known = course_id(t.get("name"))
            if known:
                for r in rings(el):
                    if len(r) > 3:
                        rx = [xy(p) for p in r]; courses.append((cid, area(rx), rx, t.get("name")))
        elif t.get("golf") == "green":
            for r in rings(el):
                if len(r) > 3:
                    rx = [xy(p) for p in r]; greens.append((rx, centroid(rx)))
        elif t.get("golf") == "hole" and el.get("geometry"):
            holes.append((t, [xy((g["lat"], g["lon"])) for g in el["geometry"]]))

    found, report = {}, []
    for t, line in holes:
        ref = re.match(r"\d+", t.get("ref", "") or "")
        if not ref or len(line) < 2: continue
        n = int(ref.group())
        if not 1 <= n <= 18: continue
        end = line[-1]
        hits = sorted([c for c in courses if inside(end, c[2])], key=lambda c: c[1])
        cid = hits[0][0] if hits else course_id(t.get("golf:course:name") or t.get("course"))[0]
        if not cid: continue
        # direction of play into the green: from a point ~60 m back along the line
        back, dist = line[-1], 0
        for i in range(len(line) - 1, 0, -1):
            dist += math.dist(line[i], line[i - 1]); back = line[i - 1]
            if dist >= 60: break
        d = (end[0] - back[0], end[1] - back[1]); L = math.hypot(*d) or 1; d = (d[0] / L, d[1] / L)
        g = next((g for g in greens if inside(end, g[0])), None)
        if not g:
            near = min(greens, key=lambda g: math.dist(g[1], end), default=None)
            if near and math.dist(near[1], end) < 45: g = near
        length = sum(math.dist(line[i], line[i - 1]) for i in range(1, len(line)))
        key = f"{cid}-{n}"
        if key in found and found[key]["_len"] >= length: continue
        if g:
            ts = axis_hits(g[1], d, g[0])
            if len(ts) >= 2:
                tf, tb = min(ts), max(ts)
                F = (g[1][0] + d[0] * tf, g[1][1] + d[1] * tf)
                B = (g[1][0] + d[0] * tb, g[1][1] + d[1] * tb)
                M = ((F[0] + B[0]) / 2, (F[1] + B[1]) / 2)
                found[key] = {"F": ll(F), "M": ll(M), "B": ll(B), "src": "osm", "_len": length,
                              "_note": f"green depth {round(math.dist(F, B) * 1.0936)} yd"}
                continue
        found[key] = {"M": ll(end), "src": "osm", "_len": length, "_note": "no green outline, middle = end of hole line"}

    try:
        existing = json.load(open("greens.json"))
    except Exception:
        existing = {}
    out = {k: v for k, v in existing.items() if v.get("src") != "osm"}  # keep hand-marked greens
    for k, v in found.items():
        if k not in out:
            out[k] = {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
    json.dump(dict(sorted(out.items())), open("greens.json", "w"), separators=(",", ":"))

    names = sorted({c[3] for c in courses})
    report.append(f"OSM courses matched: {', '.join(names) or 'none'}")
    report.append(f"Hole lines: {len(holes)}  Green outlines: {len(greens)}")
    for cid in ["sheep", "trails", "oldmac", "dunes", "pacific"]:
        ks = [f"{cid}-{h}" for h in range(1, 19)]
        have = [k for k in ks if k in found]
        full = [k for k in have if "F" in found[k]]
        missing = [k.split("-")[1] for k in ks if k not in found]
        report.append(f"{cid}: {len(full)} full F/M/B, {len(have) - len(full)} middle only, missing holes: {', '.join(missing) or 'none'}")
        for k in have:
            report.append(f"  {k}: {found[k]['_note']}")
    open("greens-report.txt", "w").write("\n".join(report) + "\n")
    print("\n".join(report))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        # leave the error where it can be read from the repo, without failing the run
        open("greens-report.txt", "w").write("FAILED\n" + traceback.format_exc())
        print(open("greens-report.txt").read())
