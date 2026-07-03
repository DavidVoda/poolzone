from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers import categories, feeds, jobs, pricing, products, suppliers

app = FastAPI(title="Poolzone admin")

# Vite dev server runs on 5173; in production the SPA is served from the same origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(pricing.router)
app.include_router(jobs.router)
app.include_router(categories.router)
app.include_router(suppliers.router)
app.include_router(feeds.router)


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
