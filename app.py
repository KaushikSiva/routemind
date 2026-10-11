"""
RouteMind localhost dashboard.

    python app.py            # http://localhost:5050  (route = ROUTEMIND_ROUTE, default sf)

Press Drive and watch the car learn the real route on the map, trip by trip, with the
self-improvement curve filling in live. Toggle "learning" off to watch plain RAG stay lost.
The engine runs for real on each request (local vector store, embeddings cached at startup).
"""
import os

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from flask import Flask, jsonify, request

from memory import embed, LocalStore, Memory
from nav_tasks import (DECISIONS, junction_doc, make_bank, START, GOAL,
                       START_LABEL, GOAL_LABEL, CITY, ROUTE, ROUTE_JSON)

app = Flask(__name__)

GEOM = ROUTE_JSON["geometry"]["coordinates"]              # [lon, lat]
BANK = make_bank()
_UNIQ = sorted({b["document"] for b in BANK})
print(f"[{ROUTE}] embedding {len(_UNIQ)} unique junction texts for {len(BANK):,} memories…")
_VMAP = dict(zip(_UNIQ, embed(_UNIQ)))
BANK_VECS = [_VMAP[b["document"]] for b in BANK]
JVECS = embed([junction_doc(i, d) for i, d in enumerate(DECISIONS)])
print("ready — open http://localhost:5050")


def _nearest_idx(loc):                                     # loc = [lon, lat]
    return min(range(len(GEOM)), key=lambda i: (GEOM[i][0] - loc[0]) ** 2 + (GEOM[i][1] - loc[1]) ** 2)


def _cut(reached, first_fail):
    return len(GEOM) if reached else _nearest_idx(DECISIONS[first_fail]["loc"]) + 1


@app.route("/api/data")
def data():
    return jsonify({
        "route": ROUTE, "start_label": START_LABEL, "goal_label": GOAL_LABEL, "city": CITY,
        "geometry": [[lat, lon] for lon, lat in GEOM],
        "start": list(START), "goal": list(GOAL),
        "decisions": [{"on": d["on"], "loc": [d["loc"][1], d["loc"][0]], "action": d["action"]}
                      for d in DECISIONS],
        "n": len(DECISIONS), "store_size": len(BANK),
        "correct": sum(b["truth"] for b in BANK), "noise": sum(not b["truth"] for b in BANK),
        "distractors": sum(b.get("distractor", False) for b in BANK),
    })


@app.route("/api/run")
def run():
    learning = request.args.get("learning", "1") == "1"
    rounds = min(int(request.args.get("rounds", 14)), 40)
    store = LocalStore()
    for b, v in zip(BANK, BANK_VECS):
        store.add({**b, "vec": list(v), "uses": 0, "helped": 0, "usefulness": 0.5})
    mem = Memory(store, alpha=3.0, use_usefulness=learning)
    trips = []
    for r in range(rounds):
        correct, first_fail = 0, None
        for i, d in enumerate(DECISIONS):
            cands = mem.retrieve(JVECS[i], k=1, where={"junction": i})
            ok = bool(cands) and cands[0]["action"] == d["action"]
            if learning and cands:
                mem.record(cands, ok)
            if ok:
                correct += 1
            elif first_fail is None:
                first_fail = i
        if learning:
            mem.prune(min_uses=1, min_usefulness=0.4)
        reached = first_fail is None
        trips.append({"trip": r + 1, "correct_turns": correct, "reached": reached,
                      "first_fail": first_fail, "cut": _cut(reached, first_fail)})
    return jsonify({"learning": learning, "trips": trips})


@app.route("/")
def index():
    return PAGE


PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>RouteMind</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root{--bg:#0e1116;--panel:#161b22;--line:#2a2f36;--fg:#e8eaed;--mut:#8b9096;--mn:#1fa971;--rg:#e5733b;--blue:#2f81f7}
  *{box-sizing:border-box} html,body{margin:0;height:100%}
  body{background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:flex;flex-direction:column}
  header{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
  header h1{margin:0;font-size:19px;letter-spacing:.2px}
  header .sub{color:var(--mut)} header .route{color:var(--blue);font-weight:600}
  main{flex:1;display:flex;min-height:0} @media(max-width:860px){main{flex-direction:column}}
  #map{flex:1;min-height:320px;background:#223} .side{width:380px;max-width:42vw;border-left:1px solid var(--line);padding:18px;overflow:auto}
  @media(max-width:860px){.side{width:auto;max-width:none;border-left:0;border-top:1px solid var(--line)}}
  .btns{display:flex;gap:8px;margin-bottom:14px}
  button{font:inherit;font-weight:600;color:#fff;background:var(--mn);border:0;border-radius:8px;padding:10px 16px;cursor:pointer}
  button.ghost{background:#21262d;color:var(--fg);border:1px solid var(--line)}
  button:disabled{opacity:.5;cursor:default}
  .toggle{display:flex;align-items:center;gap:8px;margin-bottom:14px;color:var(--mut)}
  .status{font-size:22px;font-weight:700;margin:6px 0 2px} .status.ok{color:var(--mn)} .status.lost{color:var(--rg)}
  .meta{color:var(--mut);margin-bottom:12px}
  .stats{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}
  .stat{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px}
  .stat b{display:block;font-size:20px} .stat span{color:var(--mut);font-size:12px}
  canvas{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px;margin-top:8px}
  .leaflet-container{background:#1a1f26}
</style></head><body>
<header>
  <h1>🚗 RouteMind</h1>
  <span class="sub">self-improving route memory on <b>MongoDB Atlas Vector Search</b></span>
  <span class="route" id="routeName"></span>
</header>
<main>
  <div id="map"></div>
  <div class="side">
    <div class="btns">
      <button id="drive">▶ Drive</button>
      <button id="reset" class="ghost">Reset</button>
    </div>
    <label class="toggle"><input type="checkbox" id="learn" checked> learning on <span id="mode"></span></label>
    <div class="status" id="status">Press Drive</div>
    <div class="meta" id="trip"></div>
    <div class="stats">
      <div class="stat"><b id="sStore">—</b><span>memories in store</span></div>
      <div class="stat"><b id="sNoise">—</b><span>wrong / decoy turns</span></div>
    </div>
    <canvas id="chart" height="190"></canvas>
    <p class="meta" id="caption"></p>
  </div>
</main>
<script>
const COL={mn:'#1fa971',rg:'#e5733b',blue:'#2f81f7',mut:'#8b9096',grey:'#6b7280'};
let map, fullLine, driveLine, startM, goalM, lostM, chart, DATA, timer=null;

function mkChart(n){
  const ctx=document.getElementById('chart');
  chart=new Chart(ctx,{type:'line',
    data:{labels:[],datasets:[{label:'turns correct',data:[],borderColor:COL.mn,backgroundColor:COL.mn,tension:.25,pointRadius:3}]},
    options:{animation:false,plugins:{legend:{display:false}},
      scales:{y:{min:0,max:n,ticks:{color:COL.mut,stepSize:Math.max(1,Math.round(n/6))},grid:{color:'#2a2f36'},title:{display:true,text:'turns correct of '+n,color:COL.mut}},
              x:{ticks:{color:COL.mut},grid:{color:'#20242b'},title:{display:true,text:'trip',color:COL.mut}}}}});
}
async function load(){
  DATA=await (await fetch('/api/data')).json();
  document.getElementById('routeName').textContent=DATA.start_label+' → '+DATA.goal_label+' · '+DATA.city;
  document.getElementById('sStore').textContent=DATA.store_size.toLocaleString();
  document.getElementById('sNoise').textContent=DATA.noise.toLocaleString();
  document.getElementById('caption').textContent=
    `Atlas $vectorSearch finds each junction's turn inside ${DATA.store_size.toLocaleString()} vectors `+
    `(${DATA.distractors.toLocaleString()} decoys from other junctions). Recall is scoped to the junction; `+
    `usefulness-weighting + forgetting pick the turn that actually arrives.`;
  map=L.map('map',{zoomControl:true}).fitBounds(DATA.geometry);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);
  fullLine=L.polyline(DATA.geometry,{color:COL.grey,weight:4,opacity:.5,dashArray:'6 7'}).addTo(map);
  driveLine=L.polyline([],{color:COL.mn,weight:6}).addTo(map);
  startM=L.circleMarker(DATA.start,{radius:9,color:'#fff',weight:2,fillColor:COL.blue,fillOpacity:1}).addTo(map).bindTooltip(DATA.start_label);
  goalM=L.circleMarker(DATA.goal,{radius:9,color:'#fff',weight:2,fillColor:COL.grey,fillOpacity:1}).addTo(map).bindTooltip(DATA.goal_label);
  mkChart(DATA.n);
}
function reset(){
  if(timer){clearInterval(timer);timer=null;}
  driveLine.setLatLngs([]); goalM.setStyle({fillColor:COL.grey});
  if(lostM){map.removeLayer(lostM);lostM=null;}
  chart.data.labels=[];chart.data.datasets[0].data=[];chart.update();
  document.getElementById('status').textContent='Press Drive';document.getElementById('status').className='status';
  document.getElementById('trip').textContent='';document.getElementById('drive').disabled=false;
}
async function drive(){
  reset();
  const learn=document.getElementById('learn').checked;
  document.getElementById('drive').disabled=true;
  const res=await (await fetch('/api/run?learning='+(learn?1:0)+'&rounds=14')).json();
  const col=learn?COL.mn:COL.rg;
  chart.data.datasets[0].borderColor=col;chart.data.datasets[0].backgroundColor=col;
  let k=0;
  timer=setInterval(()=>{
    if(k>=res.trips.length){clearInterval(timer);timer=null;document.getElementById('drive').disabled=false;return;}
    const t=res.trips[k];
    driveLine.setLatLngs(DATA.geometry.slice(0,t.cut)).setStyle({color:t.reached?COL.mn:(learn?COL.mn:COL.rg)});
    if(lostM){map.removeLayer(lostM);lostM=null;}
    if(!t.reached){lostM=L.circleMarker(DATA.decisions[t.first_fail].loc,{radius:10,color:'#fff',weight:2,fillColor:COL.rg,fillOpacity:1})
        .addTo(map).bindTooltip('lost: '+DATA.decisions[t.first_fail].on);}
    goalM.setStyle({fillColor:t.reached?COL.mn:COL.grey});
    const s=document.getElementById('status');
    s.textContent=t.reached?('ARRIVED at '+DATA.goal_label):('LOST at '+DATA.decisions[t.first_fail].on);
    s.className='status '+(t.reached?'ok':'lost');
    document.getElementById('trip').textContent=`Trip ${t.trip} — ${t.correct_turns}/${DATA.n} turns correct`;
    chart.data.labels.push(t.trip);chart.data.datasets[0].data.push(t.correct_turns);chart.update();
    k++;
  },700);
}
document.getElementById('learn').addEventListener('change',e=>{
  document.getElementById('mode').textContent=e.target.checked?'(RouteMind)':'(plain RAG — stays lost)';});
document.getElementById('drive').onclick=drive;
document.getElementById('reset').onclick=reset;
load();
</script></body></html>"""


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
