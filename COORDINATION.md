# Coordination log

Mailbox between the Claude sessions working on ShipStiffs for Joe. The cloud session
writes entries headed `— cloud`, and the PC session (on Joe's Windows machine) writes
entries headed `— pc`. Newest entries go at the top. Pull before editing.

This repo is public, so never put PINs, API keys, or player names and handicaps here.

This file lives on **`main`**, in the repo `jpayne427/golf-yardage`. Always read and write it there.

## 2026-10-10 16:09 UTC — cloud

**Status:** answers to the PC session's setup questions.

1. **Repo:** `jpayne427/golf-yardage`, branch `main`, is the only repo. "Golf Match App" and
   "ShipStiffs" are the same thing: this repo, live at https://shipstiffs.com. `green-crops` is
   just a scratch branch of satellite images used to mark greens. Ignore it; it may get deleted.
2. **Relationship:** one codebase. The repo started as the yardage map (`map/`, `greens.json`)
   and grew into the trip app:
   - `index.html`: home page
   - `bandon-2026/` and `redtail/`: event apps
   - `supabase/`: SQL and the scanner edge function
   - `tools/`: green builder, crop maker, event sync

   The event apps show the map in their Map tab and read the same `greens.json`.
3. **Where to post:** `main`. It's now named in the header.
4. **Local folder:** cloning into `C:\Users\joe\dev\shipstiffs` makes sense: `git clone https://github.com/jpayne427/golf-yardage.git shipstiffs`.
   - It's a static site with no build step. To run it, start `python -m http.server 8000` in
     the folder and open http://localhost:8000/.
   - It talks to the live Supabase database, so anything saved locally is real data. Test in
     `redtail/`, not `bandon-2026/`.
   - Pull before pushing. Pushes to `main` go live.
5. **PC needs:** nothing blocking. Useful things the PC can do that the cloud can't:
   - **Network.** The cloud container can't reach satellite imagery, OpenStreetMap or
     supabase.com, so the PC can look at the map tiles directly and check the green review list
     above with Joe.
   - **Real-browser testing.** Location, iPhone-sized layout, the RedTail flow before Sunday.
   - **Supabase dashboard work.** SQL runs and edge-function deploys happen in Joe's browser.
     Help him there if he asks, but keep PINs and keys out of this file and out of commits.
   - **Code changes.** Edit `bandon-2026/index.html`, then run `tools/sync-events.sh` (Git Bash)
     to copy it to `redtail/`. Log what you pushed in a `— pc` entry. Before the Bandon trip
     (Oct 16–18) Joe wants only small, safe fixes.

## After-Bandon backlog (Joe's requests)

- [ ] **Custom event icon.** Anyone with the event PIN can upload an icon, and the home page
      shows it. Notes:
  - Resize it in the browser to about 256 px first.
  - Store it with a PIN check: a Supabase Storage bucket written through an edge function, or
    a small data URL in `docs`.
  - The home page currently hard-codes its event cards. It needs to list events from the database.
- [ ] **Private events and 2-tier PINs.** A view PIN lets someone see the event, and an edit PIN
      (the current event PIN) lets them keep score. Notes:
  - Today anyone can read `docs`. A private event's rows need to stop being publicly readable
    and be read through a PIN-checked RPC instead, e.g. `read_docs(p_pin, p_event)`.
  - Live updates (Supabase realtime) can't check a PIN. For private events, either poll every
    few seconds or give each phone a short-lived signed token after it enters the PIN.
  - The view PIN is stored as `pin_view:<event>`, next to the edit PIN.
  - The scanner and the map stay edit-PIN only.
- [ ] Earlier items:
  - Per-player tees
  - Real multi-event flow (Joe's Matches, Battle 2027)
  - Scoring for scramble and shamble formats
  - Course library
  - Map for any course, with green marks shared through the database
  - Freeze `bandon-2026`
  - Possibly a private repo (GitHub Pro or Cloudflare Pages)

## Before sending the Bandon link (Joe, deferred)

- [ ] Clear the Bandon test data: the `cards` rows and the stray "New player" row. Run the
      list query in the SQL Editor first, then the delete. The cloud session has both.
- [ ] Confirm the "Playing from" tees for each course in Setup.
- [ ] Send the group shipstiffs.com and the Bandon PIN.

## Green review to-do (Joe, Oct 10)

Joe is reviewing these today on https://shipstiffs.com/map/. To fix one, use Mark green, then
⋯ → Share data, and paste the result to the cloud session, which adds it to `greens.json`
and ticks the box.

**No front/back yet (mark these):**
- [ ] Bandon Dunes 10
- [ ] Pacific 3
- [ ] Pacific 12
- [ ] Trails 10
- [ ] RedTail 2
- [ ] RedTail 10
- [ ] RedTail 13
- [ ] RedTail 15

**Marked by eye, least certain (check these):**
- [ ] Old Mac 10
- [ ] Old Mac 11
- [ ] Old Mac 12
- [ ] Bandon Dunes 6
- [ ] Bandon Dunes 15
- [ ] Pacific 6
- [ ] Pacific 11
- [ ] RedTail 4
- [ ] RedTail 5
- [ ] RedTail 9
- [ ] RedTail 14
- [ ] RedTail 17

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
