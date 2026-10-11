"""
RouteMind benchmark: a car learning a real drive, turn by turn, from OpenStreetMap.
Pick the route with the ROUTEMIND_ROUTE env var (a folder under nav/):

    nav/chennai  — Kodambakkam railway station -> Jains Antariksha (default)
    nav/sf       — Shack 15 (Ferry Building) -> Ocean Beach, San Francisco

The route and its turns come from OSM (build_route.py). At each junction the car must recall
which way to turn; its memory holds the correct turn plus NOISE (wrong turns from bad past trips,
and decoy turns from junctions all over the city). One wrong recall sends it off-route, so the
trip only "self-drives" when every junction is recalled correctly.
"""
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTE = os.environ.get("ROUTEMIND_ROUTE", "sf")
RDIR = os.path.join(HERE, "nav", ROUTE)

DECISIONS = [d for d in json.load(open(os.path.join(RDIR, "decisions.json")))
             if d["type"] != "arrive"]   # drop the final "arrive" — it is not a turn choice
ROUTE_JSON = json.load(open(os.path.join(RDIR, "route.json")))["routes"][0]
META = json.load(open(os.path.join(RDIR, "meta.json")))
ACTIONS = ["left", "right", "straight"]

START = tuple(META["start"])         # (lat, lon)
GOAL = tuple(META["goal"])
GOAL_LABEL = META["goal_label"]
START_LABEL = META["start_label"]
CITY = META.get("city", "")

# Street-name pools for minting DISTRACTOR junctions (memories for other junctions across the
# city). They are never the answer here; they exist so Atlas Vector Search has to find this
# junction's turns inside a store of thousands. One pool per city keeps the decoys plausible.
_POOLS = {
    "Chennai": [
        "Arcot Road", "GN Chetty Road", "Usman Road", "Habibullah Road", "Venkatnarayana Road",
        "Thirumalai Road", "Burkit Road", "North Boag Road", "South Boag Road", "Bazullah Road",
        "Sir Thyagaraya Road", "Pondy Bazaar", "Nungambakkam High Road", "Sterling Road", "College Road",
        "Cathedral Road", "TTK Road", "Dr Radhakrishnan Salai", "Greams Road", "Harrington Road",
        "Poonamallee High Road", "Mount Road", "Anna Salai", "Kodambakkam High Road", "Vadapalani",
        "Ashok Nagar 1st Avenue", "Jafferkhanpet Road", "Lake View Road", "Brindavan Street", "Bharathi Salai",
    ],
    "San Francisco": [
        "Market Street", "Mission Street", "Van Ness Avenue", "Geary Boulevard", "Fulton Street",
        "Fell Street", "Oak Street", "Divisadero Street", "Masonic Avenue", "Stanyan Street",
        "19th Avenue", "Sunset Boulevard", "Judah Street", "Taraval Street", "Sloat Boulevard",
        "Portola Drive", "Clement Street", "Balboa Street", "Cabrillo Street", "Lincoln Way",
        "Columbus Avenue", "Bay Street", "Lombard Street", "Folsom Street", "Howard Street",
        "Howard Road", "Castro Street", "Church Street", "Dolores Street", "Guerrero Street",
    ],
}
_STREETS = _POOLS.get(CITY, _POOLS["Chennai"])


def junction_doc(i, d):
    return f"Junction {i} on {d['on']}: which way to continue toward {GOAL_LABEL}?"


def junction_doc_for(name, i):
    return f"Junction {i} on {name}: which way to continue toward {GOAL_LABEL}?"


def make_bank(correct_per=3, noise_per=8, distractor_junctions=160, distractor_per=6, seed=1):
    """
    The real route: per junction, correct-turn memories + noisy (wrong-turn) memories.
    Plus `distractor_junctions` fake junctions all over the city (scale) — so recall has to
    pick this junction's turns out of a store of thousands. They carry junction ids >=1000
    and are filtered out by junction-scoped recall, so they only stress the vector search.
    """
    rng = random.Random(seed)
    bank = []
    for i, d in enumerate(DECISIONS):
        correct = d["action"] if d["action"] in ACTIONS else "straight"
        doc = junction_doc(i, d)
        for _ in range(correct_per):
            bank.append({"junction": i, "on": d["on"], "document": doc, "action": correct, "truth": True})
        wrongs = [a for a in ACTIONS if a != correct]
        for _ in range(noise_per):
            bank.append({"junction": i, "on": d["on"], "document": doc, "action": rng.choice(wrongs), "truth": False})
    for j in range(distractor_junctions):
        name = rng.choice(_STREETS)
        jid = 1000 + j
        doc = junction_doc_for(name, jid)
        for _ in range(distractor_per):
            bank.append({"junction": jid, "on": name, "document": doc,
                         "action": rng.choice(ACTIONS), "truth": False, "distractor": True})
    rng.shuffle(bank)
    return bank


if __name__ == "__main__":
    bank = make_bank()
    print(f"[{ROUTE}] {START_LABEL} -> {GOAL_LABEL} ({CITY})")
    print(f"{len(DECISIONS)} junctions, {len(bank)} turn-memories "
          f"({sum(b['truth'] for b in bank)} correct / {sum(not b['truth'] for b in bank)} noise)")
    for i, d in enumerate(DECISIONS):
        print(f"  junction {i}: {d['on']:28s} correct = {d['action']}")
