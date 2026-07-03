from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import MarginRuleOut, MarginRuleUpdate
from app.models import PricingRule

router = APIRouter(prefix="/api/pricing/rules", tags=["pricing"])


@router.get("", response_model=list[MarginRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return list(db.execute(select(PricingRule).order_by(PricingRule.id)).scalars())


@router.put("/{rule_id}", response_model=MarginRuleOut)
def update_rule(rule_id: int, patch: MarginRuleUpdate, db: Session = Depends(get_db)):
    rule = db.get(PricingRule, rule_id)
    if rule is None:
        raise HTTPException(404, "rule not found")
    rule.margin_pct = patch.margin_pct
    db.flush()
    db.refresh(rule)  # reflect DB-quantized margin in the response
    return rule
