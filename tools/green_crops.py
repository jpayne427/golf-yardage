"""Satellite close-ups of greens that only have a middle, for marking front/back by eye.

For every green in greens.json without F/B, fetches Esri World Imagery around it,
rotates it so the line of play runs up the image (approach from the bottom), and
draws a yard grid centred on the current middle. Saves crops/<key>.jpg plus
crops/index.json (middle, direction of play) so marks read off the grid
("front -14, back +16, centre 3 right") can be turned back into lat/lon.
Runs on GitHub Actions (.github/workflows/green-crops.yml).
"""
import io, json, math, os, sys, time, urllib.request
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import build_greens as bg

Z = 19                       # Esri tile zoom (~0.22 m/px at Bandon)
HALF = 60                    # yards shown each side of the middle
SCALE = 2                    # upscale for readability
TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
YD = 0.9144

def px(lat, lon):            # global pixel coords at zoom Z
    n = 256 * 2 ** Z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y

_cache = {}
def tile(x, y):
    if (x, y) not in _cache:
        for attempt in range(3):
            try:
                req = urllib.request.Request(TILE.format(z=Z, x=x, y=y), headers={"User-Agent": "golf-yardage green crops"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    _cache[(x, y)] = Image.open(io.BytesIO(r.read())).convert("RGB"); break
            except Exception as ex:
                print("tile", x, y, ex); time.sleep(2)
        else:
            _cache[(x, y)] = Image.new("RGB", (256, 256), (60, 60, 60))
    return _cache[(x, y)]

def font(size):
    try: return ImageFont.load_default(size=size)
    except TypeError: return ImageFont.load_default()

def crop(key, M, A):
    lat, lon = M
    mpp = 156543.03392 * math.cos(math.radians(lat)) / 2 ** Z      # metres per pixel
    ypp = mpp / YD                                                 # yards per pixel
    r = int(HALF * 1.5 / ypp) + 2                                  # radius to fetch (room to rotate)
    cx, cy = px(lat, lon)
    x0, y0 = int(cx - r) // 256, int(cy - r) // 256
    x1, y1 = int(cx + r) // 256, int(cy + r) // 256
    mosaic = Image.new("RGB", ((x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256))
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            mosaic.paste(tile(tx, ty), ((tx - x0) * 256, (ty - y0) * 256))
    mx, my = cx - x0 * 256, cy - y0 * 256
    # direction of play in metres (east, north), from the approach point to the middle
    de = (lon - A[1]) * 111320 * math.cos(math.radians(lat)); dn = (lat - A[0]) * 110540
    ang = math.degrees(math.atan2(dn, de))                         # maths angle, 90 = north
    img = mosaic.rotate(90 - ang, resample=Image.BICUBIC, center=(mx, my))
    h = int(HALF / ypp)
    img = img.crop((int(mx) - h, int(my) - h, int(mx) + h, int(my) + h))
    img = img.resize((img.width * SCALE, img.height * SCALE), Image.LANCZOS)
    d = ImageDraw.Draw(img, "RGBA"); c = img.width / 2; k = SCALE / ypp   # pixels per yard
    f, fb = font(14), font(18)
    for yd in range(-HALF, HALF + 1, 5):
        p = c - yd * k            # up = +yards (long), right = +yards (right of the line)
        q = c + yd * k
        major = yd % 10 == 0
        col = (255, 255, 255, 110 if major else 45)
        d.line([(0, p), (img.width, p)], fill=col, width=1)
        d.line([(q, 0), (q, img.height)], fill=col, width=1)
        if major and yd:
            d.text((4, p - 8), f"{yd:+d}", fill=(255, 255, 0, 255), font=f, stroke_width=2, stroke_fill="black")
            d.text((q - 10, img.height - 18), f"{yd:+d}", fill=(0, 255, 255, 255), font=f, stroke_width=2, stroke_fill="black")
    d.line([(c, 0), (c, img.height)], fill=(255, 80, 80, 200), width=2)
    d.line([(0, c), (img.width, c)], fill=(255, 80, 80, 120), width=1)
    d.ellipse([c - 6, c - 6, c + 6, c + 6], outline=(255, 80, 80, 255), width=3)
    d.text((8, 6), f"{key}   play goes UP   yellow = yards long(+)/short(-)   cyan = yards right(+)/left(-)",
           fill="white", font=fb, stroke_width=2, stroke_fill="black")
    img.save(f"crops/{key}.jpg", quality=85)
    return {"M": M, "dir": [round(de, 3), round(dn, 3)]}

def main():
    existing = json.load(open("greens.json"))
    os.makedirs("crops", exist_ok=True)
    index = {}
    for a in bg.AREAS:
        bg.use_area(a)
        try:
            found, _ = bg.process()
        except Exception as ex:
            print("area failed", a["name"], ex); continue
        for key, v in sorted(found.items()):
            g = existing.get(key, {})
            if "F" in g or g.get("src", "osm") != "osm": continue
            A = v.get("_A") or v.get("T")
            if not A or A == v["M"]: continue
            index[key] = crop(key, g.get("M", v["M"]), A)
            print("crop", key)
    json.dump(index, open("crops/index.json", "w"), indent=1)
    print(len(index), "crops")

if __name__ == "__main__":
    main()
