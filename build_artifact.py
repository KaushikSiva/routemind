"""Build the hosted demo artifact: embed the real Atlas run bundles into a self-contained page."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("ART_OUT", "/tmp/routemind_demo.html")
BUNDLES = {s: json.load(open(f"{HERE}/out/{s}/bundle.json")) for s in ("sf", "gg")}

HTML = r"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>RouteMind</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{color-scheme:dark;--bg:#0b0e13;--panel:#141922;--line:#242b36;--fg:#e9edf2;--mut:#8b94a3;
  --mn:#1fc98a;--rg:#f07a44;--blue:#3b82f6;--atlas:#00ed64;--grid:#1b212b}
*{box-sizing:border-box} html,body{margin:0;height:100%}
body{background:var(--bg);color:var(--fg);font:15px/1.5 Inter,system-ui,sans-serif;display:flex;flex-direction:column;overflow-x:hidden}
h1,h2,.mono{font-family:"Space Grotesk",sans-serif}
header{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:14px 20px;border-bottom:1px solid var(--line)}
header h1{font-size:20px;margin:0;letter-spacing:.3px} .car{font-size:22px}
.badge{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;color:#04150c;background:var(--atlas);border-radius:20px;padding:4px 10px}
.sub{color:var(--mut);font-size:13px}
main{flex:1;display:flex;min-height:0}@media(max-width:880px){main{flex-direction:column}}
.stage{flex:1;position:relative;min-height:340px}
canvas#map{display:block;width:100%;height:100%}
.overlay{position:absolute;left:16px;top:14px;right:16px;display:flex;justify-content:space-between;pointer-events:none;gap:12px;flex-wrap:wrap}
.status{font-family:"Space Grotesk";font-size:20px;font-weight:700} .status.ok{color:var(--mn)} .status.lost{color:var(--rg)} .status.idle{color:var(--mut)}
.tripbadge{color:var(--mut);font-size:13px;text-align:right}
.side{width:380px;max-width:44vw;border-left:1px solid var(--line);padding:18px;overflow:auto}
@media(max-width:880px){.side{width:auto;max-width:none;border-left:0;border-top:1px solid var(--line)}}
.routes{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.rt{flex:1;min-width:150px;text-align:left;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;cursor:pointer;color:var(--fg)}
.rt.active{border-color:var(--atlas);box-shadow:0 0 0 1px var(--atlas) inset}
.rt b{display:block;font-size:14px} .rt span{color:var(--mut);font-size:12px}
.btns{display:flex;gap:8px;margin-bottom:12px}
button{font:inherit;font-weight:600;cursor:pointer;border:0;border-radius:9px;padding:11px 16px}
.drive{background:var(--mn);color:#04150c;flex:1} .reset{background:#1c222c;color:var(--fg);border:1px solid var(--line)}
button:disabled{opacity:.5;cursor:default}
.toggle{display:flex;align-items:center;gap:8px;color:var(--mut);margin-bottom:14px;font-size:14px}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:4px 0 14px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px}
.stat b{display:block;font-family:"Space Grotesk";font-size:22px} .stat span{color:var(--mut);font-size:12px}
.stat .atlas{color:var(--atlas)}
canvas#chart{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px}
.cap{color:var(--mut);font-size:12.5px;margin-top:12px}
.legend{display:flex;gap:14px;font-size:12px;color:var(--mut);margin-top:10px;flex-wrap:wrap}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle}
</style></head><body>
<header>
  <span class="car">🚗</span><h1>RouteMind</h1>
  <span class="badge">● MongoDB Atlas Vector Search</span>
  <span class="sub">memory that learns the route by forgetting its own wrong turns</span>
</header>
<main>
  <div class="stage">
    <canvas id="map"></canvas>
    <div class="overlay">
      <div><div class="status idle" id="status">Press Drive</div><div class="sub" id="routeName"></div></div>
      <div class="tripbadge" id="trip"></div>
    </div>
  </div>
  <div class="side">
    <div class="routes" id="routes"></div>
    <div class="btns"><button class="drive" id="drive">▶ Drive</button><button class="reset" id="reset">Reset</button></div>
    <label class="toggle"><input type="checkbox" id="learn" checked> learning on <span id="mode" class="sub"></span></label>
    <div class="stats">
      <div class="stat"><b class="atlas" id="sStore">—</b><span>vectors in Atlas</span></div>
      <div class="stat"><b id="sNoise">—</b><span>wrong / decoy turns</span></div>
    </div>
    <canvas id="chart" height="190"></canvas>
    <div class="legend">
      <span><i class="dot" style="background:#1fc98a"></i>RouteMind (learns)</span>
      <span><i class="dot" style="background:#f07a44"></i>RAG (frozen)</span>
      <span><i class="dot" style="background:#3b82f6"></i>start</span>
      <span><i class="dot" style="background:#e53935"></i>lost</span>
    </div>
    <p class="cap" id="cap"></p>
  </div>
</main>
<script>
const DATA=__BUNDLES__;
const COL={mn:'#1fc98a',rg:'#f07a44',blue:'#3b82f6',grey:'#4b5563',mut:'#8b94a3',lost:'#e53935'};
let cur='sf', chart, timer=null, anim=null;
const cv=document.getElementById('map'), ctx=cv.getContext('2d');

function proj(d,w,h){
  const lats=d.geometry.map(p=>p[0]), lons=d.geometry.map(p=>p[1]);
  const la0=Math.min(...lats),la1=Math.max(...lats),lo0=Math.min(...lons),lo1=Math.max(...lons);
  const pad=46, cosl=Math.cos((la0+la1)/2*Math.PI/180);
  const sx=(w-2*pad)/Math.max(1e-6,(lo1-lo0)*cosl), sy=(h-2*pad)/Math.max(1e-6,(la1-la0));
  const s=Math.min(sx,sy);
  const ox=(w-(lo1-lo0)*cosl*s)/2, oy=(h-(la1-la0)*s)/2;
  return [p=>ox+(p[1]-lo0)*cosl*s, p=>h-(oy+(p[0]-la0)*s)];
}
function resize(){const r=cv.parentElement.getBoundingClientRect();const dpr=devicePixelRatio||1;
  cv.width=r.width*dpr;cv.height=r.height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);draw(state);}
let state={cut:0,lost:null,reached:false,learn:true};
function draw(st){
  const d=DATA[cur], w=cv.clientWidth, h=cv.clientHeight;
  ctx.clearRect(0,0,w,h);
  // grid
  ctx.strokeStyle='#141a22';ctx.lineWidth=1;
  for(let x=0;x<w;x+=38){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
  for(let y=0;y<h;y+=38){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
  const [fx,fy]=proj(d,w,h), G=d.geometry;
  const line=(a,b,col,wd)=>{ctx.strokeStyle=col;ctx.lineWidth=wd;ctx.lineJoin='round';ctx.lineCap='round';
    ctx.beginPath();for(let i=a;i<b;i++){const X=fx(G[i]),Y=fy(G[i]);i===a?ctx.moveTo(X,Y):ctx.lineTo(X,Y);}ctx.stroke();};
  ctx.setLineDash([5,7]);line(0,G.length,'#39424f',3);ctx.setLineDash([]);
  const col=st.reached?COL.mn:(st.learn?COL.mn:COL.rg);
  if(st.cut>1)line(0,st.cut,col,6);
  const mk=(p,c,r)=>{ctx.beginPath();ctx.arc(fx(p),fy(p),r,0,7);ctx.fillStyle=c;ctx.fill();ctx.lineWidth=2;ctx.strokeStyle='#0b0e13';ctx.stroke();};
  mk(d.start,COL.blue,7); mk(d.goal,st.reached?COL.mn:COL.grey,7);
  if(st.lost!=null)mk(d.decisions[st.lost].loc,COL.lost,7);
}
function mkChart(n){if(chart)chart.destroy();
  chart=new Chart(document.getElementById('chart'),{type:'line',
    data:{labels:[],datasets:[{data:[],borderColor:COL.mn,backgroundColor:COL.mn,tension:.25,pointRadius:2,borderWidth:2.5}]},
    options:{animation:false,plugins:{legend:{display:false}},
      scales:{y:{min:0,max:n,ticks:{color:COL.mut,stepSize:Math.max(1,Math.round(n/6))},grid:{color:'#1b212b'},title:{display:true,text:'turns correct of '+n,color:COL.mut}},
              x:{ticks:{color:COL.mut},grid:{color:'#141a22'},title:{display:true,text:'trip',color:COL.mut}}}}});
}
function setStatus(t,c){const s=document.getElementById('status');s.textContent=t;s.className='status '+(c||'idle');}
function selectRoute(k){
  cur=k;const d=DATA[k];
  document.querySelectorAll('.rt').forEach(e=>e.classList.toggle('active',e.dataset.k===k));
  document.getElementById('routeName').textContent=d.start_label+' → '+d.goal_label+' · '+d.city;
  document.getElementById('sStore').textContent=d.store_size.toLocaleString();
  document.getElementById('sNoise').textContent=d.noise.toLocaleString();
  document.getElementById('cap').textContent=
    `A filtered $vectorSearch finds this junction's turn inside ${d.store_size.toLocaleString()} vectors `+
    `(${d.distractors.toLocaleString()} decoys from other junctions). Usefulness-weighting keeps the turns that help and `+
    `forgets the ones that mislead — so the route locks in over a few trips. RAG, same vectors frozen, stays lost.`;
  reset();
}
function reset(){
  if(timer){clearInterval(timer);timer=null;}
  state={cut:0,lost:null,reached:false,learn:document.getElementById('learn').checked};
  mkChart(DATA[cur].n);draw(state);
  setStatus('Press Drive','idle');document.getElementById('trip').textContent='';document.getElementById('drive').disabled=false;
}
function drive(){
  const d=DATA[cur], learn=document.getElementById('learn').checked;
  reset();state.learn=learn;
  const trips=learn?d.mnemo:d.rag, c=learn?COL.mn:COL.rg;
  chart.data.datasets[0].borderColor=c;chart.data.datasets[0].backgroundColor=c;
  document.getElementById('drive').disabled=true;
  let k=0;
  timer=setInterval(()=>{
    if(k>=trips.length){clearInterval(timer);timer=null;document.getElementById('drive').disabled=false;return;}
    const t=trips[k];
    // animate the path growing
    const from=state.cut, to=t.cut, t0=performance.now();
    (function step(now){const p=Math.min(1,(now-t0)/420);state.cut=Math.round(from+(to-from)*p);
      state.lost=t.reached?null:t.first_fail;state.reached=t.reached;draw(state);
      if(p<1)anim=requestAnimationFrame(step);})(t0);
    setStatus(t.reached?('ARRIVED at '+d.goal_label):('LOST at '+d.decisions[t.first_fail].on),t.reached?'ok':'lost');
    document.getElementById('trip').textContent=`Trip ${t.trip} · ${t.correct}/${d.n} turns correct`;
    chart.data.labels.push(t.trip);chart.data.datasets[0].data.push(t.correct);chart.update();
    k++;
  },780);
}
// build route buttons
const rdiv=document.getElementById('routes');
Object.entries(DATA).forEach(([k,d])=>{const b=document.createElement('button');b.className='rt';b.dataset.k=k;
  b.innerHTML=`<b>${d.start_label} → ${d.goal_label}</b><span>${d.city} · ${d.n} turns · ${d.store_size.toLocaleString()} vectors</span>`;
  b.onclick=()=>selectRoute(k);rdiv.appendChild(b);});
document.getElementById('learn').addEventListener('change',e=>{
  document.getElementById('mode').textContent=e.target.checked?'(RouteMind)':'(plain RAG — stays lost)';reset();});
document.getElementById('drive').onclick=drive;
document.getElementById('reset').onclick=reset;
addEventListener('resize',resize);
selectRoute('sf');requestAnimationFrame(resize);
</script></body></html>"""

html = HTML.replace("__BUNDLES__", json.dumps(BUNDLES))
open(OUT, "w").write(html)
print("wrote", OUT, f"({len(html)//1024} KB)")
