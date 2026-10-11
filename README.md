<h1 align="center">🚗 RouteMind</h1>

<p align="center"><b>A car that teaches itself a route on real roads — by learning from its own wrong turns.</b></p>

<p align="center">
  Drive from <b>Kodambakkam railway station</b> to <b>Jains Antariksha</b> (Chennai). The streets and
  turns are real (OpenStreetMap). The car starts with a head full of <i>wrong</i> directions and,
  trip by trip, learns which turns actually get it there — recursive self-improvement you can watch
  on the map.
</p>

---

## Watch it learn

<p align="center">
  <img src="docs/learning.gif" width="760" alt="RouteMind learning the Kodambakkam → Jains Antariksha route trip by trip"><br>
  <i>Every trip the green path pushes further down the real route — until it arrives. (<a href="docs/learning.mp4">mp4</a>)</i>
</p>

| Trip 1 — lost at the 1st turn | Trip 3 — most of the way | Trip 7 — arrives |
|---|---|---|
| ![t1](docs/trip_01.png) | ![t3](docs/trip_03.png) | ![t7](docs/trip_07.png) |

Run on **MongoDB Atlas Vector Search over 1,026 turn-memories** (18 correct, 1,008 noise — of which
960 are decoy turns from 160 other Chennai junctions the search has to sift through):

```
 trip | turns right | result            || RAG (frozen memory)
   1  |    2/6      | lost @ junction 2  ||  2/6  lost @ junction 1
   3  |    4/6      | lost @ junction 4  ||  2/6  lost @ junction 1
   5  |    5/6      | lost @ junction 5  ||  2/6  lost @ junction 1
   7  |    6/6      | ARRIVES ✅          ||  2/6  still lost
```

Watch the failure point **walk forward down the route** — j2 → j4 → j5 → arrived — as the memory
forgets its bad turns. The car (Mnemo) **arrives by trip 7**. A frozen-memory baseline (RAG), same
1,026 memories but no learning, **never gets past the first turn.**

## How it works

- **Real route:** we geocode the two points and pull the actual driving route + turn-by-turn from
  OpenStreetMap (Nominatim + OSRM) — real Kodambakkam streets.
- **The task:** at each junction the car **recalls which way to turn** from memory. Its memory holds
  the correct turn **plus noise** — wrong turns from bad past trips.
- **It compounds:** one wrong recall sends it off-route, so a trip only completes when **every**
  junction is recalled correctly.
- **The self-improvement:** each trip is graded (and the car is corrected, so every junction gets
  learned). The memory engine scores each remembered turn by whether recalling it helped, **keeps the
  good ones, forgets the wrong ones** — so the route locks in over a handful of trips, with no retraining.

That feedback loop — recall → drive → learn what helped → forget the noise → **better recall next trip** —
is the recursive self-improvement.

> **Demoing this?** See [DEMO.md](DEMO.md) — the one-liner, the live Atlas run to show on stage, and how to record the clip.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install openai pymongo python-dotenv numpy staticmap matplotlib pillow
# .env: OPENAI_API_KEY (embeddings), optional MONGODB_URI

python run_nav.py              # learn the route (local vector store)
python run_nav.py --atlas      # same, backed by MongoDB Atlas Vector Search (1,026 memories)
python render_nav.py           # render per-trip maps + stitch out/learning.mp4 and out/learning.gif
```

**Scale:** the store holds **1,026 vectors** — the route's own turns plus 960 decoy turns from 160
other Chennai junctions. Recall is a **filtered `$vectorSearch`** scoped to the current junction, so
Atlas finds this junction's three candidate turns inside the whole city's worth of memories, and the
usefulness-weighting picks the one that actually gets the car there.

## Credits

- **OpenStreetMap** — the road network · **Nominatim** (geocoding) · **OSRM** (routing) · **staticmap** (tiles).
- Memory engine (`memory.py`) is the **Mnemo** self-improving memory: usefulness-weighted recall + forgetting
  on a vector store (local or **MongoDB Atlas**).
- Everything else here (`nav_tasks.py`, `run_nav.py`, `render_nav.py`) written for this demo.

---

<p align="center"><i>It got lost, then it learned the way.</i></p>
