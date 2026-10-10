# Coordination log

Mailbox between the Claude sessions working on ShipStiffs for Joe. The cloud session
writes entries headed `— cloud`, and the PC session (on Joe's Windows machine) writes
entries headed `— pc`. Newest entries go at the top. Pull before editing.

This repo is public, so never put PINs, API keys, or player names and handicaps here.

---

## 2026-10-10 15:51 UTC — cloud

**Status**
- Repo: https://github.com/jpayne427/golf-yardage. Branch `main`, which is live on GitHub Pages at https://shipstiffs.com. A push goes live within about 10 minutes.
- The app: ShipStiffs, a phone web app for golf trips.
  - Home page: `index.html`.
  - Event apps:
    - `bandon-2026/` is the Bandon Dunes trip, Oct 16–18, 2026. It's the main event: 8 players, 2 teams, match play and Stableford with handicap allowances, skins, scorecard scanner, GPS yardage map.
    - `redtail/` is a 2-person, 9-hole test drive at RedTail, Portland, on Sun Oct 11.
  - Standalone yardage map: `map/`.
- Backend is Supabase (project URL and anon key are in `config.js`; the anon key is public by design).
  - Table `public.docs`, with writes only through the `write_doc` RPC, which checks the PIN.
  - Each event has its own PIN, set up by `supabase/event-pins.sql`. The organizer PIN unlocks all events. The PINs live only in the database. Joe has them.
  - Edge function `supabase/functions/scan-scorecard` reads scorecard photos with Claude. The API key is in Supabase secrets only.
- Greens data: `greens.json`.
  - Built from OpenStreetMap by `tools/build_greens.py`, through the GitHub Action `greens.yml`.
  - Entries with `src: "hand"` (marked by Joe) and `src: "eye"` (marked by the cloud session from satellite crops) are kept on rebuild.
- Code conventions:
  - Edit `bandon-2026/index.html`, then run `tools/sync-events.sh` to copy it to `redtail/index.html`. Never edit the copy.
  - Each event's data is namespaced by folder name. Bandon collections have no prefix; other events use `<event>.`.

**Done since last entry**
- Event-specific PINs. The SQL is run, and Joe has set and checked both PINs.
- Front, middle and back for 50 more greens, marked by eye from satellite crops (`tools/green_crops.py`, crops on the `green-crops` branch). Sheep Ranch 2 now uses Joe's hand marks.
- Earlier: courses scanned and saved; per-tee ratings with a "Playing from" picker; 9-hole (front/back) matches; 1v1 game picker; first-run setup for new events; tab and home icons; home-screen install banner; safe-area fixes for iPhone home-screen mode.

**Questions / blockers for PC or Joe**
- Greens still middle-only:
  - Bandon: Dunes 10, Pacific 3, Pacific 12, Trails 10.
  - RedTail: 2, 10, 13, 15.
  - Joe can mark them on the map (Mark green), then use ⋯ → Share data and paste the result to the cloud session.
- Least-certain eyeballed greens, worth a visual check on a big screen:
  - Old Mac 10, 11, 12
  - Bandon Dunes 6, 15
  - Pacific 6, 11
  - RedTail 4, 5, 9, 14, 17
- Before the group gets the Bandon link, Joe still needs to:
  - Clear the test data: Bandon `cards` rows plus the stray "New player" row. The cloud session gave him SQL that lists the rows first, then deletes them.
  - Confirm the "Playing from" tees per course in Setup.
- Side games beyond skins wait on the group's choice.

**Needs from PC**
- Nothing blocking. Useful if you can:
  - Spot-check the green marks above on https://shipstiffs.com/map/.
  - Test the RedTail flow in a desktop browser before Sunday.
- If you change code, edit `bandon-2026/index.html` and run `tools/sync-events.sh`. Note what you pushed in a `— pc` entry so the cloud session pulls before editing.
- After Bandon (no big changes before then):
  - Per-player tees
  - Real multi-event flow (Joe's Matches, Battle 2027)
  - Scoring for scramble and shamble formats
  - Course library
  - Freeze `bandon-2026`
