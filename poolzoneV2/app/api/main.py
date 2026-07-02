from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routers import jobs, pricing, products

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


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve the built SPA if present (production). No-op during API-only dev.
_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="spa")
