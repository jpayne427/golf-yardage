# Services

Every outside service ShipStiffs depends on, what it's for, and what happens when a limit is hit.
"Confirm" means the repo can't tell us; Joe should fill it in. Plan limits are from the providers'
published free tiers as of October 2026; check their pricing pages before relying on a number.
No keys, PINs or account details belong in this file (the repo is public).

| Service | What we use it for | Who pays / plan | Limits that matter | Alerts and bills go to |
|---|---|---|---|---|
| **GitHub** (`jpayne427/golf-yardage`) | Code, history, and hosting the site on GitHub Pages; Actions run the green builder (`greens.yml`) and satellite crops (`green-crops.yml`) | Joe's personal account, not the Swiftwater-Capital org. Public repo, so Pages and Actions minutes are free | **Pages:** 1 GB site, about 100 GB/month bandwidth and 10 builds/hour (soft limits; GitHub emails before acting). Changes take up to ~10 min to show. **Actions:** free for public repos. Both workflows run only by hand or when their own files change, never on PRs. If the repo goes private, minutes count against Joe's personal free allowance | Confirm (GitHub account email) |
| **Domain `shipstiffs.com`** | The site's address (`CNAME` file points Pages at it) | Confirm (registrar and renewal date) | **Expiry:** if it lapses the site disappears from that address (still at the github.io URL). Turn on auto-renew | Confirm |
| **Cloudflare DNS** | DNS for shipstiffs.com, pointing at GitHub Pages | Confirm (likely free plan) | None in practice on the free plan. A wrong DNS change takes the site offline until fixed | Confirm |
| **Supabase** (one project) | The database for every event (setup, players, rounds, matches, scores, games), live updates between phones, the PIN checks (database functions), and the `scan-scorecard` Edge Function. The Anthropic API key lives only in its Edge Function secrets | Confirm (plan; free tier assumed) | **Free tier pauses the project after about 7 days with no activity:** the app then can't load or save scores until it's restored from the Supabase dashboard. Open the app (or the dashboard) at least weekly before a trip. **Database:** 500 MB (we use a tiny fraction). **Realtime:** about 200 concurrent connections and 2M messages/month, far above 8 phones. **Edge Functions:** about 500K calls/month. Over a limit, writes or live updates can be refused until the next cycle or an upgrade | Confirm |
| **Anthropic API** | Reads scorecard photos for the Setup tab's "Scan scorecard" (Claude Sonnet, called from the Supabase Edge Function) | Confirm (prepaid credits or invoiced; who holds the account) | **Spend:** each scan costs a few cents. If credits run out or a spend limit is hit, scanning fails with an error; everything else works and cards can be typed in by hand. Set a monthly spend limit in the Console | Confirm |
| **Claude Code cloud sessions** | The AI sessions that build and maintain the app (this repo's commits) | Confirm (Joe's Claude plan) | **Usage limits on the plan:** when reached, sessions pause until the limit resets. The live app doesn't depend on them | Confirm |
| **Esri World Imagery** (`server.arcgisonline.com`) | Satellite map tiles on the Map tab; `tools/green_crops.py` also fetches tiles to mark greens by eye | Free, no account or key | **Terms:** Esri's basemap terms require attribution (shown on the map) and are aimed at ArcGIS use; very heavy use could need an ArcGIS account. If tiles stop loading, the map goes grey but GPS yardages to saved greens still work. Confirm the terms are fine for a private group app | None (no account) |
| **jsDelivr CDN** | Loads `supabase-js` 2.45.4 and `leaflet-rotate` 0.2.8 (pinned versions) | Free | If the CDN is down, the app can't load (scores) or the map can't rotate. Rare | None |
| **cdnjs (Cloudflare)** | Loads Leaflet 1.9.4 (the map library) | Free | If down, the Map tab can't load. Rare | None |
| **Google Fonts** | Big Shoulders Display and IBM Plex Sans | Free | If unavailable, pages fall back to system fonts. Nothing breaks | None |

## Free data sources

| Source | What we use it for | Terms to keep |
|---|---|---|
| **OpenStreetMap** (via Overpass API mirrors: overpass-api.de, overpass.private.coffee, maps.mail.ru, overpass.kumi.systems) | Green and tee shapes that `tools/build_greens.py` turns into `greens.json` (only on demand; the app never calls Overpass) | ODbL: keep the "© OpenStreetMap contributors" credit. Overpass is a fair-use public service; the builder tries the next mirror if one is busy |
| **Esri World Imagery** | Background imagery, and crops for marking greens by eye | Keep the Esri attribution on the map |
| **Course scorecards** (Bandon Dunes courses, Bandon Crossings) | Pars, handicap holes, ratings, slopes, yardages and green depths (`tools/cards/`, course setup in the app) | Facts from published cards; we don't republish the card images |
