"""Local-only owner console. Separate from customer authentication."""
import os, secrets, sqlite3, time, threading
from datetime import date, timedelta
from contextlib import closing
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

router = APIRouter()
ROOT = Path(__file__).resolve().parent
from database import STORE, connect
COOKIE = "kurdway_admin"
ph = PasswordHasher()
sessions = {}
attempts = []
lock = threading.Lock()

def local(request):
    if not request.client or request.client.host not in ("127.0.0.1", "::1"):
        raise HTTPException(403)
    if request.method != "GET" and request.headers.get("origin") != str(request.base_url).rstrip("/"):
        raise HTTPException(403)

def require_admin(request):
    local(request)
    token = request.cookies.get(COOKIE, "")
    with lock:
        expiry = sessions.get(token, 0)
        if expiry < time.monotonic():
            sessions.pop(token, None)
            raise HTTPException(401, "Admin login required")
    return token

def page(name):
    return HTMLResponse((ROOT / name).read_text(), headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'","Referrer-Policy":"no-referrer"})

class Login(BaseModel):
    password: str = Field(min_length=1, max_length=256)

@router.get("/admin")
def dashboard(request: Request):
    local(request)
    return page("admin.html")

@router.post("/api/admin/login")
def login(body: Login, request: Request):
    local(request)
    with lock:
        now = time.monotonic()
        attempts[:] = [t for t in attempts if now-t < 300]
        if len(attempts) >= 5:
            raise HTTPException(429, "Try again in five minutes")
        attempts.append(now)
    path = STORE / "owner.hash"
    if not path.is_file() or path.is_symlink():
        raise HTTPException(503, "Initialize the local owner first")
    try:
        ph.verify(path.read_text().strip(), body.password)
    except (VerifyMismatchError, VerificationError):
        raise HTTPException(401, "Invalid credentials")
    token = secrets.token_urlsafe(32)
    with lock:
        sessions.clear()
        sessions[token] = time.monotonic() + 1800
        attempts.clear()
    response = JSONResponse({"ok": True}, headers={"Cache-Control":"no-store"})
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=1800, path="/api/admin")
    return response

@router.post("/api/admin/logout")
def logout(request: Request):
    token = require_admin(request)
    with lock:
        sessions.pop(token, None)
    response = JSONResponse({"ok":True})
    response.delete_cookie(COOKIE, path="/api/admin")
    return response

@router.get("/api/admin/overview")
def overview(request: Request, days: int = Query(30, ge=7, le=90)):
    require_admin(request)
    with closing(connect()) as conn:
        conn.row_factory = sqlite3.Row
        counts = dict(conn.execute("SELECT plan, count(*) FROM users GROUP BY plan").fetchall())
        users = [dict(r) for r in conn.execute("SELECT id, email, role, plan, created_at, blocked, CASE WHEN email LIKE \'%@example.com\' THEN 1 ELSE 0 END AS test_account FROM users ORDER BY id DESC LIMIT 100")]
        total = conn.execute("SELECT count(*) FROM users").fetchone()[0]
        start = date.today() - timedelta(days=days-1)
        series = dict(conn.execute("SELECT date(created_at), count(*) FROM users WHERE date(created_at)>=? GROUP BY date(created_at)", (start.isoformat(),)))
        trend = [{"date": (start+timedelta(days=i)).isoformat(), "count": series.get((start+timedelta(days=i)).isoformat(),0)} for i in range(days)]
        admins = conn.execute("SELECT count(*) FROM users WHERE role='admin'").fetchone()[0]
        verified = conn.execute("SELECT count(*) FROM users WHERE email_verified_at IS NOT NULL AND email_verified_at != '' AND email NOT LIKE '%@example.com'").fetchone()[0]
        test_accounts = conn.execute("SELECT count(*) FROM users WHERE email LIKE '%@example.com'").fetchone()[0]
        events = [dict(r) for r in conn.execute("SELECT action,user_id,created_at FROM audit ORDER BY id DESC LIMIT 50")]
    from mail_delivery import settings
    try:
        mail_status = "SMTP configured (delivery unverified)" if settings() else "Local test only"
    except (OSError, ValueError, RuntimeError):
        mail_status = "Configuration error"
    return JSONResponse({"events":events,"trend":trend,"new_users":sum(p["count"] for p in trend),"admins":admins,"verified":verified,"test_accounts":test_accounts,"total":total,"free":counts.get("free",0),"premium":counts.get("premium",0),"users":users,"mode":"Local development","billing":"Not connected","mail":mail_status},headers={"Cache-Control":"no-store"})

class AccountStatus(BaseModel):
    blocked: bool

@router.post("/api/admin/users/{uid}/status")
def change_status(uid: int, body: AccountStatus, request: Request):
    require_admin(request)
    with closing(connect()) as conn, conn:
        cursor = conn.execute("UPDATE users SET blocked=? WHERE id=? AND role='user'", (int(body.blocked),uid))
        if cursor.rowcount != 1:
            raise HTTPException(404, "Customer not found")
        if body.blocked:
            conn.execute("DELETE FROM customer_sessions WHERE user_id=?", (uid,))
        conn.execute("INSERT INTO audit(action,user_id) VALUES(?,?)", ("customer_blocked" if body.blocked else "customer_unblocked",uid))
    return JSONResponse({"ok":True},headers={"Cache-Control":"no-store"})

def setup():
    import getpass
    from database import initialize
    initialize()
    path = STORE / "owner.hash"
    if path.exists():
        raise SystemExit("Owner already configured; no changes made.")
    password = getpass.getpass("Choose owner password (at least 14 characters): ")
    if len(password)<14 or len(password)>256:
        raise SystemExit("Password must be 14–256 characters.")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match.")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd,"w") as f:
        f.write(ph.hash(password))
    print("Local owner configured.")

if __name__ == "__main__":
    setup()
