from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import (
    CategoryCreate,
    CategoryMappingOut,
    CategoryMappingUpdate,
    CategoryOut,
    CategoryUpdate,
)
from app.models import Category, ProductCategory, SupplierCategoryMap

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return list(db.execute(select(Category).order_by(Category.id)).scalars())


@router.get("/mappings", response_model=list[CategoryMappingOut])
def list_mappings(db: Session = Depends(get_db), category_id: int | None = None):
    stmt = select(SupplierCategoryMap).order_by(SupplierCategoryMap.supplier_path)
    if category_id is not None:
        stmt = stmt.where(SupplierCategoryMap.category_id == category_id)
    return list(db.execute(stmt).scalars())


@router.patch("/mappings/{mapping_id}", response_model=CategoryMappingOut)
def update_mapping(mapping_id: int, patch: CategoryMappingUpdate, db: Session = Depends(get_db)):
    mapping = db.get(SupplierCategoryMap, mapping_id)
    if mapping is None:
        raise HTTPException(404, "mapping not found")
    mapping.category_id = patch.category_id
    db.flush()
    return mapping


@router.post("", response_model=CategoryOut)
def create_category(body: CategoryCreate, db: Session = Depends(get_db)):
    category = Category(name=body.name, parent_id=body.parent_id)
    db.add(category)
    db.flush()
    return category


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, patch: CategoryUpdate, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(404, "category not found")
    for field, value in patch.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.flush()
    return category


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(404, "category not found")
    in_use = (
        db.execute(select(func.count()).where(Category.parent_id == category_id)).scalar_one()
        + db.execute(
            select(func.count()).where(ProductCategory.category_id == category_id)
        ).scalar_one()
        + db.execute(
            select(func.count()).where(SupplierCategoryMap.category_id == category_id)
        ).scalar_one()
    )
    if in_use:
        raise HTTPException(409, "category has children, products or mappings")
    db.delete(category)
    db.flush()
    return {"deleted": category_id}
