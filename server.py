"""KURDWAY local development server. Not production-ready."""
from pathlib import Path
from contextlib import asynccontextmanager
from database import initialize
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

ROOT = Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(lifespan=lifespan, title="KURDWAY", version="0.3.1-dev", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

@app.get("/api/health")
def health():
    return {"status": "ok", "project": "KURDWAY", "mode": "local-development"}

@app.get("/")
def home():
    return asset("index.html")

@app.get("/favicon.ico")
def favicon():
    return asset("favicon.svg")

@app.get("/{name}")
def asset(name: str):
    if name not in {"index.html", "style.css", "app.js", "ui.js", "favicon.svg"}:
        raise HTTPException(status_code=404)
    path = ROOT / name
    if not path.is_file() or path.is_symlink():
        raise HTTPException(status_code=404)
    return FileResponse(path, headers={"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})
