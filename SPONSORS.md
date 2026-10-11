# Sponsor / partner integrations

RouteMind is built on the MongoDB SFTW hackathon stack and nods to the partners + judges.

| Sponsor / partner | Role | How RouteMind uses it |
|---|---|---|
| **MongoDB Atlas** | Host (required) | Memories are 1,081+ vectors in `mnemo.memories`; recall is `$vectorSearch` on the `mnemo_vec` index; usefulness + forgetting are persisted back to Atlas. The whole self-improving memory lives here. |
| **Voyage AI** | Retrieval partner | *(pending key)* embeddings swap from OpenAI to Voyage (`voyage-3`, 1024-dim) — retrieval powered by Voyage AI, as the challenge calls for. |
| **Raindrop** | Judge (observability) | Every junction recall is streamed to Raindrop (`raindrop.py`) as an AI interaction with a `atlas_vector_search` tool call — the self-improvement is visible in the dashboard (`ok` flips false→true for RouteMind, stays stuck for RAG). Enabled by `RAINDROP_WRITE_KEY`. |

**Theme fit:** MongoDB's brief is agents with *"memory, persistence, and self-evolving systems."*
RouteMind is exactly that — a memory that self-evolves by forgetting its own wrong turns.

## Enabling the integrations

```bash
# .env
MONGODB_URI=...            # required
OPENAI_API_KEY=...         # embeddings (until Voyage is wired)
RAINDROP_WRITE_KEY=...     # optional — turns on Raindrop streaming in run_nav.py
VOYAGE_API_KEY=...         # optional — switches embeddings to Voyage AI (coming)
```

Run `python run_nav.py --atlas` and, if `RAINDROP_WRITE_KEY` is set, recalls stream to
raindrop.ai automatically (best-effort; a missing key is a silent no-op).
