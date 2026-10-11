"""
RouteMind benchmark: a car learning the real drive from Kodambakkam railway station to
Jains Antariksha (Chennai). The route and its turns come from OpenStreetMap (nav/route.json),
so these are actual roads. At each junction the car must recall which way to turn; its memory
holds the correct turn plus NOISE (wrong turns from bad past trips). One wrong recall sends it
off-route, so the trip only "self-drives" when every junction is recalled correctly.
"""
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
DECISIONS = [d for d in json.load(open(os.path.join(HERE, "nav", "decisions.json")))
             if d["type"] != "arrive"]   # drop the final "arrive" — it is not a turn choice
ROUTE = json.load(open(os.path.join(HERE, "nav", "route.json")))["routes"][0]
ACTIONS = ["left", "right", "straight"]

START = (13.0516624, 80.2306892)     # Kodambakkam railway station (lat, lon)
GOAL = (13.0477760, 80.2195109)      # Jains Antariksha


def junction_doc(i, d):
    return f"Junction {i} on {d['on']}: which way to continue toward Jains Antariksha?"


# A pool of real Chennai street names, used to mint DISTRACTOR junctions — memories for
# other junctions all over the city. They are never the answer here; they exist so Atlas
# Vector Search has to find this junction's turns inside a store of thousands of memories.
_STREETS = [
    "Arcot Road", "GN Chetty Road", "Usman Road", "Habibullah Road", "Venkatnarayana Road",
    "Thirumalai Road", "Burkit Road", "North Boag Road", "South Boag Road", "Bazullah Road",
    "Sir Thyagaraya Road", "Pondy Bazaar", "Nungambakkam High Road", "Sterling Road", "College Road",
    "Cathedral Road", "TTK Road", "Dr Radhakrishnan Salai", "Greams Road", "Harrington Road",
    "Poonamallee High Road", "Mount Road", "Anna Salai", "Kodambakkam High Road", "Vadapalani",
    "Ashok Nagar 1st Avenue", "Jafferkhanpet Road", "Lake View Road", "Brindavan Street", "Bharathi Salai",
]


def junction_doc_for(name, i):
    return f"Junction {i} on {name}: which way to continue toward Jains Antariksha?"


def make_bank(correct_per=3, noise_per=8, distractor_junctions=160, distractor_per=6, seed=1):
    """
    The real route: per junction, correct-turn memories + noisy (wrong-turn) memories.
    Plus `distractor_junctions` fake junctions all over Chennai (scale) — so recall has to
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
    print(f"{len(DECISIONS)} junctions, {len(bank)} turn-memories "
          f"({sum(b['truth'] for b in bank)} correct / {sum(not b['truth'] for b in bank)} noise)")
    for i, d in enumerate(DECISIONS):
        print(f"  junction {i}: {d['on']:28s} correct = {d['action']}")
