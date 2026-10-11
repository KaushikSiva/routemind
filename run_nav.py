"""
RouteMind harness: each round is one drive. The car visits every junction on the true route,
recalls a turn from memory, and is graded + corrected (so all junctions get learned). We track
the FIRST wrong recall each trip — that's where it would have gone off-route (the failure point).

Mnemo (usefulness-weighted recall + forgetting) vs RAG (frozen similarity). Same memory.
"""
import argparse
import json
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from memory import embed, LocalStore, AtlasStore, Memory
from nav_tasks import DECISIONS, junction_doc, make_bank


def run(use_usefulness, rounds, store_factory, bank, bank_vecs, jvecs):
    store = store_factory()
    store.clear()
    for b, v in zip(bank, bank_vecs):
        store.add({**b, "vec": list(v), "uses": 0, "helped": 0, "usefulness": 0.5})
    import time
    if isinstance(store, AtlasStore):
        time.sleep(10)
    mem = Memory(store, alpha=3.0, use_usefulness=use_usefulness)
    history = []
    for r in range(rounds):
        correct_turns, first_fail = 0, None
        for i, d in enumerate(DECISIONS):
            cands = mem.retrieve(jvecs[i], k=1, where={"junction": i})
            chosen = cands[0]["action"] if cands else None
            ok = chosen == d["action"]
            if use_usefulness and cands:
                mem.record(cands, ok)                   # learn: did this remembered turn help?
            if ok:
                correct_turns += 1
            elif first_fail is None:
                first_fail = i                          # where it would have left the route
        if use_usefulness:
            mem.prune(min_uses=1, min_usefulness=0.4)   # forget a turn the moment it misleads once
        reached = first_fail is None
        history.append({"reached": reached, "correct_turns": correct_turns, "first_fail": first_fail})
    return history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--atlas", action="store_true")
    ap.add_argument("--save", default="out/history.json")
    args = ap.parse_args()

    bank = make_bank()
    print(f"{len(DECISIONS)} junctions | {len(bank)} turn-memories "
          f"({sum(b['truth'] for b in bank)} correct / {sum(not b['truth'] for b in bank)} noise)\n")
    bank_vecs = embed([b["document"] for b in bank])
    jvecs = embed([junction_doc(i, d) for i, d in enumerate(DECISIONS)])

    store_factory = LocalStore
    if args.atlas:
        uri = os.environ["MONGODB_URI"]
        store_factory = lambda: AtlasStore(uri)         # noqa: E731

    mnemo = run(True, args.rounds, store_factory, bank, bank_vecs, jvecs)
    rag = run(False, args.rounds, store_factory, bank, bank_vecs, jvecs)

    N = len(DECISIONS)
    print(" round | Mnemo turns right | reached? || RAG turns right | reached?")
    for i, (m, g) in enumerate(zip(mnemo, rag), 1):
        print(f"   {i:2d}  |   {m['correct_turns']}/{N}  ({'ARRIVED' if m['reached'] else 'lost @ j'+str(m['first_fail'])})"
              f"   ||  {g['correct_turns']}/{N}  ({'ARRIVED' if g['reached'] else 'lost @ j'+str(g['first_fail'])})")
    print(f"\n final — Mnemo: {'ARRIVES' if mnemo[-1]['reached'] else 'still lost'} "
          f"({mnemo[-1]['correct_turns']}/{N} turns) | RAG: {'ARRIVES' if rag[-1]['reached'] else 'still lost'} "
          f"({rag[-1]['correct_turns']}/{N} turns)")

    os.makedirs("out", exist_ok=True)
    json.dump({"mnemo": mnemo, "rag": rag, "n": N}, open(args.save, "w"), indent=1)
    print(f" wrote {args.save}")


if __name__ == "__main__":
    main()
