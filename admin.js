'use strict';
const by=id=>document.getElementById(id);
let users=[];
function render(){const q=by('search').value.toLowerCase();by('rows').replaceChildren();for(const u of users.filter(x=>[x.email,x.role,x.plan].join(' ').toLowerCase().includes(q))){const tr=document.createElement('tr');for(const k of ['email','role','plan','created_at']){const td=document.createElement('td');td.textContent=u[k];tr.append(td)}by('rows').append(tr)}}
function signedOut(){users=[];by('rows').replaceChildren();by('panel').hidden=true;by('logout').hidden=true;by('login').hidden=false}
async function load(){const r=await fetch('/api/admin/overview',{cache:'no-store'});if(!r.ok){signedOut();return}const d=await r.json();users=d.users;for(const k of ['total','free','premium'])by(k).textContent=d[k];render();by('panel').hidden=false;by('logout').hidden=false;by('login').hidden=true}
by('form').addEventListener('submit',async e=>{e.preventDefault();by('message').textContent='';try{const r=await fetch('/api/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:by('password').value})});by('password').value='';if(!r.ok){by('message').textContent=r.status===429?'Too many attempts. Try later.':r.status===503?'Configure owner in Terminal first.':'Sign in failed.';return}await load()}catch{by('message').textContent='Connection failed.'}});
by('logout').addEventListener('click',async()=>{try{await fetch('/api/admin/logout',{method:'POST'})}finally{signedOut()}});
by('search').addEventListener('input',render);
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==b.dataset.view);document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x===b))}));
load().catch(signedOut);
