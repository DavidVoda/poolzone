from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import require_user
from app.api.routers import (
    auth,
    categories,
    feature_requests,
    feeds,
    jobs,
    pricing,
    products,
    suppliers,
    users,
)
from app.settings import IS_PRODUCTION, SECRET_KEY

app = FastAPI(title="Poolzone admin")

# Signed HTTP-only session cookie (holds only the user id). https_only in prod.
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    https_only=IS_PRODUCTION,
    same_site="lax",
)

# Vite dev server runs on 5173; in production the SPA is served from the same origin.
# allow_credentials so the session cookie rides cross-origin during dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth endpoints stay open (you must reach login without a session).
app.include_router(auth.router)

# Everything else requires a logged-in user in production; dev/localhost is open
# (require_user is a no-op unless POOLZONE_ENV=production).
_guard = [Depends(require_user)]
app.include_router(products.router, dependencies=_guard)
app.include_router(pricing.router, dependencies=_guard)
app.include_router(jobs.router, dependencies=_guard)
app.include_router(categories.router, dependencies=_guard)
app.include_router(suppliers.router, dependencies=_guard)
app.include_router(feeds.router, dependencies=_guard)
app.include_router(feature_requests.router, dependencies=_guard)
app.include_router(users.router)  # already gated by require_admin


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve the built SPA if present (production). No-op during API-only dev.
_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist.is_dir():
    # Serve built asset files directly...
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    # ...and fall back to index.html for client-side routes (deep links / refresh
    # on /products/1, /feed-mapping, etc). Real files under dist are served too.
    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "not found")
        candidate = _dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
