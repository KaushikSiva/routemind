// The pitch, as an in-app tab. Reflects the latest run: Shack 15 → Ocean Beach,
// ~1,081 vectors on MongoDB Atlas, Voyage embeddings, arrives by trip 5, RAG never.

const MN = [3, 7, 8, 10, 11, 11, 11, 11]; // RouteMind correct turns / trip (latest Atlas run)
const RG = [2, 2, 2, 2, 2, 2, 2, 2]; // RAG, frozen
const N = 11;

function Curve() {
  const w = 320, h = 150, pad = 18;
  const pt = (arr: number[]) => arr.map((c, i) => {
    const x = pad + (i / (arr.length - 1)) * (w - 2 * pad);
    const y = h - pad - (c / N) * (h - 2 * pad);
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="pt-curve">
      <line x1={pad} y1={h - pad - (N / N) * (h - 2 * pad)} x2={w - pad} y2={h - pad - (h - 2 * pad)} className="pt-max" />
      <polyline points={pt(RG)} className="pt-rg" />
      <polyline points={pt(MN)} className="pt-mn" />
    </svg>
  );
}

export default function Pitch() {
  return (
    <div className="pt">
      <style>{CSS}</style>

      <section className="pt-slide pt-hero">
        <div className="pt-tag">MongoDB SFTW Hackathon</div>
        <h1>Agent memory that learns the route by <span className="g">forgetting its own wrong turns</span>.</h1>
        <p>RouteMind is self-improving memory on <b>MongoDB Atlas Vector Search</b>, with embeddings by
          <b> Voyage AI</b>. A car starts at Shack 15 with a head full of wrong directions and teaches
          itself the real drive to Ocean Beach, on real OpenStreetMap roads.</p>
      </section>

      <div className="pt-row">
        <section className="pt-slide">
          <h2 className="r">The problem</h2>
          <p>Agent memory today is frozen. Plain retrieval (RAG) ranks by similarity and never learns
            from what happened next. At a junction, every candidate turn can score the <b>same</b>
            similarity, so similarity alone cannot tell the right turn from the wrong one.</p>
          <div className="pt-stat"><b className="r">1.000</b><span>vector similarity of every candidate turn, so RAG cannot choose</span></div>
        </section>

        <section className="pt-slide">
          <h2 className="m">The idea</h2>
          <p>RouteMind scores each memory by whether recalling it <b>helped</b>, keeps the useful ones,
            and <b>deletes</b> the ones that mislead. The same vector search now ranks the turn it
            learned, not just the one that looks closest.</p>
          <div className="pt-loop">
            <span>recall from Atlas</span><i>→</i><span>drive</span><i>→</i>
            <span className="k">score usefulness</span><i>→</i><span className="x">forget noise</span><i>→</i><span className="k">better recall</span>
          </div>
        </section>
      </div>

      <section className="pt-slide pt-proof">
        <div>
          <h2 className="m">The proof</h2>
          <p>Over 1,081 vectors in MongoDB Atlas, RouteMind arrives by <b>trip 5</b>. The same memory
            with learning switched off never leaves the first block.</p>
          <div className="pt-stats">
            <div className="pt-stat"><b className="a">1,081</b><span>vectors in Atlas</span></div>
            <div className="pt-stat"><b className="r">27</b><span>wrong turns forgotten</span></div>
            <div className="pt-stat"><b className="m">trip 5</b><span>RouteMind arrives</span></div>
            <div className="pt-stat"><b className="r">never</b><span>RAG reaches the goal</span></div>
          </div>
        </div>
        <Curve />
      </section>

      <section className="pt-slide">
        <h2>Built for the brief: <span className="g">memory, persistence, self-evolving systems</span></h2>
        <ul>
          <li><b>MongoDB Atlas Vector Search</b> is the recall engine and the durable, self-evolving memory.</li>
          <li><b>Voyage AI</b> (voyage-3.5, 1024-d, via MongoDB) generates the embeddings.</li>
          <li><b>Raindrop</b> streams every recall so the self-improvement is observable.</li>
          <li><b>Modelence</b> hosts this app and dashboard; <b>ElevenLabs</b> narrates it.</li>
        </ul>
        <p className="pt-kick">It got lost in San Francisco, then it learned the way.</p>
      </section>
    </div>
  );
}

const CSS = `
.pt{--mn:#15a46e;--rg:#e4661f;--blue:#2563eb;--atlas:#00c767;max-width:1100px;margin:0 auto;display:flex;flex-direction:column;gap:16px}
.pt-slide{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:26px 30px;animation:ptin .5s both}
@keyframes ptin{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.pt-hero{background:radial-gradient(900px 300px at 20% -40%,#15a46e22,transparent),var(--panel)}
.pt h1{font-family:'Space Grotesk',Inter,sans-serif;font-size:34px;line-height:1.12;margin:10px 0 14px}
.pt h2{font-family:'Space Grotesk',Inter,sans-serif;font-size:22px;margin:0 0 10px}
.pt h2.m{color:var(--mn)} .pt h2.r{color:var(--rg)}
.pt p{color:var(--mut);font-size:16px;line-height:1.6;max-width:70ch} .pt b{color:var(--fg)}
.pt .g{background:linear-gradient(110deg,var(--mn),#36d3ff 60%,var(--blue));-webkit-background-clip:text;background-clip:text;color:transparent}
.pt-tag{display:inline-block;font-family:'Space Grotesk';font-size:12px;color:var(--atlas);border:1px solid #1e3a2a;background:#0d1f16;border-radius:20px;padding:5px 12px}
.pt-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:820px){.pt-row{grid-template-columns:1fr}}
.pt-loop{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:14px;font-family:'Space Grotesk';font-size:13px}
.pt-loop span{background:#0c1017;border:1px solid var(--line);border-radius:10px;padding:7px 11px}
.pt-loop i{color:var(--mut)} .pt-loop .k{color:var(--mn)} .pt-loop .x{color:var(--rg)}
.pt-proof{display:grid;grid-template-columns:1.4fr 1fr;gap:20px;align-items:center}@media(max-width:820px){.pt-proof{grid-template-columns:1fr}}
.pt-stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}
.pt-stat{background:#0c1017;border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.pt-stat b{font-family:'Space Grotesk';font-size:26px;display:block} .pt-stat span{color:var(--mut);font-size:12px}
.pt-stat b.a{color:var(--atlas)} .pt-stat b.m{color:var(--mn)} .pt-stat b.r{color:var(--rg)}
.pt-curve{width:100%;height:auto;background:#0c1017;border:1px solid var(--line);border-radius:12px}
.pt-max{stroke:#2a333f;stroke-dasharray:4 5}
.pt-mn{fill:none;stroke:var(--mn);stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.pt-rg{fill:none;stroke:var(--rg);stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.pt ul{margin:8px 0 0;padding-left:20px;display:flex;flex-direction:column;gap:9px;color:var(--mut);font-size:15px;line-height:1.5}
.pt-kick{font-family:'Space Grotesk';color:var(--fg);font-size:18px;margin-top:16px}
`;
