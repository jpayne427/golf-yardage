"""Build greens.json (front/middle/back of each green) from OpenStreetMap.

Uses golf=hole lines (drawn tee -> green) and golf=green polygons for each
area in AREAS (Bandon Dunes resort, RedTail in Portland, ...). Front/back are where the line of play, extended through
the green's center, crosses the green's edge. Entries already in greens.json
that were not generated here (no "src": "osm") are kept as-is.
"""
import json, math, re, time, traceback, urllib.parse, urllib.request

# Each area is fetched and matched separately. courses: (id, name pattern), first match wins,
# None = ignore. named: courses with their own OSM outline. shared: courses that share one
# outline and are told apart by card pars. default: id for routings when the area has one course.
AREAS = [
    {"name": "Bandon Dunes", "bbox": (43.14, -124.44, 43.25, -124.35),
     "courses": [(None, r"preserve|shorty|punchbowl|practice|range"), ("sheep", r"sheep"), ("trails", r"trails"),
                 ("oldmac", r"old\s*mac"), ("pacific", r"pacific"), ("dunes", r"bandon dunes")],
     "named": ("sheep", "trails"), "shared": ("oldmac", "dunes", "pacific"), "default": None,
     "ids": ["sheep", "trails", "oldmac", "dunes", "pacific"]},
    {"name": "RedTail (Portland)", "bbox": (45.42, -122.86, 45.51, -122.73),
     "courses": [(None, r"practice|range|driving|par\s*3|executive|pitch"), ("redtail", r"red\s*tail")],
     "named": ("redtail",), "shared": (), "default": "redtail", "ids": ["redtail"]},
]
BBOX = AREAS[0]["bbox"]; COURSES = AREAS[0]["courses"]; AREA = AREAS[0]   # set per area in main()
# card pars, used to check which routing belongs to which course
PARS = {
    "sheep":  [5,4,3,4,3,4,3,4,4,4,5,4,5,4,4,3,4,5],
    "trails": [4,3,5,4,3,4,4,4,5,4,4,3,4,4,4,5,3,4],
    "oldmac": [4,3,4,4,3,5,4,3,4,4,4,3,4,4,5,4,5,4],
    "dunes":  [4,3,5,4,4,3,4,4,5,4,4,3,5,4,3,4,4,5],
    "pacific": [4,4,5,4,3,4,4,4,4,3,3,5,4,3,5,4,3,5],
}
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
def use_area(a):
    global BBOX, COURSES, AREA, LAT0, KX
    AREA, BBOX, COURSES = a, a["bbox"], a["courses"]
    LAT0 = (BBOX[0] + BBOX[2]) / 2; KX = 111320 * math.cos(math.radians(LAT0))
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

