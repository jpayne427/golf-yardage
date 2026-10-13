"""Set front/back of each green from a scorecard's green depths ("+11 / -11" = back 11 yd past
the middle, front 11 yd short), along the line from the tee (T) through the middle (M).
Usage: python3 tools/apply_card_depths.py shortys   (reads tools/cards/shortys.json, updates greens.json)
Entries become src "card" so the OSM builder keeps them."""
import json, math, sys
course = sys.argv[1]
card = json.load(open(f"tools/cards/{course}.json"))
front, back = card["green_depth_yards"]["front"], card["green_depth_yards"]["back"]
g = json.load(open("greens.json"))
YD = 0.9144
done, skipped, moved = [], [], []
for i in range(card["holes"]):
    k = f"{course}-{i + 1}"
    e = g.get(k)
    if not e or "M" not in e or "T" not in e:
        skipped.append(i + 1); continue
    M, T = e["M"], e["T"]
    kx, ky = 111320 * math.cos(math.radians(M[0])), 110540
    dx, dy = (M[1] - T[1]) * kx, (M[0] - T[0]) * ky
    L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    want = card["yards_to_center"]["back"][i] * YD   # OSM's tee is the back tee; the card measures to the middle
    if abs(L - want) > 12 * YD:   # e.g. a shared double green: OSM's middle is the centre of the whole thing
        moved.append(f"{i + 1} ({round(L / YD)} -> {card['yards_to_center']['back'][i]} yd)")
        M = [round(T[0] + uy * want / ky, 6), round(T[1] + ux * want / kx, 6)]; L = want
    pt = lambda yd: [round(M[0] + uy * yd * YD / ky, 6), round(M[1] + ux * yd * YD / kx, 6)]
    g[k] = {"F": pt(-front[i]), "M": M, "B": pt(back[i]), "T": T, "src": "card"}
    done.append(f"{i + 1} ({round(L / YD)} yd tee to middle, card {card['yards_to_center']['back'][i]})")
json.dump(dict(sorted(g.items())), open("greens.json", "w"), separators=(",", ":"))
print("set from card:", "; ".join(done))
print("no middle/tee in greens.json yet:", skipped or "none")
print("middle moved to the card distance (check these on the map):", moved or "none")
