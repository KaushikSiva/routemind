"""
Recreate the Atlas vector-search index 'mnemo_vec' to match the current embedding dimension
(1024 for Voyage voyage-3.5, 1536 for OpenAI). Run after switching embedding providers.
    python recreate_index.py
"""
import os
import time

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from pymongo import MongoClient
from memory import DIM, EMBED_PROVIDER, EMBED_MODEL

col = MongoClient(os.environ["MONGODB_URI"])["mnemo"]["memories"]
print(f"provider={EMBED_PROVIDER} model={EMBED_MODEL} dim={DIM}")

existing = {ix["name"] for ix in col.list_search_indexes()}
if "mnemo_vec" in existing:
    print("dropping old mnemo_vec…")
    col.drop_search_index("mnemo_vec")
    while "mnemo_vec" in {ix["name"] for ix in col.list_search_indexes()}:
        time.sleep(3)

print(f"creating mnemo_vec at {DIM} dims (cosine)…")
col.create_search_index({
    "name": "mnemo_vec", "type": "vectorSearch",
    "definition": {"fields": [{"type": "vector", "path": "vec", "numDimensions": DIM, "similarity": "cosine"}]},
})
for _ in range(60):
    ix = next((i for i in col.list_search_indexes() if i["name"] == "mnemo_vec"), None)
    status = ix and ix.get("status")
    if status == "READY":
        print("mnemo_vec is READY ✅"); break
    print(f"  …{status}")
    time.sleep(5)
else:
    print("timed out waiting for READY (it may still finish building)")
