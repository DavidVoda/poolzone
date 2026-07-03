from decimal import Decimal

from app.models import PricingRule, Product
from app.pricing import load_margin_rules, resolve_margin, sale_price

RULES = {"default": Decimal("0.35"), "AK": Decimal("0.34")}


def _p(code, purchase, margin=None, coef="1.0"):
    return Product(
        code=code,
        price_purchase=Decimal(purchase),
        margin_pct=Decimal(margin) if margin is not None else None,
        coefficient=Decimal(coef),
    )


def test_explicit_margin_wins():
    assert resolve_margin(_p("AK1", "100", margin="0.45"), RULES) == Decimal("0.45")


def test_ak_prefix_falls_to_ak_rule():
    # AK prefix, no explicit margin -> AK default 0.34 (NOT the manufacturer field)
    assert resolve_margin(_p("AK1", "100"), RULES) == Decimal("0.34")


def test_non_ak_falls_to_default():
    assert resolve_margin(_p("ESPA1", "100"), RULES) == Decimal("0.35")


def test_sale_price_matches_old_formula():
    # purchase 77, margin 0.35, coef 1 -> 77 / 0.65 = 118.46
    assert sale_price(_p("ESPA1", "77", margin="0.35"), RULES) == Decimal("118.46")


def test_sale_price_applies_coefficient():
    # 100 / 0.55 * 0.995 = 180.91
    assert sale_price(_p("X1", "100", margin="0.45", coef="0.995"), RULES) == Decimal("180.91")


def test_load_margin_rules_from_db(db_session):
    db_session.add(PricingRule(scope="default", match_value=None, margin_pct=Decimal("0.35")))
    db_session.add(PricingRule(scope="manufacturer", match_value="AK", margin_pct=Decimal("0.34")))
    db_session.flush()
    rules = load_margin_rules(db_session)
    assert rules == {"default": Decimal("0.35"), "AK": Decimal("0.34")}
