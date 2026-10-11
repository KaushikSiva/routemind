// RouteMind engine, server side: geocode + route from OpenStreetMap, embed with Voyage AI
// (via MongoDB's hosted endpoint), and run the usefulness-weighted, self-forgetting recall
// in-process so the deployed app can build and "drive" any route the visitor types.

const ACTIONS = ['left', 'right', 'straight'] as const;
const STREETS = [
  'Market Street', 'Mission Street', 'Van Ness Avenue', 'Geary Boulevard', 'Fulton Street',
  'Fell Street', 'Oak Street', 'Divisadero Street', 'Masonic Avenue', 'Stanyan Street',
  '19th Avenue', 'Sunset Boulevard', 'Judah Street', 'Taraval Street', 'Sloat Boulevard',
  'Portola Drive', 'Clement Street', 'Balboa Street', 'Cabrillo Street', 'Lincoln Way',
  'Columbus Avenue', 'Bay Street', 'Lombard Street', 'Folsom Street', 'Howard Street',
  'Castro Street', 'Church Street', 'Dolores Street', 'Guerrero Street', 'Arguello Boulevard',
];
const MOD: Record<string, string> = {
  left: 'left', 'slight left': 'left', 'sharp left': 'left',
  right: 'right', 'slight right': 'right', 'sharp right': 'right',
  straight: 'straight', uturn: 'left',
};

export type Decision = { on: string; loc: [number, number]; action: string; type: string };
export type Trip = { trip: number; correct: number; reached: boolean; first_fail: number | null };

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function cosine(a: number[], b: number[]) {
  let d = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) { d += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  return d / (Math.sqrt(na) * Math.sqrt(nb) + 1e-9);
}

export async function geocode(q: string): Promise<[number, number]> {
  const url = 'https://nominatim.openstreetmap.org/search?' +
    new URLSearchParams({ q, format: 'json', limit: '1' });
  const r = await fetch(url, { headers: { 'User-Agent': 'RouteMind/1.0 (hackathon)' } });
  const j = (await r.json()) as Array<{ lat: string; lon: string }>;
  if (!j.length) throw new Error(`could not find "${q}"`);
  return [parseFloat(j[0].lat), parseFloat(j[0].lon)];
}

export async function routeOSRM(s: [number, number], g: [number, number]) {
  const url = `https://router.project-osrm.org/route/v1/driving/${s[1]},${s[0]};${g[1]},${g[0]}` +
    `?overview=full&geometries=geojson&steps=true`;
  const j = (await fetch(url).then((x) => x.json())) as any;
  if (j.code !== 'Ok') throw new Error('no route found between those points');
  const rt = j.routes[0];
  const geometry: [number, number][] = rt.geometry.coordinates.map((c: number[]) => [c[1], c[0]]);
  const steps = rt.legs[0].steps as any[];
  const decisions: Decision[] = steps.map((st) => ({
    on: st.name || 'unnamed road',
    loc: st.maneuver.location as [number, number], // [lon, lat]
    action: MOD[st.maneuver.modifier ?? 'straight'] ?? 'straight',
    type: st.maneuver.type,
  }));
  return { geometry, decisions, distance: rt.distance as number };
}

const jdoc = (i: number, on: string, goal: string) =>
  `Junction ${i} on ${on}: which way to continue toward ${goal}?`;

export async function voyageEmbed(texts: string[]): Promise<number[][]> {
  const key = process.env.VOYAGE_API_KEY;
  const endpoint = (process.env.VOYAGE_ENDPOINT || 'https://ai.mongodb.com').replace(/\/$/, '') + '/v1/embeddings';
  const model = process.env.VOYAGE_MODEL || 'voyage-3.5';
  if (!key) throw new Error('VOYAGE_API_KEY not set');
  const out: number[][] = [];
  for (let i = 0; i < texts.length; i += 128) {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, input: texts.slice(i, i + 128) }),
    });
    if (!res.ok) throw new Error(`Voyage embeddings failed (${res.status})`);
    const j = (await res.json()) as { data: Array<{ index: number; embedding: number[] }> };
    j.data.sort((a, b) => a.index - b.index).forEach((d) => out.push(d.embedding));
  }
  return out;
}

type Mem = { junction: number; on: string; document: string; action: string; truth: boolean;
  distractor?: boolean; vec: number[]; uses: number; helped: number; usefulness: number };

