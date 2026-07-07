from __future__ import annotations

import typer

from app.db import session_scope
from app.export.upgates_xml import run_export
from app.job_run import job_run
from app.models import Supplier
from app.sync.pipeline import run_sync
from app.sync.suppliers import pooltechnika

app = typer.Typer(help="Poolzone middleware CLI")

# Registry: supplier code -> adapter module exposing fetch() + parse().
ADAPTERS = {pooltechnika.CODE: pooltechnika}


@app.command()
def sync(supplier_code: str) -> None:
    """Fetch a supplier feed and apply create-full / update-whitelist."""
    adapter = ADAPTERS.get(supplier_code)
    if adapter is None:
        typer.echo(f"Unknown supplier '{supplier_code}'. Known: {', '.join(ADAPTERS)}")
        raise typer.Exit(code=1)

    with session_scope() as session:
        supplier = session.query(Supplier).filter_by(code=supplier_code).one_or_none()
        if supplier is None:
            typer.echo(f"Supplier '{supplier_code}' not in DB. Seed it first.")
            raise typer.Exit(code=1)
        with job_run(session, "sync") as job:
            parsed = adapter.parse(adapter.fetch(supplier.feed_url))
            job.stats = run_sync(session, supplier, parsed)
            stats = job.stats
    typer.echo(f"Sync done: {stats}")


@app.command()
def export(out_dir: str = "feeds") -> None:
    """Render active products to Upgates XML in OUT_DIR (default: ./feeds)."""
    with session_scope() as session:
        stats = run_export(session, out_dir)
    typer.echo(f"Export done: {stats}")


if __name__ == "__main__":
    app()
