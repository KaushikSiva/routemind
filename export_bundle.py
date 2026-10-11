"""
Export a self-contained JSON bundle for the hosted demo page: geometry + decisions +
per-trip RouteMind/RAG histories (with the geometry cut index per trip) for one route.
    ROUTEMIND_ROUTE=sf python export_bundle.py
"""
import json
import os

from nav_tasks import DECISIONS, START, GOAL, START_LABEL, GOAL_LABEL, CITY, ROUTE, ROUTE_JSON, make_bank

HERE = os.path.dirname(os.path.abspath(__file__))
GEOM = ROUTE_JSON["geometry"]["coordinates"]              # [lon, lat]


def nearest(loc):
    return min(range(len(GEOM)), key=lambda i: (GEOM[i][0] - loc[0]) ** 2 + (GEOM[i][1] - loc[1]) ** 2)


def cut(t):
    return len(GEOM) if t["reached"] else nearest(DECISIONS[t["first_fail"]]["loc"]) + 1


def tripify(trips):
    return [{"trip": i + 1, "correct": t["correct_turns"], "reached": t["reached"],
             "first_fail": t["first_fail"], "cut": cut(t)} for i, t in enumerate(trips)]


H = json.load(open(f"{HERE}/out/{ROUTE}/history.json"))
bank = make_bank()
bundle = {
    "route": ROUTE, "start_label": START_LABEL, "goal_label": GOAL_LABEL, "city": CITY,
    "geometry": [[lat, lon] for lon, lat in GEOM],
    "start": list(START), "goal": list(GOAL),
    "decisions": [{"on": d["on"], "loc": [d["loc"][1], d["loc"][0]], "action": d["action"]} for d in DECISIONS],
    "n": len(DECISIONS), "store_size": len(bank),
    "noise": sum(not b["truth"] for b in bank), "distractors": sum(b.get("distractor", False) for b in bank),
    "mnemo": tripify(H["mnemo"]), "rag": tripify(H["rag"]),
}
os.makedirs(f"{HERE}/out", exist_ok=True)
json.dump(bundle, open(f"{HERE}/out/{ROUTE}/bundle.json", "w"))
print(f"wrote out/{ROUTE}/bundle.json — {START_LABEL} -> {GOAL_LABEL}, {len(DECISIONS)} turns, "
      f"{len(bundle['geometry'])} geom pts, mnemo arrives trip "
      f"{next((t['trip'] for t in bundle['mnemo'] if t['reached']), None)}")
