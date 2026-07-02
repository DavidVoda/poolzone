from __future__ import annotations

import typer

from app.db import session_scope
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
        raw = adapter.fetch(supplier.feed_url)
        parsed = adapter.parse(raw)
        stats = run_sync(session, supplier, parsed)
    typer.echo(f"Sync done: {stats}")


if __name__ == "__main__":
    app()
