"""Isolated OTP failure and concurrency tests; no network or live data."""
import os
import subprocess
import sys
from pathlib import Path

def test_otp_edges(tmp_path):
    script = r'''
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from server import app
import account

origin="http://localhost"
headers={"Origin":origin}
def client():
    return TestClient(app,base_url=origin,client=("127.0.0.1",12345))
def request(c,email):
    return c.post("/api/account/code",json={"email":email},headers=headers)
def verify(c,email,code):
    return c.post("/api/account/verify",json={"email":email,"code":code},headers=headers)
def broken(*args):
    raise OSError("Synthetic mail failure")
with client() as c:
    account.settings=broken
    assert request(c,"failure@example.org").status_code==503
    account.settings=lambda: {"test":True}
    account.deliver=broken
    assert request(c,"failure@example.org").status_code==503
    assert "failure@example.org" not in account.pending
    delivered={}
    account.deliver=lambda email,code,config: delivered.update({email:code})
    assert request(c,"expired@example.org").status_code==200
    with account.lock:
        p=account.pending["expired@example.org"]
        account.pending["expired@example.org"]=(p[0],time.monotonic()-1,p[2],p[3])
    assert verify(c,"expired@example.org",delivered["expired@example.org"]).status_code==401
    assert request(c,"limited@example.org").status_code==200
    assert request(c,"limited@example.org").status_code==429
    code=delivered["limited@example.org"]
    wrong="000000" if code!="000000" else "111111"
    for _ in range(5):
        assert verify(c,"limited@example.org",wrong).status_code==401
    assert verify(c,"limited@example.org",code).status_code==401

    started=threading.Event()
    release=threading.Event()
    def slow(email,code,config):
        if email=="slow@example.org":
            started.set()
            if not release.wait(10):
                raise RuntimeError("Test timeout")
    account.deliver=slow
    def call(email):
        with client() as peer:
            return request(peer,email).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        slow_future=pool.submit(call,"slow@example.org")
        try:
            assert started.wait(5)
            fast_future=pool.submit(call,"fast@example.org")
            assert fast_future.result(timeout=5)==200
        finally:
            release.set()
        assert slow_future.result(timeout=5)==200
'''
    subprocess.run([sys.executable,"-c",script],cwd=Path(__file__).resolve().parent,env=dict(os.environ,HOME=str(tmp_path)),check=True)
