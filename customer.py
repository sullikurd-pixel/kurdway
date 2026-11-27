"""Private customer dashboard. Local synthetic accounts only."""
import sqlite3, time
from datetime import date
from contextlib import contextmanager, closing
from typing import Literal
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from account import COOKIE, digest, response
from admin import local
from database import connect

router = APIRouter(prefix="/api/customer")
PLACES = ("Halgurd","Sulaymaniyah","Hawraman / Uraman Takht","Sanandaj","Hakkari","Mount Nemrut (Adıyaman)","Afrin","Qamishli")

@contextmanager
def authorized(request):
    local(request)
    with closing(connect()) as conn, conn:
        conn.row_factory=sqlite3.Row
        if request.method!="GET":
            conn.execute("BEGIN IMMEDIATE")
        row=conn.execute("SELECT u.id FROM customer_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>? AND u.blocked=0 AND u.role='user'",(digest(request.cookies.get(COOKIE,"")),int(time.time()))).fetchone()
        if not row:
            raise HTTPException(401,"Sign in required")
        yield conn,row["id"]

class Profile(BaseModel):
    display_name: str = Field(max_length=60)
    language: Literal["en","ckb","ku"]="en"

class Favorite(BaseModel):
    place: str = Field(max_length=100)
    saved: bool

class Activity(BaseModel):
    title: str = Field(min_length=1,max_length=100)
    activity_date: date
    distance_km: float = Field(ge=0,le=1000,allow_inf_nan=False)
    elevation_m: int = Field(ge=0,le=30000)

@router.get("/dashboard")
def dashboard(request: Request):
    with authorized(request) as (conn,uid):
        p=conn.execute("SELECT display_name,language FROM customer_profiles WHERE user_id=?",(uid,)).fetchone()
        favorites=[r[0] for r in conn.execute("SELECT place FROM customer_favorites WHERE user_id=? ORDER BY place",(uid,))]
        activities=[dict(r) for r in conn.execute("SELECT id,title,activity_date,distance_km,elevation_m FROM customer_activities WHERE user_id=? ORDER BY activity_date DESC,id DESC LIMIT 100",(uid,))]
        totals=dict(conn.execute("SELECT count(*) AS trips,COALESCE(sum(distance_km),0) AS km,COALESCE(sum(elevation_m),0) AS elevation FROM customer_activities WHERE user_id=?",(uid,)).fetchone())
        return response({"profile":dict(p) if p else {"display_name":"","language":"en"},"places":PLACES,"favorites":favorites,"activities":activities,"totals":totals})

@router.post("/profile")
def profile(body: Profile,request: Request):
    with authorized(request) as (conn,uid):
        conn.execute("INSERT INTO customer_profiles VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name,language=excluded.language",(uid,body.display_name.strip(),body.language))
    return response({"ok":True})

@router.post("/favorite")
def favorite(body: Favorite,request: Request):
    if body.place not in PLACES:
        raise HTTPException(400,"Unknown place")
    with authorized(request) as (conn,uid):
        if body.saved:
            conn.execute("INSERT OR IGNORE INTO customer_favorites VALUES(?,?)",(uid,body.place))
        else:
            conn.execute("DELETE FROM customer_favorites WHERE user_id=? AND place=?",(uid,body.place))
    return response({"ok":True})

@router.post("/activity")
def activity(body: Activity,request: Request):
    if not body.title.strip() or body.activity_date>date.today():
        raise HTTPException(400,"Enter a valid completed activity")
    with authorized(request) as (conn,uid):
        if conn.execute("SELECT count(*) FROM customer_activities WHERE user_id=?",(uid,)).fetchone()[0]>=1000:
            raise HTTPException(409,"Local preview activity limit reached")
        conn.execute("INSERT INTO customer_activities(user_id,title,activity_date,distance_km,elevation_m) VALUES(?,?,?,?,?)",(uid,body.title.strip(),body.activity_date.isoformat(),body.distance_km,body.elevation_m))
    return response({"ok":True})

@router.delete("/activity/{activity_id}")
def delete_activity(activity_id: int,request: Request):
    with authorized(request) as (conn,uid):
        if conn.execute("DELETE FROM customer_activities WHERE id=? AND user_id=?",(activity_id,uid)).rowcount!=1:
            raise HTTPException(404)
    return response({"ok":True})
