"""KURDWAY local development server. Not production-ready."""
from pathlib import Path
from contextlib import asynccontextmanager
from database import initialize
from admin import router as admin_router
from account import router as account_router
from customer import router as customer_router
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

ROOT = Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(lifespan=lifespan, title="KURDWAY", version="0.5.0-dev", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

app.include_router(admin_router)
app.include_router(account_router)
app.include_router(customer_router)

@app.get("/api/health")
def health():
    return {"status": "ok", "project": "KURDWAY", "mode": "local-development", "version": app.version}

@app.get("/")
def home():
    return asset("index.html")

@app.get("/favicon.ico")
def favicon():
    return asset("favicon.svg")

@app.get("/{name}")
def asset(name: str):
    if name not in {"index.html", "style.css", "app.js", "ui.js", "favicon.svg", "admin.css", "admin.js", "account.js", "customer.css"}:
        raise HTTPException(status_code=404)
    path = ROOT / name
    if not path.is_file() or path.is_symlink():
        raise HTTPException(status_code=404)
    return FileResponse(path, headers={"X-Content-Type-Options": "nosniff", "Referrer-Policy": "strict-origin-when-cross-origin" if name == "index.html" else "no-referrer"})
