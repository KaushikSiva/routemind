"""
Build a RouteMind route from two place names, using only OpenStreetMap:
geocode (Nominatim) -> driving route + turn-by-turn (OSRM) -> nav/<slug>/.

    python build_route.py --slug sf \
        --start "Ferry Building, San Francisco" --goal "Ocean Beach, San Francisco" \
        --start-label "Shack 15" --goal-label "Ocean Beach"

Writes nav/<slug>/route.json (raw OSRM), decisions.json (one per turn) and meta.json
(start/goal coords + labels). Everything downstream reads the route via ROUTEMIND_ROUTE=<slug>.
"""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "RouteMind/1.0 (hackathon demo)"}
_MOD = {"left": "left", "slight left": "left", "sharp left": "left",
        "right": "right", "slight right": "right", "sharp right": "right",
        "straight": "straight", "uturn": "left"}


def _get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))


def geocode(q):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1})
    r = _get(url)
    if not r:
        raise SystemExit(f"could not geocode: {q!r}")
    return float(r[0]["lat"]), float(r[0]["lon"])


def route(start, goal):
    # OSRM public server wants lon,lat
    url = (f"https://router.project-osrm.org/route/v1/driving/"
           f"{start[1]},{start[0]};{goal[1]},{goal[0]}"
           f"?overview=full&geometries=geojson&steps=true")
    r = _get(url)
    if r.get("code") != "Ok":
        raise SystemExit(f"OSRM error: {r.get('code')}")
    return r


def decisions_from(osrm):
    steps = osrm["routes"][0]["legs"][0]["steps"]
    out = []
    for s in steps:
        m = s["maneuver"]
        action = _MOD.get(m.get("modifier", "straight"), "straight")
        out.append({"on": s.get("name") or "unnamed road", "loc": m["location"],
                    "action": action, "type": m["type"]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--goal", required=True)
    ap.add_argument("--start-label", required=True)
    ap.add_argument("--goal-label", required=True)
    ap.add_argument("--city", default="")
    a = ap.parse_args()

    s = geocode(a.start); time.sleep(1)
    g = geocode(a.goal)
    print(f"start {a.start_label}: {s}\ngoal  {a.goal_label}: {g}")
    osrm = route(s, g)
    rt = osrm["routes"][0]
    decs = decisions_from(osrm)
    turns = [d for d in decs if d["type"] != "arrive"]
    print(f"route {rt['distance']/1000:.2f} km, {len(rt['geometry']['coordinates'])} geometry pts, "
          f"{len(turns)} turns")

    d = os.path.join(HERE, "nav", a.slug)
    os.makedirs(d, exist_ok=True)
    json.dump(osrm, open(f"{d}/route.json", "w"))
    json.dump(decs, open(f"{d}/decisions.json", "w"), indent=1)
    json.dump({"start": list(s), "goal": list(g), "start_label": a.start_label,
               "goal_label": a.goal_label, "city": a.city}, open(f"{d}/meta.json", "w"), indent=1)
    print(f"wrote nav/{a.slug}/")


if __name__ == "__main__":
    main()
