# Showing RouteMind live in MongoDB Atlas

The "remote URL" for the demo is your **Atlas cluster** itself (cloud.mongodb.com). The data is
already seeded in the learned state. Three screens, ~90 seconds.

**Cluster** `cluster0` · **database** `mnemo` · **collection** `memories` · **index** `mnemo_vec`

Re-seed anytime (leaves Atlas in the learned state and prints what to point at):
```bash
ROUTEMIND_ROUTE=sf python seed_atlas_demo.py --rounds 10
```

---

## Screen 1 — the memory, learned (Collections → mnemo.memories)

Filter and sort in the Data Explorer:
```
Filter:  { "uses": { "$gt": 0 } }
Sort:    { "usefulness": -1 }
```
- **11 documents**, one per junction, each the **correct** turn, `usefulness ≈ 0.9` (`uses=10, helped=10`).
- The collection went **1,081 → 1,061 vectors**: the agent **deleted 20 wrong turns** it kept getting
  misled by. Say: *"it didn't just reweight — it forgot."*

## Screen 2 — the vector index (Atlas Search → mnemo_vec)

- `mnemo_vec`, type **vector**, path `vec`, **1536 dims**, **cosine**, status **READY**.
- 1,061 memories are vector-searchable. This is what recall runs against.

## Screen 3 — the vector search, live (Collections → Aggregation)

Generate the pipeline (full 1536-dim query vector is written to `out/sf/atlas_pipeline.json`):
```bash
ROUTEMIND_ROUTE=sf python atlas_pipeline.py --junction 0
```
In Atlas: **Aggregation → `...` → New Pipeline from Text →** paste the JSON. You'll see:

| on | action | similarity | usefulness | |
|---|---|---|---|---|
| The Embarcadero | **right** | 1.000 | **0.917** | ✓ correct — ranks first |
| The Embarcadero | straight | 1.000 | 0.500 | wrong |
| The Embarcadero | right | 1.000 | 0.500 | |
| … | | 1.000 | 0.500 | |

**The line that wins the hackathon:** every candidate has `similarity = 1.000` — pure vector
similarity (plain RAG) **cannot tell the right turn from the wrong ones**. RouteMind ranks the
correct turn first because it **learned** which memory actually got the car there — and that learned
signal (`usefulness`) lives right here in Atlas.

---

## Optional — change it in front of them

Open a terminal next to the Atlas tab and run the live learning; refresh the collection to watch
`uses` / `usefulness` climb and wrong turns disappear:
```bash
python run_nav.py --atlas --rounds 8     # Shack 15 → Ocean Beach
```

## The pitch, in one breath

> "Memories live in MongoDB Atlas as 1,081 vectors. Vector search alone can't pick the right turn —
> every candidate scores 1.0. RouteMind scores each memory by whether recalling it *helped*, keeps the
> useful ones, and **deletes** the misleading ones — all persisted in Atlas. So the car teaches itself
> the real Shack 15 → Ocean Beach drive in four trips, while plain RAG never leaves the first block."
