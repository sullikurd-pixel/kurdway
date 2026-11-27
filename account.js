'use strict';
const translate=s=>typeof tr==='function'?tr(s):s;
const by=id=>document.getElementById(id);
let requested='';
async function post(path,data){const r=await fetch('/api/account/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!r.ok){const d=await r.json();throw Error(typeof d.detail==='string'?d.detail:'Request failed ('+r.status+')')}return r.json()}
async function load(){const r=await fetch('/api/account/me',{cache:'no-store'});by('profile').hidden=!r.ok;by('login').hidden=r.ok;by('customer-nav').hidden=!r.ok;by('logout').hidden=!r.ok;if(r.ok){const d=await r.json();by('address').textContent=d.email;by('plan').textContent='Plan: '+d.plan;await dashboard()}}
by('codeform').onsubmit=async e=>{e.preventDefault();try{requested=by('email').value;const result=await post('code',{email:requested});by('verifyform').hidden=false;by('message').textContent=result.delivery==='email'?translate('Check your email for your six-digit code.'):'Read the local test code in ~/.kurdway/test-mail/latest.txt. No email was sent.'}catch(e){by('message').textContent=e.message}};
by('verifyform').onsubmit=async e=>{e.preventDefault();try{await post('verify',{email:requested,code:by('code').value});by('code').value='';by('message').textContent='';await load()}catch(e){by('message').textContent=e.message}};
by('logout').onclick=async()=>{try{await post('logout',{});by('verifyform').hidden=true;by('activityrows').replaceChildren();by('places').replaceChildren();by('displayname').value='';by('activityform').reset();await load()}catch(e){alert(e.message)}};


const make=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el};
async function customer(path,method='GET',data){
 const opts={method,cache:'no-store'};
 if(data!==undefined){opts.headers={'Content-Type':'application/json'};opts.body=JSON.stringify(data)}
 const r=await fetch('/api/customer/'+path,opts);
 if(r.status===401){by('profile').hidden=true;by('customer-nav').hidden=true;by('logout').hidden=true;by('login').hidden=false;throw Error('Session expired. Sign in again.')}
 if(!r.ok)throw Error('Request failed ('+r.status+')');
 return r.json();
}
async function dashboard(){
 const d=await customer('dashboard');
 if(typeof applyLanguage==='function')applyLanguage(d.profile.language);
 by('welcome').textContent=d.profile.display_name?translate('Welcome, ')+d.profile.display_name:translate('Welcome to KURDWAY');
 by('displayname').value=d.profile.display_name;by('language').value=d.profile.language;
 by('trips').textContent=d.totals.trips;by('km').textContent=Number(d.totals.km||0).toFixed(2);by('elevation').textContent=d.totals.elevation;by('favorite-count').textContent=d.favorites.length;
 by('places').replaceChildren();
 for(const place of d.places){const card=make('article');const saved=d.favorites.includes(place);const b=make('button',saved?translate('Remove favorite'):translate('Save favorite'));b.onclick=()=>act(()=>customer('favorite','POST',{place,saved:!saved}));card.append(make('h3',place),b);by('places').append(card)}
 by('activityrows').replaceChildren();
 for(const a of d.activities){const row=make('tr');for(const k of ['title','activity_date','distance_km','elevation_m'])row.append(make('td',a[k]));const cell=make('td');const b=make('button',translate('Delete'));b.onclick=()=>{if(confirm(translate('Delete this activity?')))act(()=>customer('activity/'+a.id,'DELETE'))};cell.append(b);row.append(cell);by('activityrows').append(row)}
 if(!d.activities.length){const tr=make('tr'),td=make('td',translate('No activities recorded yet.'));td.colSpan=5;tr.append(td);by('activityrows').append(tr)}
}
async function act(fn){try{await fn();await dashboard();by('dashboard-message').textContent=translate('Saved.')}catch(e){by('dashboard-message').textContent=e.message;by('message').textContent=e.message}}
by('profileform').onsubmit=e=>{e.preventDefault();act(()=>customer('profile','POST',{display_name:by('displayname').value,language:by('language').value}))};
by('activityform').onsubmit=e=>{e.preventDefault();act(async()=>{await customer('activity','POST',{title:by('title').value,activity_date:by('date').value,distance_km:Number(by('distance').value),elevation_m:Number(by('gain').value)});e.target.reset()})};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('.customer-view').forEach(v=>v.hidden=v.id!==b.dataset.tab);document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===b))});

load().catch(e=>{const msg='Dashboard unavailable: '+e.message;by('message').textContent=msg;by('dashboard-message').textContent=msg;});