def process():
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

    report = []
    # holes inside non-championship areas (Preserve, Shorty's, practice) are dropped
    def skip(pt):
        return any(c[0] is None and inside(pt, c[2]) for c in courses)
    H = []
    for t, line in holes:
        ref = re.match(r"\d+", t.get("ref", "") or "")
        if not ref or len(line) < 2: continue
        n = int(ref.group())
        if 1 <= n <= 18 and not skip(line[-1]):
            H.append({"n": n, "line": line, "len": sum(math.dist(line[i], line[i-1]) for i in range(1, len(line)))})
    # follow each routing: green of hole n -> nearest tee of hole n+1
    used, chains = set(), []
    for h in sorted([h for h in H if h["n"] == 1], key=lambda h: -h["len"]):
        if id(h) in used: continue
        chain, cur = [h], h
        used.add(id(h))
        while cur["n"] < 18:
            cands = [x for x in H if x["n"] == cur["n"] + 1 and id(x) not in used]
            if not cands: break
            nx = min(cands, key=lambda x: math.dist(x["line"][0], cur["line"][-1]))
            if math.dist(nx["line"][0], cur["line"][-1]) > 450: break
            chain.append(nx); used.add(id(nx)); cur = nx
        if len(chain) >= 9: chains.append(chain)
    # label chains: named course outline first, then north-to-south for the resort courses
    def named(chain):
        votes = {}
        for h in chain:
            hits = sorted([c for c in courses if c[0] and inside(h["line"][-1], c[2])], key=lambda c: c[1])
            if hits and hits[0][0] in AREA["named"]:
                votes[hits[0][0]] = votes.get(hits[0][0], 0) + 1
        return max(votes, key=votes.get) if votes else None
    def par_of(yd): return 3 if yd < 250 else 5 if yd > 475 else 4
    def par_match(chain, cid):
        if cid not in PARS: return None
        return sum(1 for h in chain if par_of(h["len"] * 1.0936) == PARS[cid][h["n"] - 1])
    labels, rest = {}, []
    for i, ch in enumerate(chains):
        cid = named(ch)
        if cid and cid not in labels.values(): labels[i] = cid
        else: rest.append(i)
    # resort courses share one outline: give each routing the course whose card pars it fits best
    import itertools
    left = [c for c in AREA["shared"] if c not in labels.values()]
    best, best_score = (), -1
    for perm in itertools.permutations(left, min(len(left), len(rest))):
        score = sum(par_match(chains[i], cid) for i, cid in zip(rest, perm))
        if score > best_score: best, best_score = perm, score
    for i, cid in zip(rest, best): labels[i] = cid
    # single-course area with no outline in OSM: the longest routing is that course
    if AREA["default"] and AREA["default"] not in labels.values():
        free = [i for i in range(len(chains)) if i not in labels]
        if free: labels[max(free, key=lambda i: len(chains[i]))] = AREA["default"]
    report.append(f"Routings found: {len(chains)} (lengths {', '.join(str(len(c)) for c in chains)})")
    for i, ch in enumerate(chains):
        cid = labels.get(i, "?")
        lat = sum(h["line"][-1][1] for h in ch) / len(ch) / KY
        pm = par_match(ch, cid)
        report.append(f"  routing {i}: {cid}, {len(ch)} holes, avg lat {lat:.4f}, hole yards " +
                      " ".join(f"{h['n']}:{round(h['len']*1.0936)}" for h in ch) +
                      (f", par check {pm}/{len(ch)}" if pm is not None else ""))
    found = {}
    for i, ch in enumerate(chains):
        cid = labels.get(i)
        if not cid: continue
        for h in ch:
            line, end = h["line"], h["line"][-1]
            back, dist = line[-1], 0
            for j in range(len(line) - 1, 0, -1):
                dist += math.dist(line[j], line[j - 1]); back = line[j - 1]
                if dist >= 60: break
            d = (end[0] - back[0], end[1] - back[1]); L = math.hypot(*d) or 1; d = (d[0] / L, d[1] / L)
            g = next((g for g in greens if inside(end, g[0])), None)
            if not g:
                near = min(greens, key=lambda g: math.dist(g[1], end), default=None)
                if near and math.dist(near[1], end) < 45: g = near
            key = f"{cid}-{h['n']}"
            entry = {"M": ll(end), "src": "osm", "_note": "no green outline, middle = end of hole line"}
            if g:
                ts = axis_hits(g[1], d, g[0])
                if len(ts) >= 2:
                    tf, tb = min(ts), max(ts)
                    F = (g[1][0] + d[0] * tf, g[1][1] + d[1] * tf)
                    B = (g[1][0] + d[0] * tb, g[1][1] + d[1] * tb)
                    depth = math.dist(F, B) * 1.0936
                    if 12 <= depth <= 65:
                        entry = {"F": ll(F), "M": ll(((F[0]+B[0])/2, (F[1]+B[1])/2)), "B": ll(B), "src": "osm",
                                 "_note": f"green depth {round(depth)} yd"}
                    else:
                        entry = {"M": ll(g[1]), "src": "osm", "_note": f"odd green shape ({round(depth)} yd deep), middle = green center"}
            entry["T"] = ll(line[0])  # tee end of the hole line, used to point the map up the hole
            found[key] = entry

    names = sorted({c[3] for c in courses})
    report.insert(0, f"OSM courses matched: {', '.join(names) or 'none'}")
    report.insert(1, f"Hole lines: {len(holes)}  Green outlines: {len(greens)}")
    for cid in AREA["ids"]:
        ks = [f"{cid}-{h}" for h in range(1, 19)]
        have = [k for k in ks if k in found]
        full = [k for k in have if "F" in found[k]]
        missing = [k.split("-")[1] for k in ks if k not in found]
        report.append(f"{cid}: {len(full)} full F/M/B, {len(have) - len(full)} middle only, missing holes: {', '.join(missing) or 'none'}")
        for k in have:
            report.append(f"  {k}: {found[k]['_note']}")
    return found, report

def main():
    found, report, failed = {}, [], set()
    for a in AREAS:
        use_area(a)
        report.append(f"===== {a['name']} =====")
        try:
            f, r = process()
            found.update(f); report += r
        except Exception:
            failed.update(a["ids"])
            report.append("FAILED\n" + traceback.format_exc())
    try:
        existing = json.load(open("greens.json"))
    except Exception:
        existing = {}
    out = {k: v for k, v in existing.items() if v.get("src") != "osm"}  # keep hand-marked greens
    for k, v in found.items():
        if k not in out:
            out[k] = {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
        elif "T" not in out[k]:
            out[k]["T"] = v["T"]  # hand-marked green: borrow the tee from the map
    # an area whose download failed this time keeps the greens it had
    for k, v in existing.items():
        if v.get("src") == "osm" and k.split("-")[0] in failed and k not in out:
            out[k] = v
    json.dump(dict(sorted(out.items())), open("greens.json", "w"), separators=(",", ":"))
    open("greens-report.txt", "w").write("\n".join(report) + "\n")
    print("\n".join(report))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        # leave the error where it can be read from the repo, without failing the run
        open("greens-report.txt", "w").write("FAILED\n" + traceback.format_exc())
        print(open("greens-report.txt").read())
