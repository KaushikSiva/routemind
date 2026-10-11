import { useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { modelenceQuery } from '@modelence/react-query';
import type * as LT from 'leaflet';
import 'leaflet/dist/leaflet.css';
import Pitch from './Pitch';

const SPONSORS = [
  { name: 'MongoDB Atlas', url: 'https://cloud.mongodb.com/v2/6acbd27f4122ab4be33b8a0d#/clusters', tag: 'Vector Search' },
  { name: 'Voyage AI', url: 'https://www.voyageai.com', tag: 'embeddings' },
  { name: 'Raindrop', url: 'https://app.raindrop.ai/events?org=9cb3abaf', tag: 'observability' },
  { name: 'Modelence', url: 'https://cloud.modelence.com/environments/6acc0f11dfdb1813453a5b71/builds', tag: 'this app' },
  { name: 'ElevenLabs', url: 'https://elevenlabs.io', tag: 'narration' },
  { name: 'AWS', url: 'https://aws.amazon.com', tag: '' },
  { name: 'Cerebral Valley', url: 'https://cerebralvalley.ai', tag: 'host' },
];
const EXAMPLES: [string, string][] = [
  ['Ferry Building, San Francisco', 'Ocean Beach, San Francisco'],
  ['Golden Gate Bridge', 'Oracle Park, San Francisco'],
  ['Painted Ladies, San Francisco', 'Twin Peaks, San Francisco'],
];
const NARRATION =
  `RouteMind is self-improving agent memory on MongoDB Atlas. A car starts with a head full of wrong ` +
  `directions buried in over a thousand vectors. Every trip it recalls a turn, gets corrected, and ` +
  `forgets the turns that mislead it, so in a handful of trips it teaches itself the real route. The ` +
  `same memory frozen, plain retrieval, never leaves the first block. Vectors are from Voyage AI, ` +
  `recall is Atlas vector search, and the self-improvement is the point.`;

type Trip = { trip: number; correct: number; reached: boolean; first_fail: number | null; cut: number; lost: number | null };
type RouteData = {
  startLabel: string; goalLabel: string; geometry: [number, number][]; start: [number, number]; goal: [number, number];
  decisions: { on: string; loc: [number, number]; action: string }[]; n: number; storeSize: number;
  noise: number; distractors: number; forgotten: number; mnemo: Trip[]; rag: Trip[]; embedding: string;
};

function useCountUp(target: number, ms = 900) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let raf = 0; const t0 = performance.now(); const start = v;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / ms);
      setV(Math.round(start + (target - start) * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);
  return v;
}

