"""
Plot the recursive self-improvement curve: turns recalled correctly per trip, RouteMind
(usefulness-weighted recall + forgetting) vs RAG (same memory, frozen similarity).
    python graph.py            # uses the default route's out/<route>/history.json
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nav_tasks import ROUTE, START_LABEL, GOAL_LABEL, CITY

HERE = os.path.dirname(os.path.abspath(__file__))
H = json.load(open(f"{HERE}/out/{ROUTE}/history.json"))
N = H["n"]
mn = [t["correct_turns"] for t in H["mnemo"]]
rg = [t["correct_turns"] for t in H["rag"]]
x = list(range(1, len(mn) + 1))
arrive = next((i + 1 for i, t in enumerate(H["mnemo"]) if t["reached"]), None)

BG, FG, GRID = "#0e1116", "#e8eaed", "#2a2f36"
MN, RG = "#1fa971", "#e5733b"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
                     "text.color": FG, "axes.labelcolor": FG, "xtick.color": FG, "ytick.color": FG,
                     "font.size": 12})
fig, ax = plt.subplots(figsize=(9, 5))
ax.axhline(N, color=GRID, lw=1, ls="--")
ax.text(len(mn), N + 0.1, "every turn correct = ARRIVES", ha="right", va="bottom", color="#8b9096", fontsize=10)
ax.plot(x, mn, "-o", color=MN, lw=2.6, ms=7, label="RouteMind  (learns + forgets)")
ax.plot(x, rg, "-o", color=RG, lw=2.6, ms=7, label="RAG  (same memory, frozen)")
if arrive:
    ax.axvline(arrive, color=MN, lw=1, alpha=0.4)
    ax.annotate(f"arrives\ntrip {arrive}", (arrive, N), (arrive + 0.3, N - 2.4),
                color=MN, fontsize=11, fontweight="bold",
                arrowprops=dict(color=MN, arrowstyle="->", alpha=0.7))
ax.set_xlim(0.8, len(mn) + 0.4)
ax.set_ylim(0, N + 1.2)
ax.set_xlabel("trip"); ax.set_ylabel(f"turns recalled correctly (of {N})")
ax.set_title(f"RouteMind — self-improving on MongoDB Atlas\n{START_LABEL} → {GOAL_LABEL}, {CITY}  ·  "
             f"{len(mn)} trips over 1,000+ memories", fontsize=13, color=FG)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("bottom", "left"):
    ax.spines[s].set_color(GRID)
ax.grid(axis="y", color=GRID, lw=0.6)
ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=FG, loc="lower right")
fig.tight_layout()
out = f"{HERE}/out/{ROUTE}/curve.png"
fig.savefig(out, dpi=150)
print("wrote", out)
