"""Regression tests using a temporary home; no real SMTP or customer data."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

def test_isolated_regression(tmp_path):
    env=dict(os.environ,HOME=str(tmp_path))
    script=r'''
from pathlib import Path
import sqlite3
from fastapi.testclient import TestClient
from server import app
from admin import STORE, ph
from backup import backup
import account

origin="http://localhost"
headers={"Origin":origin}
# Explicit ASGI peer, rather than accepting a 403 as a successful auth test.
with TestClient(app,base_url=origin,client=("127.0.0.1",12345)) as c:
    assert c.get("/api/health").status_code==200
    assert c.get("/api/admin/overview").status_code==401
    assert c.get("/api/customer/dashboard").status_code==401
    assert c.post("/api/account/code",json={"email":"bad"},headers=headers).status_code==422
    assert c.post("/api/account/code",json={"email":"hiker@example.com"},headers={"Origin":"https://invalid.example"}).status_code==403
    for path in ("/database.py","/smtp.json","/owner.hash","/backup.py","/.gitignore"):
        assert c.get(path).status_code==404
    for path in ("/","/account","/admin","/account.js","/customer-language.js","/brand-logo"):
        assert c.get(path).status_code==200
    # Mock email delivery, but use the real authentication flow.
    delivered=[]
    account.settings=lambda: {"test":True}
    account.deliver=lambda email,code,config: delivered.append((email,code))
    account.welcome=lambda email,config: None
    def sign_in(email):
        assert c.post("/api/account/code",json={"email":email},headers=headers).status_code==200
        code=delivered[-1][1]
        wrong="000000" if code!="000000" else "111111"
        assert c.post("/api/account/verify",json={"email":email,"code":wrong},headers=headers).status_code==401
        assert c.post("/api/account/verify",json={"email":email,"code":code},headers=headers).status_code==200
        assert c.post("/api/account/verify",json={"email":email,"code":code},headers=headers).status_code==401
    sign_in("first@example.org")
    assert c.get("/api/account/me").json()["email"]=="first@example.org"
    assert c.post("/api/customer/profile",json={"display_name":"QA","language":"ckb"},headers=headers).status_code==200
    assert c.post("/api/customer/favorite",json={"place":"Halgurd","saved":True},headers=headers).status_code==200
    activity={"title":"QA hike","activity_date":"2020-01-01","distance_km":4.5,"elevation_m":120}
    assert c.post("/api/customer/activity",json=activity,headers=headers).status_code==200
    assert c.post("/api/customer/activity",json={**activity,"distance_km":-1},headers=headers).status_code==422
    d=c.get("/api/customer/dashboard").json()
    assert d["profile"]["language"]=="ckb" and d["favorites"]==["Halgurd"]
    assert d["totals"]=={"trips":1,"km":4.5,"elevation":120}
    aid=d["activities"][0]["id"]
    assert c.post("/api/account/logout",json={},headers=headers).status_code==200
    assert c.get("/api/customer/dashboard").status_code==401
    sign_in("second@example.org")
    assert c.get("/api/customer/dashboard").json()["totals"]["trips"]==0
    assert c.delete(f"/api/customer/activity/{aid}",headers=headers).status_code==404
    (STORE/"owner.hash").write_text(ph.hash("Synthetic-QA-password-123"))
    assert c.post("/api/admin/login",json={"password":"Synthetic-QA-password-123"},headers=headers).status_code==200
    users=c.get("/api/admin/overview").json()["users"]
    uid=next(u["id"] for u in users if u["email"]=="second@example.org")
    assert c.post(f"/api/admin/users/{uid}/status",json={"blocked":True},headers=headers).status_code==200
    assert c.get("/api/customer/dashboard").status_code==401
    copy=backup(STORE/"development.sqlite3",STORE/"backups")
    with sqlite3.connect(copy) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()==("ok",)
        assert db.execute("SELECT count(*) FROM users").fetchone()==(2,)
'''
    subprocess.run([sys.executable,"-c",script],cwd=Path(__file__).resolve().parent,env=env,check=True)
