"""
RouteMind localhost dashboard.

    python app.py            # http://localhost:5050

Type ANY start and destination, and RouteMind builds the real OpenStreetMap route live, then
learns it trip by trip on the map — the self-improvement curve filling in as it goes. Toggle
"learning" off to watch plain RAG stay lost. The engine runs for real (local vector store;
embeddings computed per route and cached).
"""
import os
import re

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from flask import Flask, jsonify, request

from build_route import geocode, route as osrm_route, decisions_from
from memory import embed, LocalStore, Memory
from nav_tasks import (DECISIONS, make_bank_for, jdoc, START, GOAL,
                       START_LABEL, GOAL_LABEL, CITY, ROUTE_JSON)

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
STATE = {}


def _nearest_idx(geom, loc):                               # loc = [lon, lat]
    return min(range(len(geom)), key=lambda i: (geom[i][0] - loc[0]) ** 2 + (geom[i][1] - loc[1]) ** 2)


def set_route(geom, decisions, start, goal, start_label, goal_label, city):
    """Build the memory store for this route and embed it (cached in STATE)."""
    turns = [d for d in decisions if d["type"] != "arrive"]
    bank = make_bank_for(turns, goal_label)
    uniq = sorted({b["document"] for b in bank})
    vmap = dict(zip(uniq, embed(uniq)))
    STATE.update({
        "geom": geom, "decisions": turns, "start": list(start), "goal": list(goal),
        "start_label": start_label, "goal_label": goal_label, "city": city,
        "bank": bank, "bank_vecs": [vmap[b["document"]] for b in bank],
        "jvecs": embed([jdoc(i, d["on"], goal_label) for i, d in enumerate(turns)]),
    })
    return STATE


def _data():
    s = STATE
    return {
        "start_label": s["start_label"], "goal_label": s["goal_label"], "city": s["city"],
        "geometry": [[lat, lon] for lon, lat in s["geom"]],
        "start": s["start"], "goal": s["goal"],
        "decisions": [{"on": d["on"], "loc": [d["loc"][1], d["loc"][0]], "action": d["action"]}
                      for d in s["decisions"]],
        "n": len(s["decisions"]), "store_size": len(s["bank"]),
        "noise": sum(not b["truth"] for b in s["bank"]),
        "distractors": sum(b.get("distractor", False) for b in s["bank"]),
    }


@app.route("/api/data")
def data():
    return jsonify(_data())


@app.route("/api/build")
def build():
    start_q = request.args.get("start", "").strip()
    goal_q = request.args.get("goal", "").strip()
    if not start_q or not goal_q:
        return jsonify({"error": "enter both a start and a destination"}), 400
    try:
        s = geocode(start_q)
        g = geocode(goal_q)
        osrm = osrm_route(s, g)
        decs = decisions_from(osrm)
    except SystemExit as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"could not build route: {e}"}), 400
    turns = [d for d in decs if d["type"] != "arrive"]
    if len(turns) < 2:
        return jsonify({"error": "that route has too few turns — try points further apart"}), 400

    def label(q):
        return re.split(r",", q)[0].strip()[:28]
    city = ""
    parts = [p.strip() for p in goal_q.split(",")]
    if len(parts) > 1:
        city = parts[-1]
    set_route(osrm["routes"][0]["geometry"]["coordinates"], decs, s, g,
              label(start_q), label(goal_q), city)
    return jsonify(_data())


