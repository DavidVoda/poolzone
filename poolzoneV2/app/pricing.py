from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PricingRule, Product

_ONE = Decimal("1")
_CENT = Decimal("0.01")


def load_margin_rules(session: Session) -> dict[str, Decimal]:
    """Margin defaults as {"default": .., "AK": ..}. Keyed by match_value, "default" for the default scope."""
    rules: dict[str, Decimal] = {}
    for rule in session.execute(select(PricingRule)).scalars():
        key = "default" if rule.scope == "default" else rule.match_value
        rules[key] = rule.margin_pct
    return rules


def resolve_margin(product: Product, rules: dict[str, Decimal]) -> Decimal:
    if product.margin_pct is not None:
        return product.margin_pct
    # Aseko rule keys on the ITEM_ID prefix "AK", not the manufacturer field (matches old script).
    if product.code.startswith("AK") and "AK" in rules:
        return rules["AK"]
    return rules["default"]


def sale_price(product: Product, rules: dict[str, Decimal]) -> Decimal:
    """Sale price excl VAT = purchase * 1/(1-margin) * coefficient, rounded to cents."""
    margin = resolve_margin(product, rules)
    raw = product.price_purchase * (_ONE / (_ONE - margin)) * product.coefficient
    return raw.quantize(_CENT, rounding=ROUND_HALF_UP)
