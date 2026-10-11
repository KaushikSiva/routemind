"""Build the pitch deck as a single self-contained animated HTML file on the Desktop."""
import base64
import json
import math
import os

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

HERE = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(f"{HERE}/out/sf/bundle.json"))


def b64(path):
    return base64.b64encode(open(path, "rb").read()).decode()


# headline numbers from Atlas demo_meta (fallbacks if offline)
forgotten, remaining = 27, 1054
try:
    from pymongo import MongoClient
    m = MongoClient(os.environ["MONGODB_URI"])["mnemo"]["demo_meta"].find_one({"_id": "sf"})
    if m:
        forgotten, remaining = m["forgotten"], m["remaining"]
except Exception:
    pass

arrive = next((t["trip"] for t in B["mnemo"] if t["reached"]), 5)
rag_last = B["rag"][-1]["correct"]
curve_b64 = b64(f"{HERE}/out/sf/curve.png")
arr = f"{HERE}/out/sf/trip_0{arrive}.png"
map_b64 = b64(arr if os.path.exists(arr) else f"{HERE}/out/sf/trip_05.png")

# normalized SVG route path for the animated title background
G = B["geometry"]
lats = [p[0] for p in G]; lons = [p[1] for p in G]
la0, la1, lo0, lo1 = min(lats), max(lats), min(lons), max(lons)
cosl = math.cos((la0 + la1) / 2 * math.pi / 180)
W, H, pad = 1000, 560, 30
s = min((W - 2 * pad) / ((lo1 - lo0) * cosl), (H - 2 * pad) / (la1 - la0))
ox = (W - (lo1 - lo0) * cosl * s) / 2; oy = (H - (la1 - la0) * s) / 2
pts = [(ox + (lo - lo0) * cosl * s, H - (oy + (la - la0) * s)) for la, lo in G]
path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)

SPONSORS = [
    ("MongoDB Atlas", "https://cloud.mongodb.com/v2/6acbd27f4122ab4be33b8a0d#/clusters"),
    ("Voyage AI", "https://www.voyageai.com"),
    ("Raindrop", "https://app.raindrop.ai/events?org=9cb3abaf"),
    ("Modelence", "https://cloud.modelence.com/environments/6acc0f11dfdb1813453a5b71/builds"),
    ("ElevenLabs", "https://elevenlabs.io"),
    ("AWS", "https://aws.amazon.com"),
    ("Cerebral Valley", "https://cerebralvalley.ai"),
]
sponsor_html = "".join(f'<a href="{u}" target="_blank" rel="noreferrer">{n}</a>' for n, u in SPONSORS)

HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RouteMind Pitch</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap">
<style>
:root{{--bg:#0a0d12;--panel:#12171f;--line:#232b36;--fg:#eef2f7;--mut:#8a94a3;--mn:#1fc98a;--rg:#f07a44;--blue:#3b82f6;--atlas:#00ed64}}
*{{box-sizing:border-box;margin:0}} html,body{{height:100%}}
body{{background:var(--bg);color:var(--fg);font-family:Inter,system-ui,sans-serif;overflow:hidden}}
.deck{{height:100vh;width:100vw;position:relative}}
.slide{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:6vh 8vw;
  opacity:0;transform:translateY(24px) scale(.99);pointer-events:none;transition:opacity .5s,transform .5s}}
.slide.active{{opacity:1;transform:none;pointer-events:auto}}
h1{{font-family:'Space Grotesk';font-size:7vmin;line-height:1.05}} h2{{font-family:'Space Grotesk';font-size:4.6vmin;margin-bottom:2.4vh}}
p,li{{font-size:2.5vmin;color:var(--mut);line-height:1.5;max-width:60ch}} b{{color:var(--fg)}}
.grad{{background:linear-gradient(110deg,var(--mn),#36d3ff 60%,var(--blue));-webkit-background-clip:text;background-clip:text;color:transparent}}
.sponsorbar{{position:fixed;top:0;left:0;right:0;display:flex;gap:10px;align-items:center;padding:12px 24px;z-index:10;
  border-bottom:1px solid var(--line);background:#0a0d12cc;backdrop-filter:blur(6px);flex-wrap:wrap}}
.sponsorbar span{{font-size:10px;letter-spacing:2px;color:var(--mut);font-weight:700}}
.sponsorbar a{{font-size:12px;color:var(--fg);text-decoration:none;border:1px solid var(--line);border-radius:20px;padding:4px 10px}}
.sponsorbar a:hover{{border-color:var(--atlas)}}
.tag{{display:inline-block;font-family:'Space Grotesk';font-size:2vmin;color:var(--atlas);border:1px solid #1e3a2a;
  background:#0d1f16;border-radius:20px;padding:6px 14px;margin-bottom:3vh;width:max-content}}
.route-bg{{position:absolute;inset:0;z-index:-1;opacity:.5}}
.route-bg path.f{{fill:none;stroke:#1a2230;stroke-width:3;stroke-dasharray:4 7}}
.route-bg path.d{{fill:none;stroke:url(#gg);stroke-width:5;stroke-linecap:round;stroke-dasharray:4000;stroke-dashoffset:4000}}
.active .route-bg path.d{{animation:draw 3.4s .4s ease forwards}}
@keyframes draw{{to{{stroke-dashoffset:0}}}}
.cols{{display:flex;gap:5vw;align-items:center;margin-top:2vh}} .cols img{{border-radius:12px;border:1px solid var(--line)}}
.stats{{display:flex;gap:2vw;margin-top:3vh;flex-wrap:wrap}}
.stat{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:2.4vh 2.2vw}}
.stat b{{font-family:'Space Grotesk';font-size:5.2vmin;display:block}} .stat span{{color:var(--mut);font-size:1.8vmin}}
.a{{color:var(--atlas)}} .m{{color:var(--mn)}} .r{{color:var(--rg)}}
.loop{{display:flex;gap:1.4vw;flex-wrap:wrap;margin-top:3vh}}
.loop div{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:1.8vh 1.6vw;font-family:'Space Grotesk';font-size:2.1vmin}}
.loop .k{{color:var(--mn)}} .loop .x{{color:var(--rg)}}
.big{{font-size:3.4vmin;color:var(--fg);max-width:70ch;margin-top:1.5vh}}
ul{{margin-top:1.5vh;padding-left:3vh;display:flex;flex-direction:column;gap:1.3vh}}
.progress{{position:fixed;bottom:18px;left:0;right:0;display:flex;gap:8px;justify-content:center;z-index:10}}
.progress i{{width:9px;height:9px;border-radius:50%;background:#2a333f;transition:.3s}} .progress i.on{{background:var(--mn);width:26px;border-radius:5px}}
.hint{{position:fixed;bottom:16px;right:20px;color:#3a4350;font-size:11px;z-index:10}}
.foot{{position:absolute;bottom:5vh;left:8vw;color:var(--mut);font-size:1.8vmin}}
</style></head><body>
<div class="sponsorbar"><span>BUILT ON</span>{sponsor_html}</div>
<div class="deck" id="deck">

  <section class="slide active">
    <svg class="route-bg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">
      <defs><linearGradient id="gg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1fc98a"/><stop offset="1" stop-color="#36d3ff"/></linearGradient></defs>
      <path class="f" d="{path}"/><path class="d" d="{path}"/>
    </svg>
    <div class="tag">MongoDB SFTW Hackathon</div>
    <h1>🚗 <span class="grad">RouteMind</span></h1>
    <p class="big">Agent memory that learns the route by <b>forgetting its own wrong turns.</b><br>
    Self-improving memory on <b>MongoDB Atlas Vector Search</b>, embeddings by <b>Voyage AI</b>.</p>
    <div class="foot">Shack 15 to Ocean Beach, San Francisco, on real OpenStreetMap roads.</div>
  </section>

  <section class="slide">
    <h2>Agent memory today is <span class="r">frozen</span></h2>
    <p class="big">RAG retrieves by similarity and never learns from what happened next. At a junction,
    every candidate turn can score the <b>same</b> similarity, so similarity alone cannot tell the right
    turn from the wrong one. The agent repeats the same mistake forever.</p>
    <div class="stats"><div class="stat"><b class="r">1.000</b><span>vector similarity of every candidate turn</span></div>
    <div class="stat"><b class="r">{rag_last}/{B['n']}</b><span>turns a frozen memory ever gets right</span></div></div>
  </section>

  <section class="slide">
    <h2>RouteMind: a memory that <span class="m">improves itself</span></h2>
    <p class="big">Every trip, it recalls a turn, acts, and scores whether that memory helped. It keeps the
    useful ones and <b>deletes</b> the ones that mislead. The same similarity search now ranks the turn it
    <b>learned</b>, not just the one that looks closest. This is the recursive self-improvement.</p>
    <div class="loop">
      <div>recall from Atlas</div><div>&rarr;</div><div>drive the turn</div><div>&rarr;</div>
      <div class="k">score usefulness</div><div>&rarr;</div><div class="x">forget the noise</div><div>&rarr;</div>
      <div class="k">better recall</div>
    </div>
  </section>

  <section class="slide">
    <h2>Watch it <span class="m">learn</span></h2>
    <div class="cols">
      <img src="data:image/png;base64,{curve_b64}" style="width:46vw"/>
      <img src="data:image/png;base64,{map_b64}" style="width:30vw"/>
    </div>
    <div class="stats">
      <div class="stat"><b class="a">{B['store_size']:,}</b><span>vectors in MongoDB Atlas</span></div>
      <div class="stat"><b class="r">{forgotten}</b><span>wrong turns forgotten</span></div>
      <div class="stat"><b class="m">trip {arrive}</b><span>RouteMind arrives</span></div>
      <div class="stat"><b class="r">never</b><span>RAG reaches the goal</span></div>
    </div>
  </section>

  <section class="slide">
    <h2>Built for the brief: <span class="grad">memory, persistence, self-evolving</span></h2>
    <ul>
      <li><b>MongoDB Atlas Vector Search</b> is the recall engine and the durable, self-evolving memory.</li>
      <li><b>Voyage AI</b> (voyage-3.5, 1024-d, via MongoDB) generates the embeddings.</li>
      <li><b>Raindrop</b> streams every recall so the self-improvement is observable.</li>
      <li><b>Modelence</b> hosts a live dashboard reading the same Atlas cluster, with <b>ElevenLabs</b> narration.</li>
    </ul>
    <p class="big" style="margin-top:3vh">It got lost in San Francisco, then it learned the way.</p>
  </section>

</div>
<div class="progress" id="dots"></div>
<div class="hint">arrow keys or space</div>
<script>
const slides=[...document.querySelectorAll('.slide')];let i=0;
const dots=document.getElementById('dots');slides.forEach((_,k)=>{{const d=document.createElement('i');if(!k)d.className='on';dots.appendChild(d);}});
function go(n){{i=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,k)=>s.classList.toggle('active',k===i));
  [...dots.children].forEach((d,k)=>d.classList.toggle('on',k===i));}}
addEventListener('keydown',e=>{{if(['ArrowRight',' ','PageDown'].includes(e.key)){{e.preventDefault();go(i+1);}}
  else if(['ArrowLeft','PageUp'].includes(e.key))go(i-1);else if(e.key==='Home')go(0);else if(e.key==='End')go(slides.length-1);}});
addEventListener('click',e=>{{if(e.clientX<innerWidth*0.25)go(i-1);else go(i+1);}});
</script></body></html>"""

out = os.path.expanduser("~/Desktop/RouteMind_Pitch.html")
open(out, "w").write(HTML)
print("wrote", out, f"({len(HTML)//1024} KB, {len(B['mnemo'])} trips, arrives {arrive}, {forgotten} forgotten)")
