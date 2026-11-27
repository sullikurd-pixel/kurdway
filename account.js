'use strict';
const by=id=>document.getElementById(id);
let requested='';
async function post(path,data){const r=await fetch('/api/account/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!r.ok){const d=await r.json();throw Error(typeof d.detail==='string'?d.detail:'Request failed ('+r.status+')')}return r.json()}
async function load(){const r=await fetch('/api/account/me',{cache:'no-store'});by('profile').hidden=!r.ok;by('login').hidden=r.ok;if(r.ok){const d=await r.json();by('address').textContent=d.email;by('plan').textContent='Plan: '+d.plan}}
by('codeform').onsubmit=async e=>{e.preventDefault();try{requested=by('email').value;await post('code',{email:requested});by('verifyform').hidden=false;by('message').textContent='Read the local test code in ~/.kurdway/test-mail/latest.txt. No email was sent.'}catch(e){by('message').textContent=e.message}};
by('verifyform').onsubmit=async e=>{e.preventDefault();try{await post('verify',{email:requested,code:by('code').value});by('code').value='';by('message').textContent='';await load()}catch(e){by('message').textContent=e.message}};
by('logout').onclick=async()=>{try{await post('logout',{});by('verifyform').hidden=true;await load()}catch(e){alert(e.message)}};
load().catch(()=>by('message').textContent='Connection unavailable.');
