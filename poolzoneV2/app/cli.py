from __future__ import annotations

import typer

from app.auth import hash_password
from app.db import session_scope
from app.export.upgates_xml import run_export
from app.job_run import job_run
from app.models import Supplier, User
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


@app.command()
def create_user(
    email: str,
    password: str,
    name: str = "",
    admin: bool = typer.Option(False, help="Grant the admin role (can manage users)."),
) -> None:
    """Create a login. Seed the first admin here before enabling production auth."""
    with session_scope() as session:
        if session.query(User).filter_by(email=email).first():
            typer.echo(f"User '{email}' already exists.")
            raise typer.Exit(code=1)
        session.add(
            User(
                email=email,
                name=name or email.split("@")[0],
                role="admin" if admin else "member",
                password_hash=hash_password(password),
            )
        )
    typer.echo(f"Created {'admin' if admin else 'member'} '{email}'.")


@app.command()
def set_password(email: str, password: str) -> None:
    """Reset a user's password."""
    with session_scope() as session:
        user = session.query(User).filter_by(email=email).one_or_none()
        if user is None:
            typer.echo(f"No user '{email}'.")
            raise typer.Exit(code=1)
        user.password_hash = hash_password(password)
    typer.echo(f"Password updated for '{email}'.")


if __name__ == "__main__":
    app()
