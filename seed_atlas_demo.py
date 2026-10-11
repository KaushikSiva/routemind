"""
Leave MongoDB Atlas in a DEMO-READY, learned state for showing in the Atlas console.
Runs ONLY the RouteMind learning pass (no RAG after), so the collection keeps the memory
the agent actually learned: recalled-and-helpful turns climb in usefulness, recalled-and-
misleading turns are pruned (deleted). Then prints exactly what to point at in Atlas.

    ROUTEMIND_ROUTE=sf python seed_atlas_demo.py --rounds 10
"""
import argparse
import os
import time

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from memory import embed, AtlasStore, Memory
from nav_tasks import DECISIONS, junction_doc, make_bank, START_LABEL, GOAL_LABEL, ROUTE

ap = argparse.ArgumentParser()
ap.add_argument("--rounds", type=int, default=10)
args = ap.parse_args()

uri = os.environ["MONGODB_URI"]
store = AtlasStore(uri)
store.clear()
bank = make_bank()
bank_vecs = embed([b["document"] for b in bank])
for b, v in zip(bank, bank_vecs):
    store.add({**b, "vec": list(v), "uses": 0, "helped": 0, "usefulness": 0.5})
seeded = len(bank)
print(f"[{ROUTE}] seeded {seeded:,} vectors into mnemo.memories — waiting for the vector index…")
time.sleep(10)

jvecs = embed([junction_doc(i, d) for i, d in enumerate(DECISIONS)])
mem = Memory(store, alpha=3.0, use_usefulness=True)
for r in range(args.rounds):
    for i, d in enumerate(DECISIONS):
        cands = mem.retrieve(jvecs[i], k=1, where={"junction": i})
        if cands:
            mem.record(cands, cands[0]["action"] == d["action"])
    mem.prune(min_uses=1, min_usefulness=0.4)

col = store.col
remaining = col.count_documents({})
touched = list(col.find({"uses": {"$gt": 0}}).sort("usefulness", -1))

import datetime
store.c["mnemo"]["demo_meta"].replace_one({"_id": ROUTE}, {   # headline numbers for the dashboard
    "_id": ROUTE, "route": ROUTE, "start_label": START_LABEL, "goal_label": GOAL_LABEL,
    "n_junctions": len(DECISIONS), "seeded": seeded, "remaining": remaining,
    "forgotten": seeded - remaining, "used": len(touched),
    "updatedAt": datetime.datetime.utcnow().isoformat() + "Z",
}, upsert=True)
print(f"\n✅ Atlas now holds the LEARNED memory for: {START_LABEL} → {GOAL_LABEL}")
print(f"   vectors: {seeded:,} seeded  →  {remaining:,} remaining  ({seeded - remaining} wrong turns FORGOTTEN / deleted)")
print(f"   memories the agent actually used (uses>0): {len(touched)}")
print("\n   top learned turns (sorted by usefulness):")
for d in touched[:12]:
    tag = "correct ✓" if d.get("truth") else "WRONG (should be gone)"
    print(f"     j{d.get('junction')} {d.get('on'):24s} {d.get('action'):8s} "
          f"uses={d.get('uses')} helped={d.get('helped')} usefulness={round(d.get('usefulness',0),3)}  {tag}")

print("\n──────── SHOW THIS IN MONGODB ATLAS (cloud.mongodb.com) ────────")
print(" cluster: cluster0  ·  database: mnemo  ·  collection: memories")
print(" 1) Collections → mnemo.memories → Filter:  {\"uses\": {\"$gt\": 0}}   Sort:  {\"usefulness\": -1}")
print("    → the turns it learned sit on top (high usefulness); the misleading ones are gone.")
print(" 2) Atlas Search → index  mnemo_vec  (vector, path 'vec', 1536 dims, cosine) → status READY")
print(" 3) Collections → Aggregation → add stage $vectorSearch (pipeline printed by: python atlas_pipeline.py)")
