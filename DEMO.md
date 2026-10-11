# Demoing RouteMind

A 2-minute live demo that shows **recursive self-improvement on MongoDB Atlas, at scale**:
a car learns a real Chennai route by forgetting its own wrong turns, out of 1,026 memories.

---

## The one-liner

> "A car starts with a head full of wrong directions. Every trip it recalls a turn from memory,
> gets corrected, and the memory **forgets the turns that misled it** — so over seven trips it
> teaches itself the real drive from Kodambakkam station to Jains Antariksha. Same 1,026 memories
> with the learning switched off (plain RAG) never get past the first turn."

## What to say it is (and isn't)

- It is **self-improving agent memory**: recall → act → score what helped → forget the noise → better recall.
- It is **not RAG**. RAG retrieves by frozen similarity. Here the *ranking changes* as the agent learns,
  and bad memories are *deleted*. The RAG column in the output is the exact same code with learning off —
  it's the control that proves the lift is the learning, not the embeddings.

---

## Live demo (do this on stage)

```bash
cd routemind
source .venv/bin/activate

# 1. Show the scale + the learning, live on Atlas (~40s)
python run_nav.py --atlas --rounds 8
```

Point at three things as it prints:

1. The header: **"1,026 turn-memories … Atlas Vector Search must find each junction's turn inside all 1,026 vectors."**
2. The **Mnemo column walking forward**: lost @ j2 → j4 → j5 → **ARRIVED**. That's the memory healing itself.
3. The **RAG column frozen** at 2/6, every single trip. Same memories, no learning.

```bash
# 2. Show it on the real map (already rendered; this re-makes the video)
python render_nav.py
open out/learning.mp4          # the green route growing trip by trip
```

If you only have 20 seconds: **just play `docs/learning.mp4`** and read the one-liner.

## If asked "where's the MongoDB?"

- Memories live in Atlas collection `mnemo.memories`; recall is a **`$vectorSearch`** on the `mnemo_vec`
  index (`memory.py` → `AtlasStore.search`), **filtered to the current junction** so it scopes recall
  inside 1,026 vectors.
- The learning writes back to Atlas: `update_stats` persists each memory's usefulness, `delete` forgets
  the ones that keep misleading (`prune`).
- In-process we keep an authoritative usefulness cache because the Atlas **search index is eventually
  consistent** — we don't want to re-rank on a stale index mid-demo. Good detail to mention; judges like it.

---

## Recording the video (for the submission / social)

The map animation is already built by `render_nav.py` → `out/learning.mp4` (+ `.gif`). To also capture a
**screen recording of the live Atlas run** (terminal + map), macOS:

```bash
# Terminal run → asciinema or just QuickTime screen capture (Cmd-Shift-5)
# Full combined clip: record the terminal, then cut to out/learning.mp4

# Optional: a side-by-side (terminal cast + map) with ffmpeg once you have term.mov:
ffmpeg -i term.mov -i out/learning.mp4 -filter_complex \
  "[0:v]scale=-1:680[a];[a][1:v]hstack" -y demo_sidebyside.mp4
```

Suggested 60-second cut: **(0–10s)** one-liner over the station pin · **(10–40s)** the live `--atlas` run,
cursor following the Mnemo column arriving while RAG stays stuck · **(40–60s)** `out/learning.mp4`, the
green route completing, freeze on "ARRIVED at Jains Antariksha".

## The numbers to put on a slide

| | |
|---|---|
| Route | Kodambakkam Railway Station → Jains Antariksha, Chennai (real OSM roads) |
| Memory store | **1,026** vectors on MongoDB Atlas (`$vectorSearch`) |
| Signal vs. noise | 18 correct turns vs. 1,008 wrong/decoy turns |
| RouteMind (learns) | **arrives by trip 7** (6/6 turns) |
| RAG (frozen, same memory) | **never past the 1st turn** (2/6), all 8 trips |
