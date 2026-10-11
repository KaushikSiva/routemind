"""
Produce a paste-ready $vectorSearch aggregation for the MongoDB Atlas UI
(Collections → Aggregation → add stage). Embeds one junction query and writes the full
pipeline (with the 1536-dim queryVector) to out/atlas_pipeline.json.

    ROUTEMIND_ROUTE=sf python atlas_pipeline.py --junction 0
"""
import argparse
import json
import os

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from memory import embed
from nav_tasks import DECISIONS, junction_doc, ROUTE

ap = argparse.ArgumentParser()
ap.add_argument("--junction", type=int, default=0)
args = ap.parse_args()

i = args.junction
q = junction_doc(i, DECISIONS[i])
qvec = embed([q])[0]

# Exactly what RouteMind does: $vectorSearch recalls candidates by similarity across ALL
# vectors in Atlas, then we scope to this junction and rank by the usefulness it LEARNED.
pipeline = [
    {"$vectorSearch": {
        "index": "mnemo_vec", "path": "vec",
        "queryVector": qvec,
        "numCandidates": 200, "limit": 150
    }},
    {"$addFields": {"similarity": {"$meta": "vectorSearchScore"}}},
    {"$match": {"junction": i}},                       # scope recall to this junction
    {"$sort": {"usefulness": -1}},                     # the turn the memory learned ranks first
    {"$project": {"_id": 0, "on": 1, "action": 1, "truth": 1,
                  "uses": 1, "helped": 1, "usefulness": 1, "similarity": 1}}
]

HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{HERE}/out/{ROUTE}", exist_ok=True)
path = f"{HERE}/out/{ROUTE}/atlas_pipeline.json"
json.dump(pipeline, open(path, "w"), indent=1)

print(f"query: {q!r}")
print(f"\nFull pipeline (with 1536-dim queryVector) written to:\n  {path}")
print("\nPaste it in Atlas → Collections (mnemo.memories) → Aggregation → '...' → New Pipeline from Text.")
print("It runs a FILTERED vector search scoped to this junction and returns the top turns with")
print("their live usefulness — the correct turn ranks first *because the memory learned it*.")
print("\n(compact preview — queryVector truncated:)")
preview = json.loads(json.dumps(pipeline))
preview[0]["$vectorSearch"]["queryVector"] = qvec[:3] + ["…(1536 dims)"]
print(json.dumps(preview, indent=1))