@app.route("/api/run")
def run():
    learning = request.args.get("learning", "1") == "1"
    rounds = min(int(request.args.get("rounds", 14)), 40)
    s = STATE
    store = LocalStore()
    for b, v in zip(s["bank"], s["bank_vecs"]):
        store.add({**b, "vec": list(v), "uses": 0, "helped": 0, "usefulness": 0.5})
    mem = Memory(store, alpha=3.0, use_usefulness=learning)
    trips = []
    for r in range(rounds):
        correct, first_fail = 0, None
        for i, d in enumerate(s["decisions"]):
            cands = mem.retrieve(s["jvecs"][i], k=1, where={"junction": i})
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
        cut = len(s["geom"]) if reached else _nearest_idx(s["geom"], s["decisions"][first_fail]["loc"]) + 1
        trips.append({"trip": r + 1, "correct_turns": correct, "reached": reached,
                      "first_fail": first_fail, "cut": cut})
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
  header h1{margin:0;font-size:19px} header .sub{color:var(--mut)} header .route{color:var(--blue);font-weight:600}
  main{flex:1;display:flex;min-height:0} @media(max-width:860px){main{flex-direction:column}}
  #map{flex:1;min-height:340px;background:#1a1f26} .side{width:390px;max-width:44vw;border-left:1px solid var(--line);padding:18px;overflow:auto}
  @media(max-width:860px){.side{width:auto;max-width:none;border-left:0;border-top:1px solid var(--line)}}
  .field{display:flex;flex-direction:column;gap:4px;margin-bottom:8px}
  .field label{font-size:12px;color:var(--mut)}
  input[type=text]{font:inherit;color:var(--fg);background:#0b0e13;border:1px solid var(--line);border-radius:7px;padding:9px 11px}
  .btns{display:flex;gap:8px;margin:10px 0 6px}
  button{font:inherit;font-weight:600;color:#fff;background:var(--mn);border:0;border-radius:8px;padding:10px 16px;cursor:pointer}
  button.blue{background:var(--blue)} button.ghost{background:#21262d;color:var(--fg);border:1px solid var(--line)}
  button:disabled{opacity:.5;cursor:default}
  .chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px}
  .chip{font-size:12px;color:var(--mut);background:#21262d;border:1px solid var(--line);border-radius:20px;padding:4px 10px;cursor:pointer}
  .hr{height:1px;background:var(--line);margin:14px 0}
  .toggle{display:flex;align-items:center;gap:8px;margin:4px 0 12px;color:var(--mut)}
  .status{font-size:21px;font-weight:700;margin:4px 0 2px} .status.ok{color:var(--mn)} .status.lost{color:var(--rg)} .status.work{color:var(--blue)}
  .meta{color:var(--mut);margin-bottom:10px}
  .stats{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}
  .stat{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px}
  .stat b{display:block;font-size:19px} .stat span{color:var(--mut);font-size:12px}
  canvas{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px;margin-top:8px}
  .leaflet-container{background:#1a1f26}
</style></head><body>
<header>
  <h1>🚗 RouteMind</h1>
  <span class="sub">self-improving route memory · <b>MongoDB Atlas Vector Search</b></span>
  <span class="route" id="routeName"></span>
</header>
<main>
  <div id="map"></div>
  <div class="side">
    <div class="field"><label>Start</label><input type="text" id="start" placeholder="e.g. Ferry Building, San Francisco"></div>
    <div class="field"><label>Destination</label><input type="text" id="goal" placeholder="e.g. Ocean Beach, San Francisco"></div>
    <div class="chips" id="chips"></div>
    <div class="btns"><button class="blue" id="build">🧭 Build route</button></div>
    <div class="hr"></div>
    <div class="btns">
      <button id="drive">▶ Drive</button>
      <button id="reset" class="ghost">Reset</button>
    </div>
    <label class="toggle"><input type="checkbox" id="learn" checked> learning on <span id="mode"></span></label>
    <div class="status" id="status">Build a route, then press Drive</div>
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
const EXAMPLES=[
  ['Ferry Building, San Francisco','Ocean Beach, San Francisco'],
  ['Golden Gate Bridge','Oracle Park, San Francisco'],
  ['Kodambakkam Railway Station','Jains Antariksha, Chennai'],
];
let map, fullLine, driveLine, startM, goalM, lostM, chart, DATA, timer=null;

function setStatus(t,cls){const s=document.getElementById('status');s.textContent=t;s.className='status '+(cls||'');}
function mkChart(n){
  if(chart) chart.destroy();
  chart=new Chart(document.getElementById('chart'),{type:'line',
    data:{labels:[],datasets:[{data:[],borderColor:COL.mn,backgroundColor:COL.mn,tension:.25,pointRadius:3}]},
    options:{animation:false,plugins:{legend:{display:false}},
      scales:{y:{min:0,max:n,ticks:{color:COL.mut,stepSize:Math.max(1,Math.round(n/6))},grid:{color:'#2a2f36'},title:{display:true,text:'turns correct of '+n,color:COL.mut}},
              x:{ticks:{color:COL.mut},grid:{color:'#20242b'},title:{display:true,text:'trip',color:COL.mut}}}}});
}
function setRoute(d){
  DATA=d;
  document.getElementById('routeName').textContent=d.start_label+' → '+d.goal_label+(d.city?(' · '+d.city):'');
  document.getElementById('sStore').textContent=d.store_size.toLocaleString();
  document.getElementById('sNoise').textContent=d.noise.toLocaleString();
  document.getElementById('caption').textContent=
    `Atlas $vectorSearch finds each junction's turn inside ${d.store_size.toLocaleString()} vectors `+
    `(${d.distractors.toLocaleString()} decoys). Recall is scoped to the junction; usefulness-weighting + forgetting pick the turn that arrives.`;
  [fullLine,driveLine,startM,goalM,lostM].forEach(l=>{if(l)map.removeLayer(l);}); lostM=null;
  fullLine=L.polyline(d.geometry,{color:COL.grey,weight:4,opacity:.5,dashArray:'6 7'}).addTo(map);
  driveLine=L.polyline([],{color:COL.mn,weight:6}).addTo(map);
  startM=L.circleMarker(d.start,{radius:9,color:'#fff',weight:2,fillColor:COL.blue,fillOpacity:1}).addTo(map).bindTooltip(d.start_label);
  goalM=L.circleMarker(d.goal,{radius:9,color:'#fff',weight:2,fillColor:COL.grey,fillOpacity:1}).addTo(map).bindTooltip(d.goal_label);
  map.fitBounds(d.geometry,{padding:[30,30]});
  mkChart(d.n);
  setStatus(`${d.n} turns · ${d.store_size.toLocaleString()} memories · press Drive`);
  document.getElementById('trip').textContent='';
}
async function build(){
  const start=document.getElementById('start').value.trim(), goal=document.getElementById('goal').value.trim();
  if(!start||!goal){setStatus('Enter a start and a destination','lost');return;}
  if(timer){clearInterval(timer);timer=null;}
  document.getElementById('build').disabled=true; document.getElementById('drive').disabled=true;
  setStatus('Building route from OpenStreetMap…','work');
  try{
    const r=await fetch('/api/build?start='+encodeURIComponent(start)+'&goal='+encodeURIComponent(goal));
    const d=await r.json();
    if(!r.ok){setStatus(d.error||'could not build route','lost');return;}
    setRoute(d);
  }catch(e){setStatus('build failed: '+e,'lost');}
  finally{document.getElementById('build').disabled=false; document.getElementById('drive').disabled=false;}
}
function reset(){
  if(timer){clearInterval(timer);timer=null;}
  if(DATA){driveLine.setLatLngs([]); goalM.setStyle({fillColor:COL.grey});}
  if(lostM){map.removeLayer(lostM);lostM=null;}
  if(chart){chart.data.labels=[];chart.data.datasets[0].data=[];chart.update();}
  setStatus(DATA?'Press Drive':'Build a route, then press Drive');
  document.getElementById('trip').textContent='';document.getElementById('drive').disabled=!DATA;
}
async function drive(){
  if(!DATA){setStatus('Build a route first','lost');return;}
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
    driveLine.setLatLngs(DATA.geometry.slice(0,t.cut)).setStyle({color:t.reached?COL.mn:col});
    if(lostM){map.removeLayer(lostM);lostM=null;}
    if(!t.reached){lostM=L.circleMarker(DATA.decisions[t.first_fail].loc,{radius:10,color:'#fff',weight:2,fillColor:COL.rg,fillOpacity:1})
        .addTo(map).bindTooltip('lost: '+DATA.decisions[t.first_fail].on);}
    goalM.setStyle({fillColor:t.reached?COL.mn:COL.grey});
    setStatus(t.reached?('ARRIVED at '+DATA.goal_label):('LOST at '+DATA.decisions[t.first_fail].on),t.reached?'ok':'lost');
    document.getElementById('trip').textContent=`Trip ${t.trip} — ${t.correct_turns}/${DATA.n} turns correct`;
    chart.data.labels.push(t.trip);chart.data.datasets[0].data.push(t.correct_turns);chart.update();
    k++;
  },700);
}
const chips=document.getElementById('chips');
EXAMPLES.forEach(([s,g])=>{const c=document.createElement('span');c.className='chip';c.textContent=s.split(',')[0]+' → '+g.split(',')[0];
  c.onclick=()=>{document.getElementById('start').value=s;document.getElementById('goal').value=g;build();};chips.appendChild(c);});
document.getElementById('learn').addEventListener('change',e=>{
  document.getElementById('mode').textContent=e.target.checked?'(RouteMind)':'(plain RAG — stays lost)';});
document.getElementById('build').onclick=build;
document.getElementById('drive').onclick=drive;
document.getElementById('reset').onclick=reset;

map=L.map('map',{zoomControl:true}).setView([37.76,-122.45],12);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);
fetch('/api/data').then(r=>r.json()).then(setRoute);   // load the default route on start
</script></body></html>"""


def _boot():
    set_route(ROUTE_JSON["geometry"]["coordinates"],
              DECISIONS + [{"type": "arrive"}],            # DECISIONS already excludes arrive
              START, GOAL, START_LABEL, GOAL_LABEL, CITY)
    print("ready — open http://localhost:5050")


if __name__ == "__main__":
    _boot()
    app.run(host="127.0.0.1", port=5050, debug=False)