export default function HomePage() {
  const qc = useQueryClient();
  const [startQ, setStartQ] = useState(EXAMPLES[0][0]);
  const [goalQ, setGoalQ] = useState(EXAMPLES[0][1]);
  const [route, setRoute] = useState<RouteData | null>(null);
  const [status, setStatus] = useState<{ text: string; cls: string }>({ text: 'Build a route to begin', cls: 'idle' });
  const [learn, setLearn] = useState(true);
  const [busy, setBusy] = useState(false);
  const [curveN, setCurveN] = useState(0);
  const [tripInfo, setTripInfo] = useState('');
  const [narrating, setNarrating] = useState(false);
  const [tab, setTab] = useState<'drive' | 'pitch'>('drive');

  const mapEl = useRef<HTMLDivElement | null>(null);
  const Lref = useRef<typeof LT | null>(null);
  const lay = useRef<{ map?: LT.Map; full?: LT.Polyline; drive?: LT.Polyline; s?: LT.CircleMarker; g?: LT.CircleMarker; lost?: LT.CircleMarker }>({});
  const timers = useRef<number[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // init Leaflet once (client-only), standard OpenStreetMap tiles
  useEffect(() => {
    let alive = true;
    (async () => {
      const mod = await import('leaflet');
      const L = ((mod as any).default ?? mod) as typeof LT;
      if (!alive || !mapEl.current || lay.current.map) return;
      Lref.current = L;
      const map = L.map(mapEl.current, { zoomControl: true }).setView([37.773, -122.46], 12);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        subdomains: 'abc', maxZoom: 19, attribution: '© OpenStreetMap contributors',
      }).addTo(map);
      lay.current.map = map;
      setTimeout(() => map.invalidateSize(), 150);
      build(EXAMPLES[0][0], EXAMPLES[0][1]); // auto-build the default route
    })();
    return () => { alive = false; timers.current.forEach(clearTimeout); lay.current.map?.remove(); lay.current = {}; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // the map has zero size while the Drive tab is hidden; fix it when the tab returns
  useEffect(() => { if (tab === 'drive') setTimeout(() => lay.current.map?.invalidateSize(), 60); }, [tab]);

  function drawRoute(rd: RouteData) {
    const L = Lref.current; const map = lay.current.map; if (!L || !map) return;
    [lay.current.full, lay.current.drive, lay.current.s, lay.current.g, lay.current.lost].forEach((l) => l?.remove());
    lay.current.lost = undefined;
    lay.current.full = L.polyline(rd.geometry, { color: '#9aa4b2', weight: 4, opacity: 0.7, dashArray: '4 8' }).addTo(map);
    lay.current.drive = L.polyline([], { color: '#15a46e', weight: 6, lineCap: 'round', lineJoin: 'round' }).addTo(map);
    lay.current.s = L.circleMarker(rd.start, { radius: 8, color: '#fff', weight: 2, fillColor: '#2563eb', fillOpacity: 1 }).addTo(map).bindTooltip(rd.startLabel);
    lay.current.g = L.circleMarker(rd.goal, { radius: 8, color: '#fff', weight: 2, fillColor: '#6b7280', fillOpacity: 1 }).addTo(map).bindTooltip(rd.goalLabel);
    map.fitBounds(rd.geometry as any, { padding: [30, 30] });
  }

  async function build(sq = startQ, gq = goalQ) {
    if (busy) return;
    timers.current.forEach(clearTimeout);
    setBusy(true); setCurveN(0); setTripInfo(''); setRoute(null);
    setStatus({ text: 'Building route from OpenStreetMap…', cls: 'work' });
    try {
      const rd = await qc.fetchQuery(modelenceQuery<RouteData>('routemind.planRoute', { start: sq, goal: gq }));
      setRoute(rd); drawRoute(rd);
      setStatus({ text: `${rd.n} turns · ${rd.storeSize.toLocaleString()} vectors · press Drive`, cls: 'idle' });
    } catch (e: any) {
      setStatus({ text: e?.message || 'Could not build that route', cls: 'lost' });
    } finally { setBusy(false); }
  }

  function drive() {
    const rd = route; const L = Lref.current; if (!rd || !L || busy) return;
    timers.current.forEach(clearTimeout); timers.current = [];
    const trips = learn ? rd.mnemo : rd.rag; const col = learn ? '#15a46e' : '#e4661f';
    lay.current.drive?.setLatLngs([]).setStyle({ color: col });
    lay.current.lost?.remove(); lay.current.lost = undefined;
    lay.current.g?.setStyle({ fillColor: '#6b7280' });
    setCurveN(0);
    let idx = 0;
    const runTrip = () => {
      if (idx >= trips.length) return;
      const t = trips[idx]; const t0 = performance.now();
      const step = (now: number) => {
        const p = Math.min(1, (now - t0) / 520);
        const k = Math.max(2, Math.round(t.cut * p));
        lay.current.drive?.setLatLngs(rd.geometry.slice(0, k) as any);
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
      lay.current.lost?.remove(); lay.current.lost = undefined;
      if (!t.reached && t.lost != null && lay.current.map) {
        lay.current.lost = L.circleMarker(rd.decisions[t.lost].loc, { radius: 10, color: '#fff', weight: 2, fillColor: '#e4661f', fillOpacity: 1 })
          .addTo(lay.current.map).bindTooltip(`lost: ${rd.decisions[t.lost].on}`);
      }
      lay.current.g?.setStyle({ fillColor: t.reached ? '#15a46e' : '#6b7280' });
      setStatus({ text: t.reached ? `ARRIVED at ${rd.goalLabel}` : `LOST at ${rd.decisions[t.lost ?? 0].on}`, cls: t.reached ? 'ok' : 'lost' });
      setTripInfo(`Trip ${t.trip} · ${t.correct}/${rd.n} turns`);
      setCurveN(idx + 1);
      idx += 1;
      timers.current.push(window.setTimeout(runTrip, 850));
    };
    timers.current.push(window.setTimeout(runTrip, 150));
  }

  async function narrate() {
    if (narrating) { audioRef.current?.pause(); window.speechSynthesis?.cancel(); setNarrating(false); return; }
    setNarrating(true);
    try {
      const res = await qc.fetchQuery(modelenceQuery<{ audio: string | null; voice: string }>('routemind.narrate', { text: NARRATION }));
      if (res?.audio) { const a = new Audio('data:audio/mpeg;base64,' + res.audio); audioRef.current = a; a.onended = () => setNarrating(false); await a.play(); return; }
    } catch { /* fall through */ }
    const u = new SpeechSynthesisUtterance(NARRATION); u.rate = 1.02; u.onend = () => setNarrating(false); window.speechSynthesis?.speak(u);
  }

  const vectors = useCountUp(route?.storeSize ?? 0);
  const forgotten = useCountUp(route?.forgotten ?? 0);
  const arrives = route ? (route.mnemo.find((t) => t.reached)?.trip ?? null) : null;

  const curve = useMemo(() => {
    const w = 300, h = 120, pad = 12; const arr = (learn ? route?.mnemo : route?.rag) ?? [];
    const n = Math.max(2, arr.length); const max = Math.max(1, route?.n ?? 1);
    return arr.slice(0, curveN).map((t, i) => {
      const x = pad + (i / (n - 1)) * (w - 2 * pad);
      const y = h - pad - (t.correct / max) * (h - 2 * pad);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  }, [curveN, learn, route]);

  return (
    <div className="rm-root">
      <style>{CSS}</style>

      <div className="rm-sponsors">
        <span className="rm-built">BUILT ON</span>
        {SPONSORS.map((s) => (
          <a key={s.name} href={s.url} target="_blank" rel="noreferrer" className="rm-chip">{s.name}{s.tag && <em> · {s.tag}</em>}</a>
        ))}
      </div>

      <header className="rm-head">
        <div>
          <h1>🚗 RouteMind</h1>
          <p>Type any start and destination. It builds the real route and <b>teaches itself the way by forgetting its own wrong turns</b>, on MongoDB Atlas.</p>
        </div>
        <div className="rm-right">
          <div className="rm-tabs">
            <button className={tab === 'drive' ? 'on' : ''} onClick={() => setTab('drive')}>Drive</button>
            <button className={tab === 'pitch' ? 'on' : ''} onClick={() => setTab('pitch')}>Pitch</button>
          </div>
          <button className={'rm-narrate' + (narrating ? ' on' : '')} onClick={narrate}>{narrating ? '◼ Stop' : '▶ Narrate'} <span>ElevenLabs</span></button>
        </div>
      </header>

      <div hidden={tab !== 'drive'}>
      <main className="rm-grid">
        <section className="rm-card rm-map">
          <div className="rm-inputs">
            <input value={startQ} onChange={(e) => setStartQ(e.target.value)} placeholder="Start" spellCheck={false} />
            <span className="rm-arrow">→</span>
            <input value={goalQ} onChange={(e) => setGoalQ(e.target.value)} placeholder="Destination" spellCheck={false} />
            <button className="rm-build" onClick={() => build()} disabled={busy}>{busy ? 'Building…' : 'Build route'}</button>
          </div>
          <div className="rm-chips">
            {EXAMPLES.map(([s, g]) => (
              <button key={s} className="rm-ex" onClick={() => { setStartQ(s); setGoalQ(g); build(s, g); }} disabled={busy}>
                {s.split(',')[0]} → {g.split(',')[0]}
              </button>
            ))}
          </div>
          <div ref={mapEl} className="rm-leaflet" />
          <div className="rm-ctrls">
            <div className="rm-statusline">
              <span className={'rm-dot ' + status.cls} />
              <b className={status.cls}>{status.text}</b>
              <span className="rm-trip">{tripInfo}</span>
            </div>
            <div className="rm-actions">
              <label className="rm-toggle"><input type="checkbox" checked={learn} onChange={(e) => setLearn(e.target.checked)} />{learn ? 'RouteMind' : 'RAG (frozen)'}</label>
              <button className="rm-drive" onClick={drive} disabled={!route || busy}>▶ Drive</button>
            </div>
          </div>
        </section>

        <section className="rm-side">
          <div className="rm-stats">
            <div className="rm-stat"><b className="atlas">{vectors.toLocaleString()}</b><span>vectors searched</span></div>
            <div className="rm-stat"><b className="rg">{forgotten.toLocaleString()}</b><span>wrong turns forgotten</span></div>
            <div className="rm-stat"><b className="mn">{arrives ? `trip ${arrives}` : '—'}</b><span>RouteMind arrives</span></div>
            <div className="rm-stat small"><b>{route?.embedding ?? 'Voyage AI'}</b><span>embeddings</span></div>
          </div>
          <div className="rm-card rm-curve">
            <div className="rm-curve-head">Self-improvement <span>turns correct / trip</span></div>
            <svg viewBox="0 0 300 120" className="rm-curvesvg" preserveAspectRatio="none">
              <polyline points={curve} className={'rm-cline ' + (learn ? 'mn' : 'rg')} />
            </svg>
            <div className="rm-curve-foot"><span className="mn">RouteMind arrives</span><span className="rg">RAG stays lost</span></div>
          </div>
          <div className="rm-card rm-how">
            <div className="rm-how-head">How it works</div>
            <ol>
              <li>Recall a turn from <b>Atlas Vector Search</b> ({route?.storeSize.toLocaleString() ?? '1,000+'} vectors, Voyage embeddings).</li>
              <li>Drive it, then score whether that memory <b>helped</b>.</li>
              <li>Keep the useful turns, <b>forget</b> the misleading ones.</li>
              <li>Next trip, recall is better. Repeat until it arrives.</li>
            </ol>
          </div>
        </section>
      </main>

      <footer className="rm-foot">
        <span>Recall by MongoDB Atlas $vectorSearch · embeddings by Voyage AI · routes from OpenStreetMap</span>
        <span>{route ? `${route.startLabel} → ${route.goalLabel}` : ''}</span>
      </footer>
      </div>

      <div hidden={tab !== 'pitch'}><Pitch /></div>
    </div>
  );
}

const CSS = `
.rm-root{--bg:#0b0e14;--panel:#141a23;--line:#232c39;--fg:#eaeef4;--mut:#8b95a5;--mn:#15a46e;--rg:#e4661f;--blue:#2563eb;--atlas:#00c767;
  min-height:100vh;background:var(--bg);color:var(--fg);font-family:Inter,system-ui,sans-serif;padding:14px 22px 26px}
.rm-root *{box-sizing:border-box}
.rm-sponsors{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding-bottom:12px;border-bottom:1px solid var(--line)}
.rm-built{font-size:11px;letter-spacing:2px;color:var(--mut);font-weight:700}
.rm-chip{font-size:12.5px;color:var(--fg);text-decoration:none;background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:5px 11px;transition:.2s;white-space:nowrap}
.rm-chip:hover{border-color:var(--atlas)} .rm-chip em{color:var(--mut);font-style:normal}
.rm-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin:18px 0}
.rm-head h1{font-family:'Space Grotesk',Inter,sans-serif;font-size:30px;margin:0}
.rm-head p{margin:5px 0 0;color:var(--mut);max-width:680px;line-height:1.5}
.rm-right{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.rm-tabs{display:flex;background:#0c1017;border:1px solid var(--line);border-radius:10px;padding:3px}
.rm-tabs button{font:inherit;font-weight:600;font-size:13px;color:var(--mut);background:transparent;border:0;border-radius:8px;padding:8px 16px;cursor:pointer}
.rm-tabs button.on{background:var(--panel);color:var(--fg)}
.rm-narrate{font:inherit;font-weight:600;color:#06240f;background:var(--atlas);border:0;border-radius:10px;padding:11px 16px;cursor:pointer;display:flex;align-items:center;gap:8px}
.rm-narrate span{font-size:11px;opacity:.75;font-weight:700} .rm-narrate.on{background:var(--rg);color:#fff}
.rm-grid{display:grid;grid-template-columns:1.6fr 1fr;gap:16px}@media(max-width:920px){.rm-grid{grid-template-columns:1fr}}
.rm-card{background:var(--panel);border:1px solid var(--line);border-radius:14px}
.rm-map{padding:14px}
.rm-inputs{display:flex;gap:8px;align-items:center}
.rm-inputs input{flex:1;min-width:0;font:inherit;color:var(--fg);background:#0c1017;border:1px solid var(--line);border-radius:9px;padding:10px 12px}
.rm-inputs input:focus{outline:none;border-color:var(--atlas)}
.rm-arrow{color:var(--mut)}
.rm-build{font:inherit;font-weight:600;color:#06240f;background:var(--atlas);border:0;border-radius:9px;padding:10px 16px;cursor:pointer;white-space:nowrap}
.rm-build:disabled{opacity:.6;cursor:default}
.rm-chips{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
.rm-ex{font:inherit;font-size:12px;color:var(--mut);background:#0c1017;border:1px solid var(--line);border-radius:20px;padding:5px 10px;cursor:pointer}
.rm-ex:hover{border-color:var(--atlas);color:var(--fg)}
.rm-leaflet{height:420px;border-radius:10px;overflow:hidden;background:#0c1017}
.leaflet-container{font-family:Inter}
.rm-ctrls{display:flex;justify-content:space-between;align-items:center;margin-top:12px;gap:12px;flex-wrap:wrap}
.rm-statusline{display:flex;align-items:center;gap:10px;font-family:'Space Grotesk',sans-serif;min-width:0}
.rm-statusline b{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rm-statusline b.ok{color:var(--mn)} .rm-statusline b.lost{color:var(--rg)} .rm-statusline b.work{color:var(--blue)}
.rm-trip{color:var(--mut);font-size:13px;font-family:Inter}
.rm-dot{width:10px;height:10px;border-radius:50%;background:var(--mut);flex:none}
.rm-dot.ok{background:var(--mn);box-shadow:0 0 10px var(--mn)} .rm-dot.lost{background:var(--rg);box-shadow:0 0 10px var(--rg)} .rm-dot.work{background:var(--blue)} .rm-dot.idle{background:var(--mut)}
.rm-actions{display:flex;align-items:center;gap:12px}
.rm-toggle{display:flex;align-items:center;gap:7px;color:var(--mut);font-size:13px;cursor:pointer}
.rm-drive{font:inherit;font-weight:700;color:#fff;background:var(--mn);border:0;border-radius:9px;padding:10px 20px;cursor:pointer}
.rm-drive:disabled{opacity:.5;cursor:default}
.rm-side{display:flex;flex-direction:column;gap:16px}
.rm-stats{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.rm-stat{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px;animation:pop .5s both}
@keyframes pop{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.rm-stat b{font-family:'Space Grotesk',sans-serif;font-size:24px;display:block} .rm-stat.small b{font-size:13px}
.rm-stat span{color:var(--mut);font-size:12px}
.rm-stat b.atlas{color:var(--atlas)} .rm-stat b.rg{color:var(--rg)} .rm-stat b.mn{color:var(--mn)}
.rm-curve{padding:14px}
.rm-curve-head{display:flex;justify-content:space-between;font-family:'Space Grotesk',sans-serif;font-size:14px;margin-bottom:6px}
.rm-curve-head span{color:var(--mut);font-size:12px;font-family:Inter}
.rm-curvesvg{width:100%;height:120px;background:#0c1017;border-radius:10px}
.rm-cline{fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.rm-cline.mn{stroke:var(--mn)} .rm-cline.rg{stroke:var(--rg)}
.rm-curve-foot{display:flex;justify-content:space-between;font-size:12px;margin-top:6px}
.rm-curve-foot .mn{color:var(--mn)} .rm-curve-foot .rg{color:var(--rg)}
.rm-how{padding:14px;flex:1}
.rm-how-head{font-family:'Space Grotesk',sans-serif;font-size:14px;margin-bottom:8px}
.rm-how ol{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:7px;color:var(--mut);font-size:13px;line-height:1.45}
.rm-foot{display:flex;justify-content:space-between;color:var(--mut);font-size:12px;margin-top:18px;flex-wrap:wrap;gap:8px}
`;
