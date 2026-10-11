"""
Raindrop (raindrop.ai) observability for RouteMind — "Sentry for AI agents".

Every junction recall is an AI interaction: the agent recalls a turn from Atlas and acts.
We stream each one to Raindrop so the self-improvement is visible in their dashboard
(ok flips false -> true across trips for RouteMind, stays stuck for RAG).

Best-effort and env-gated: set RAINDROP_WRITE_KEY to enable; with no key it is a silent no-op,
and any network error is swallowed so instrumentation never breaks a run. No extra dependencies.
"""
import json
import os
import urllib.request

ENDPOINT = "https://api.raindrop.ai/v1/events/track"
EMBED_MODEL = "text-embedding-3-small"


class Raindrop:
    def __init__(self, project=None, flush_every=100):
        self.key = os.environ.get("RAINDROP_WRITE_KEY")
        self.project = project or os.environ.get("RAINDROP_PROJECT_ID")
        self.buf = []
        self.flush_every = flush_every
        self.sent = 0
        self.enabled = bool(self.key)

    def _post(self, events):
        if not events:
            return
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        if self.project:
            headers["X-Raindrop-Project-Id"] = self.project
        req = urllib.request.Request(ENDPOINT, data=json.dumps(events).encode(), headers=headers)
        try:
            urllib.request.urlopen(req, timeout=15)
            self.sent += len(events)
        except Exception:
            pass                                        # never let telemetry break the run

    def track(self, event):
        if not self.enabled:
            return
        self.buf.append(event)
        if len(self.buf) >= self.flush_every:
            self._post(self.buf); self.buf = []

    def recall(self, route, city, mode, trip, junction, road, chosen, correct, ok, usefulness, store_size):
        """One junction recall: the agent recalled a turn from Atlas and acted."""
        self.track({
            "user_id": f"routemind-{route}",
            "event": "junction_recall",
            "event_id": f"{route}-{mode}-t{trip}-j{junction}",
            "properties": {
                "route": route, "city": city, "mode": mode, "trip": trip, "junction": junction,
                "road": road, "chosen": chosen, "correct": correct, "ok": ok,
                "usefulness_of_chosen": round(usefulness, 3), "atlas_vectors": store_size,
            },
            "ai_data": {
                "model": EMBED_MODEL,
                "input": f"At junction {junction} on {road}, which way to continue?",
                "output": str(chosen),
                "convo_id": f"{route}-{mode}-trip{trip}",
                "tool_calls": [{
                    "name": "atlas_vector_search",
                    "arguments": {"index": "mnemo_vec", "junction": junction, "k": 1},
                    "result": {"action": chosen, "usefulness": round(usefulness, 3), "correct": ok},
                    "status": "ok" if ok else "wrong_turn",
                    "call_id": f"{route}-{mode}-t{trip}-j{junction}",
                }],
            },
        })

    def trip(self, route, mode, trip, reached, correct_turns, n):
        self.track({
            "user_id": f"routemind-{route}",
            "event": "trip_result",
            "event_id": f"{route}-{mode}-t{trip}-result",
            "properties": {"route": route, "mode": mode, "trip": trip, "reached": reached,
                           "correct_turns": correct_turns, "total_turns": n,
                           "outcome": "ARRIVED" if reached else "lost"},
        })

    def flush(self):
        if self.enabled and self.buf:
            self._post(self.buf); self.buf = []
        return self.sent
