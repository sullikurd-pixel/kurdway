'use strict';
const by=id=>document.getElementById(id);
let users=[];
const node=(tag,value)=>{const e=document.createElement(tag);if(value!==undefined)e.textContent=value;return e};
function render(){const q=by('search').value.toLowerCase();by('rows').replaceChildren();const matches=users.filter(x=>[x.email,x.role,x.plan].join(' ').toLowerCase().includes(q));by('results').textContent=matches.length+' matching accounts';for(const u of matches){const tr=document.createElement('tr');for(const k of ['email','role','plan','created_at']){const td=document.createElement('td');td.textContent=u[k];tr.append(td)}by('rows').append(tr)}}
function signedOut(){users=[];by('rows').replaceChildren();by('panel').hidden=true;by('logout').hidden=true;by('login').hidden=false}
async function load(){const r=await fetch('/api/admin/overview?days='+encodeURIComponent(by('period').value),{cache:'no-store'});if(!r.ok){signedOut();return}const d=await r.json();users=d.users;for(const k of ['total','free','premium','verified','admins','new_users'])by(k).textContent=d[k];drawAnalytics(d);render();by('panel').hidden=false;by('logout').hidden=false;by('login').hidden=true}
by('form').addEventListener('submit',async e=>{e.preventDefault();by('message').textContent='';try{const r=await fetch('/api/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:by('password').value})});by('password').value='';if(!r.ok){by('message').textContent=r.status===429?'Too many attempts. Try later.':r.status===503?'Configure owner in Terminal first.':'Sign in failed.';return}await load()}catch{by('message').textContent='Connection failed.'}});
by('logout').addEventListener('click',async()=>{try{await fetch('/api/admin/logout',{method:'POST'})}finally{signedOut()}});
by('search').addEventListener('input',render);
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==b.dataset.view);document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x===b))}));
load().catch(signedOut);

function drawAnalytics(d){
  by('share').textContent=d.total?(100*d.premium/d.total).toFixed(1)+'%':'—';
  const chart=by('trend');chart.replaceChildren();
  const max=Math.max(1,...d.trend.map(p=>p.count));
  const ns='http://www.w3.org/2000/svg', svg=document.createElementNS(ns,'svg');
  svg.setAttribute('viewBox','0 0 720 220');svg.setAttribute('role','img');
  svg.setAttribute('aria-label','Daily registrations, '+d.new_users+' in selected period');
  const add=(tag,attrs,value)=>{const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(value!==undefined)e.textContent=value;svg.append(e);return e};
  for(let j=0;j<=4;j++){let y=20+j*40;add('line',{x1:45,y1:y,x2:705,y2:y,stroke:'#dbe4dc'});add('text',{x:37,y:y+4,'text-anchor':'end',fill:'#52675a','font-size':11},(max*(4-j)/4).toFixed(max>=4?0:2))}
  const step=660/d.trend.length;
  d.trend.forEach((p,i)=>{const h=160*p.count/max;const bar=add('rect',{x:45+i*step+1,y:180-h,width:Math.max(1,step-2),height:h,fill:'#287654',rx:2});const label=document.createElementNS(ns,'title');label.textContent=p.date+': '+p.count;bar.append(label)});
  add('text',{x:45,y:205,fill:'#52675a','font-size':12},d.trend[0].date);add('text',{x:705,y:205,'text-anchor':'end',fill:'#52675a','font-size':12},d.trend.at(-1).date);chart.append(svg);
  by('range').textContent=d.new_users===0?'No registrations in this period.':d.new_users+' registrations in this period.';
  const plans=by('plans');plans.replaceChildren();for(const k of ['free','premium']){const row=node('div');row.className='planrow';row.append(node('span',k+' · '+d[k]));const progress=node('progress');progress.max=Math.max(1,d.total);progress.value=d[k];progress.setAttribute('aria-label',k+' accounts');row.append(progress);plans.append(row)}
}
async function refresh(){try{await load();by('panelstatus').textContent='Data refreshed.'}catch{by('panelstatus').textContent='Could not refresh data.'}}
by('period').addEventListener('change',refresh);
by('refresh').addEventListener('click',refresh);
