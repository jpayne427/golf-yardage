# ShipStiffs

Golf-trip app for the group: live team scoring (match play, Stableford, skins) and a GPS yardage map.

- `/` – the scoring app (Battle). Data lives in Supabase (`config.js`); anyone can view, the trip PIN unlocks scoring.
- `/map/` – satellite yardage map with GPS, tap-for-yards, and front/middle/back of each green. Deep link a hole with `map/#oldmac-7` (course ids: sheep, trails, oldmac, dunes, pacific).
- `greens.json` – green and tee positions, rebuilt from OpenStreetMap by the "Build greens" GitHub Action (`tools/build_greens.py`). Hand-marked greens (no `"src": "osm"`) are kept.
- `brand/` – logo and app icons.
