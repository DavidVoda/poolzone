"""Product CRUD service. Pure functions on top of the Product model.

Callers (importers, exporter, API) should go through these functions
rather than touching the ORM directly. This keeps invariants (e.g.
field locks) enforced in one place.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from libpoolzone.storage.models import Product


def create_product(
    session: Session,
    *,
    code: str,
    titles: dict | None = None,
    price_purchase: Decimal | None = None,
    **extra: Any,
) -> Product:
    product = Product(
        code=code,
        titles=titles or {},
        price_purchase=price_purchase,
        **extra,
    )
    session.add(product)
    session.flush()  # populate product.id without committing
    return product


def get_product(session: Session, product_id: int) -> Product | None:
    return session.get(Product, product_id)


def get_product_by_code(session: Session, code: str) -> Product | None:
    return session.scalars(select(Product).where(Product.code == code)).first()


def list_products(session: Session) -> list[Product]:
    return list(session.scalars(select(Product)))


def update_product_fields(
    session: Session,
    *,
    product_id: int,
    changes: dict[str, Any],
) -> Product:
    """Apply each (field_name -> value) pair to the product.

    Field-lock enforcement is layered on by `apply_supplier_changes` in M2;
    this function intentionally writes everything passed in.
    """
    product = session.get(Product, product_id)
    if product is None:
        raise ValueError(f"product {product_id} not found")

    for field_name, value in changes.items():
        setattr(product, field_name, value)
    session.flush()
    return product
