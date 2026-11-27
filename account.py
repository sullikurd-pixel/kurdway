"""Local test-account OTP flow. No real email delivery or production use."""
import hashlib, hmac, secrets, threading, time, sqlite3, os
from contextlib import closing
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
from admin import STORE, local, page

router = APIRouter()
COOKIE = "kurdway_customer"
key = secrets.token_bytes(32)
pending = {}
requests = []
guesses = []
lock = threading.Lock()

class Email(BaseModel):
    email: EmailStr

class Verify(Email):
    code: str = Field(pattern=r"^[0-9]{6}$")

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def otp_digest(email, code):
    return hmac.new(key, (email+":"+code).encode(), hashlib.sha256).digest()

def test_email(value):
    email = str(value).lower()
    # Use a reserved test subdomain accepted by email-validator.
    if not email.endswith("@example.com"):
        raise HTTPException(400, "Local preview: use an example.com test address only")
    return email

def response(data):
    return JSONResponse(data, headers={"Cache-Control":"no-store"})

@router.get("/account")
def account(request: Request):
    local(request)
    return page("account.html")

@router.post("/api/account/code")
def request_code(body: Email, request: Request):
    local(request)
    email = test_email(body.email)
    now = time.monotonic()
    with lock:
        requests[:] = [t for t in requests if now-t<600]
        for k in list(pending):
            if pending[k][1]<=now:
                del pending[k]
        if len(requests)>=10 or (email in pending and now-pending[email][3]<60):
            raise HTTPException(429, "Wait before requesting another code")
        requests.append(now)
        code = f"{secrets.randbelow(1000000):06d}"
        pending[email] = (otp_digest(email,code),now+300,0,now)
        # Local preview only; never expose codes in API responses.
        folder = STORE / "test-mail"
        folder.mkdir(mode=0o700, exist_ok=True)
        if folder.is_symlink():
            raise HTTPException(503)
        os.chmod(folder,0o700)
        path = folder / "latest.txt"
        fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,"w") as f:
            f.write("LOCAL TEST ONLY\n"+email+"\n"+code+"\nExpires in 5 minutes.\n")
    return response({"ok":True,"delivery":"local-test-file"})

@router.post("/api/account/verify")
def verify(body: Verify, request: Request):
    local(request)
    email = test_email(body.email)
    now = time.monotonic()
    with lock:
        guesses[:] = [t for t in guesses if now-t<600]
        if len(guesses)>=30:
            raise HTTPException(429,"Try later")
        guesses.append(now)
        p = pending.get(email)
        if not p or p[1]<=now or p[2]>=5:
            raise HTTPException(401,"Invalid or expired code")
        if not hmac.compare_digest(p[0],otp_digest(email,body.code)):
            pending[email]=(p[0],p[1],p[2]+1,p[3])
            raise HTTPException(401,"Invalid or expired code")
        del pending[email]
    token = secrets.token_urlsafe(32)
    with closing(sqlite3.connect(STORE/"development.sqlite3")) as conn, conn:
        conn.execute("INSERT INTO users(email,email_verified_at) VALUES(?,CURRENT_TIMESTAMP) ON CONFLICT(email) DO NOTHING",(email,))
        uid, role, blocked = conn.execute("SELECT id,role,blocked FROM users WHERE email=?",(email,)).fetchone()
        if blocked or role!="user":
            raise HTTPException(403,"Account unavailable")
        conn.execute("DELETE FROM customer_sessions WHERE expires<=? OR user_id=?",(int(time.time()),uid))
        conn.execute("INSERT INTO customer_sessions VALUES(?,?,?)",(digest(token),uid,int(time.time())+3600))
        conn.execute("INSERT INTO audit(action,user_id) VALUES('customer_login',?)",(uid,))
    result=response({"ok":True})
    result.set_cookie(COOKIE,token,httponly=True,samesite="strict",max_age=3600,path="/api/account")
    return result

@router.get("/api/account/me")
def me(request: Request):
    local(request)
    with closing(sqlite3.connect(STORE/"development.sqlite3")) as conn:
        conn.row_factory=sqlite3.Row
        row=conn.execute("SELECT u.email,u.plan,u.role FROM customer_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>? AND u.blocked=0 AND u.role='user'",(digest(request.cookies.get(COOKIE,"")),int(time.time()))).fetchone()
    if not row:
        raise HTTPException(401)
    return response(dict(row))

@router.post("/api/account/logout")
def logout(request: Request):
    local(request)
    with closing(sqlite3.connect(STORE/"development.sqlite3")) as conn, conn:
        conn.execute("DELETE FROM customer_sessions WHERE token_hash=?",(digest(request.cookies.get(COOKIE,"")),))
    result=response({"ok":True})
    result.delete_cookie(COOKIE,path="/api/account")
    return result
