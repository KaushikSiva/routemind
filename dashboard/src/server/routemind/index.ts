import { Module } from 'modelence/server';
import { MongoClient } from 'mongodb';
import { planRoute } from './engine';

// Read-only view of RouteMind's live memory in MongoDB Atlas (the same cluster the Python
// agent writes to). We open our own client to the Atlas URI so the dashboard shows the real
// learned state: which turns the agent kept (high usefulness) and how many it forgot.
let client: MongoClient | null = null;
async function atlasDb() {
  const uri = process.env.ROUTEMIND_MONGODB_URI || process.env.MONGODB_URI;
  if (!uri) throw new Error('ROUTEMIND_MONGODB_URI is not set');
  if (!client) {
    client = new MongoClient(uri);
    await client.connect();
  }
  return client.db('mnemo');
}

export default new Module('routemind', {
  queries: {
    // Build any route from OpenStreetMap and learn it live (Voyage embeddings + self-forgetting recall).
    planRoute: async (args: unknown) => {
      const a = (args ?? {}) as { start?: string; goal?: string };
      const start = (a.start || '').trim();
      const goal = (a.goal || '').trim();
      if (!start || !goal) throw new Error('Enter a start and a destination');
      return planRoute(start, goal);
    },

    // Live snapshot of the learned memory in Atlas.
    getState: async () => {
      const db = await atlasDb();
      const mem = db.collection('memories');
      const [total, used, meta] = await Promise.all([
        mem.countDocuments({}),
        mem.countDocuments({ uses: { $gt: 0 } }),
        db.collection('demo_meta').findOne({ _id: 'sf' as any }),
      ]);
      const learned = await mem
        .find({ uses: { $gt: 0 } })
        .sort({ usefulness: -1 })
        .limit(12)
        .project({ _id: 0, on: 1, action: 1, usefulness: 1, uses: 1, helped: 1, truth: 1, junction: 1 })
        .toArray();
      return {
        total,
        used,
        learned,
        seeded: meta?.seeded ?? null,
        forgotten: meta?.forgotten ?? null,
        startLabel: meta?.start_label ?? 'Shack 15',
        goalLabel: meta?.goal_label ?? 'Ocean Beach',
        updatedAt: meta?.updatedAt ?? null,
        embedding: process.env.VOYAGE_API_KEY ? 'Voyage AI · voyage-3.5 (1024-d)' : 'OpenAI · text-embedding-3-small',
      };
    },

    // ElevenLabs narration of the pitch. Returns base64 mp3 when ELEVENLABS_API_KEY is set;
    // otherwise the client falls back to the browser's speech synthesis.
    narrate: async (args: unknown) => {
      const key = process.env.ELEVENLABS_API_KEY;
      const text = (args as { text?: string })?.text?.slice(0, 1500) || '';
      if (!key || !text) return { audio: null as string | null, voice: 'browser' };
      const voice = process.env.ELEVENLABS_VOICE_ID || '21m00Tcm4TlvDq8ikWAM';
      const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}`, {
        method: 'POST',
        headers: { 'xi-api-key': key, 'Content-Type': 'application/json', Accept: 'audio/mpeg' },
        body: JSON.stringify({ text, model_id: 'eleven_turbo_v2_5' }),
      });
      if (!res.ok) return { audio: null as string | null, voice: 'browser' };
      const buf = Buffer.from(await res.arrayBuffer());
      return { audio: buf.toString('base64'), voice: 'elevenlabs' };
    },
  },
});