function makeBank(decisions: Decision[], goal: string, vmap: Map<string, number[]>): Mem[] {
  const rng = mulberry32(1);
  const pick = <T>(arr: readonly T[]) => arr[Math.floor(rng() * arr.length)];
  const bank: Mem[] = [];
  const base = (junction: number, on: string, doc: string, action: string, truth: boolean, distractor = false) =>
    ({ junction, on, document: doc, action, truth, distractor, vec: vmap.get(doc)!, uses: 0, helped: 0, usefulness: 0.5 });
  decisions.forEach((d, i) => {
    const correct = ACTIONS.includes(d.action as any) ? d.action : 'straight';
    const doc = jdoc(i, d.on, goal);
    for (let k = 0; k < 3; k++) bank.push(base(i, d.on, doc, correct, true));
    const wrongs = ACTIONS.filter((a) => a !== correct);
    for (let k = 0; k < 8; k++) bank.push(base(i, d.on, doc, pick(wrongs), false));
  });
  for (let j = 0; j < 160; j++) {
    const name = pick(STREETS); const jid = 1000 + j; const doc = jdoc(jid, name, goal);
    for (let k = 0; k < 6; k++) bank.push(base(jid, name, doc, pick(ACTIONS), false, true));
  }
  return bank;
}

function runLearning(decisions: Decision[], jvecs: number[][], bank0: Mem[], useUsefulness: boolean, rounds: number): { trips: Trip[]; remaining: number } {
  const alpha = 3;
  let bank = bank0.map((m) => ({ ...m }));
  const trips: Trip[] = [];
  for (let r = 0; r < rounds; r++) {
    let correct = 0; let firstFail: number | null = null;
    decisions.forEach((d, i) => {
      const cands = bank.filter((m) => m.junction === i);
      let best: Mem | null = null; let bestScore = -1;
      for (const m of cands) {
        const sim = cosine(jvecs[i], m.vec);
        const score = useUsefulness ? sim * (1 + alpha * m.usefulness) : sim;
        if (score > bestScore) { bestScore = score; best = m; }
      }
      const ok = !!best && best.action === d.action;
      if (useUsefulness && best) {
        best.uses++; if (ok) best.helped++;
        best.usefulness = (best.helped + 1) / (best.uses + 2);
      }
      if (ok) correct++; else if (firstFail === null) firstFail = i;
    });
    if (useUsefulness) bank = bank.filter((m) => !(m.uses >= 1 && m.usefulness < 0.4));
    trips.push({ trip: r + 1, correct, reached: firstFail === null, first_fail: firstFail });
  }
  return { trips, remaining: bank.length };
}

export async function planRoute(startQ: string, goalQ: string, rounds = 14) {
  const [s, g] = await Promise.all([geocode(startQ), geocode(goalQ)]);
  const { geometry, decisions: all } = await routeOSRM(s, g);
  const turns = all.filter((d) => d.type !== 'arrive');
  if (turns.length < 2) throw new Error('that route is too short, pick points further apart');

  const goalLabel = goalQ.split(',')[0].trim().slice(0, 28);
  const startLabel = startQ.split(',')[0].trim().slice(0, 28);
  const jtexts = turns.map((d, i) => jdoc(i, d.on, goalLabel));

  // embed every distinct junction text once (real-route junctions + decoys), via Voyage
  const rng = mulberry32(1);
  const distractDocs = new Set<string>();
  for (let j = 0; j < 160; j++) distractDocs.add(jdoc(1000 + j, STREETS[Math.floor(rng() * STREETS.length)], goalLabel));
  const uniq = Array.from(new Set<string>([...jtexts, ...distractDocs]));
  const vecs = await voyageEmbed(uniq);
  const vmap = new Map<string, number[]>(); uniq.forEach((t, i) => vmap.set(t, vecs[i]));

  const bank = makeBank(turns, goalLabel, vmap);
  const jvecs = jtexts.map((t) => vmap.get(t)!);
  const mnemo = runLearning(turns, jvecs, bank, true, rounds);
  const rag = runLearning(turns, jvecs, bank, false, rounds);
  const forgotten = bank.length - mnemo.remaining;

  const nearest = (loc: [number, number]) => {
    let bi = 0, bd = Infinity;
    geometry.forEach((p, i) => { const dd = (p[1] - loc[0]) ** 2 + (p[0] - loc[1]) ** 2; if (dd < bd) { bd = dd; bi = i; } });
    return bi;
  };
  const withCut = (t: Trip) => ({
    ...t, cut: t.reached ? geometry.length : nearest(turns[t.first_fail!].loc) + 1,
    lost: t.first_fail,
  });

  return {
    startLabel, goalLabel,
    geometry, start: s, goal: g,
    decisions: turns.map((d) => ({ on: d.on, loc: [d.loc[1], d.loc[0]] as [number, number], action: d.action })),
    n: turns.length, storeSize: bank.length, forgotten,
    noise: bank.filter((b) => !b.truth).length,
    distractors: bank.filter((b) => b.distractor).length,
    mnemo: mnemo.trips.map(withCut), rag: rag.trips.map(withCut),
    embedding: 'Voyage AI · voyage-3.5 (1024-d)',
  };
}
