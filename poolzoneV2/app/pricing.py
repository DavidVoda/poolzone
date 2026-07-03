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
    # Non-default rules match on a code prefix (e.g. "AK" = Aseko, from the old script).
    for prefix, margin in rules.items():
        if prefix != "default" and product.code.startswith(prefix):
            return margin
    return rules["default"]


def raw_sale_price(product: Product, rules: dict[str, Decimal]) -> Decimal:
    """Unrounded sale price excl VAT = purchase * 1/(1-margin) * coefficient.

    The exporter needs the unrounded value to byte-match the legacy XML feed
    (which wrote full float precision). Use sale_price() for money display.
    """
    margin = resolve_margin(product, rules)
    return product.price_purchase * (_ONE / (_ONE - margin)) * product.coefficient


def sale_price(product: Product, rules: dict[str, Decimal]) -> Decimal:
    """Sale price excl VAT, rounded to cents (for display / API)."""
    return raw_sale_price(product, rules).quantize(_CENT, rounding=ROUND_HALF_UP)
