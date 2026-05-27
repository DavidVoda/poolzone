"""Category CRUD service: tree management + product linking."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from libpoolzone.storage.models import Category, ProductCategory


def create_category(
    session: Session,
    *,
    code: str,
    name_i18n: dict,
    parent_id: int | None = None,
    **extra,
) -> Category:
    category = Category(
        code=code,
        name_i18n=name_i18n,
        parent_id=parent_id,
        **extra,
    )
    session.add(category)
    session.flush()
    return category


def get_category(session: Session, category_id: int) -> Category | None:
    return session.get(Category, category_id)


def get_category_by_code(session: Session, code: str) -> Category | None:
    return session.scalars(select(Category).where(Category.code == code)).first()


def link_product(
    session: Session,
    *,
    product_id: int,
    category_id: int,
    primary_yn: bool = False,
    position: int = 0,
) -> ProductCategory:
    """Idempotent: if the link already exists, update primary_yn/position; else create."""
    existing = (
        session.query(ProductCategory)
        .filter_by(product_id=product_id, category_id=category_id)
        .one_or_none()
    )
    if existing is not None:
        existing.primary_yn = primary_yn
        existing.position = position
        session.flush()
        return existing

    link = ProductCategory(
        product_id=product_id,
        category_id=category_id,
        primary_yn=primary_yn,
        position=position,
    )
    session.add(link)
    session.flush()
    return link
