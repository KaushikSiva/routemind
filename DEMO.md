# Demoing RouteMind

A 2-minute demo that shows **recursive self-improvement on MongoDB Atlas, at scale**: a car learns
the real **Shack 15 → Ocean Beach** drive by forgetting its own wrong turns, out of 1,081 memories.

---

## The one-liner

> "A car starts at Shack 15 with a head full of wrong directions. Every trip it recalls a turn from
> memory, gets corrected, and the memory **forgets the turns that misled it** — so over four trips it
> teaches itself the real drive to Ocean Beach. Same 1,081 memories with the learning switched off
> (plain RAG) never get past the first turn."

## What it is (and isn't)

- It is **self-improving agent memory**: recall → act → score what helped → forget the noise → better recall.
- It is **not RAG**. RAG retrieves by frozen similarity. Here the *ranking changes* as the agent learns
  and bad memories are *deleted*. The RAG line in the graph is the exact same code with learning off —
  the control that proves the lift is the learning, not the embeddings.

---

## Option A — the localhost app (best for a laptop/booth)

```bash
source .venv/bin/activate
python app.py          # → open http://localhost:5050
```

Press **Drive**: the car drives the real SF map, the green path grows each trip, and the curve fills in
live until it arrives. Then toggle **learning off** and press Drive again — plain RAG, stuck at the
same wrong turn forever. The engine runs for real on each click (local vector store; embeddings cached
at startup). *Port 5050, not 5000 — macOS AirPlay squats on 5000.*

## Option B — the live Atlas run (best to prove MongoDB)

```bash
python run_nav.py --atlas --rounds 14
```

Point at three things as it prints:
1. The header: **"1,081 turn-memories … Atlas Vector Search must find each junction's turn inside all 1,081 vectors."**
2. The **RouteMind column walking forward**: lost @ j1 → j4 → j5 → **ARRIVED**. The memory healing itself.
3. The **RAG column frozen** at 6/11, every trip. Same memories, no learning.

## Option C — just play the clip (20 seconds)

`docs/learning.mp4` (the green route growing) + `docs/curve.png` (the graph) + the one-liner.

---

## If asked "where's the MongoDB?"

- Memories live in Atlas collection `mnemo.memories`; recall is a **`$vectorSearch`** on the `mnemo_vec`
  index (`memory.py` → `AtlasStore.search`), **filtered to the current junction** so it scopes recall
  inside 1,081 vectors.
- Learning writes back to Atlas: `update_stats` persists each memory's usefulness, `delete`/`prune`
  forgets the ones that keep misleading.
- In-process we keep an authoritative usefulness cache because the Atlas **search index is eventually
  consistent** — we don't re-rank on a stale index mid-demo. Judges like this detail.

## Recording the video

`render_nav.py` already builds `out/sf/learning.mp4` (+ `.gif`). To also capture the localhost app or the
live Atlas run, screen-record with QuickTime (Cmd-Shift-5). A 60-second cut:
**(0–10s)** one-liner over the Shack 15 pin · **(10–40s)** press Drive in the app, the route completing ·
**(40–60s)** toggle learning off, RAG stuck — freeze there.

## Numbers for a slide

| | |
|---|---|
| Route | Shack 15 (Ferry Building) → Ocean Beach, San Francisco (real OSM roads, 13.9 km) |
| Memory store | **1,081** vectors on MongoDB Atlas (`$vectorSearch`) |
| Signal vs. noise | 33 correct turns vs. 1,048 wrong/decoy turns |
| RouteMind (learns) | **arrives by trip 4** (11/11 turns) |
| RAG (frozen, same memory) | **never past the 1st turn** (6/11), all trips |
