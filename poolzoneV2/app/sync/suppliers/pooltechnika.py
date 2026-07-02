from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import ROUND_HALF_UP, Decimal

import requests

from app.sync.types import ParsedParam, ParsedProduct

CODE = "pooltechnika"
VAT_RATE = Decimal("0.21")


def fetch(feed_url: str) -> bytes:
    """Download the Heureka feed. Network boundary — kept trivial and mockable."""
    resp = requests.get(feed_url, timeout=60)
    resp.raise_for_status()
    return resp.content


def _text(item: ET.Element, tag: str) -> str | None:
    el = item.find(tag)
    if el is None or el.text is None:
        return None
    val = el.text.strip()
    return val or None


def _purchase_excl_vat(price_vat_text: str | None) -> Decimal | None:
    if not price_vat_text:
        return None
    incl = Decimal(price_vat_text.replace(",", ".").strip())
    excl = incl / (Decimal("1") + VAT_RATE)
    return excl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _weight_grams(item: ET.Element) -> int | None:
    for param in item.findall("PARAM"):
        name = param.find("PARAM_NAME")
        val = param.find("VAL")
        if name is not None and name.text and name.text.strip() == "Hmotnost" and val is not None:
            digits = "".join(c for c in (val.text or "") if c.isdigit())
            return int(digits) if digits else None
    return None


def _params(item: ET.Element) -> list[ParsedParam]:
    out: list[ParsedParam] = []
    for param in item.findall("PARAM"):
        name = param.find("PARAM_NAME")
        val = param.find("VAL")
        if name is not None and name.text:
            out.append(
                ParsedParam(
                    name=name.text.strip(),
                    value=(val.text or "").strip() if val is not None else "",
                )
            )
    return out


def parse(raw: bytes) -> list[ParsedProduct]:
    root = ET.fromstring(raw)
    products: list[ParsedProduct] = []
    for item in root.findall("SHOPITEM"):
        code = _text(item, "ITEM_ID")
        if not code:
            continue
        stock_text = _text(item, "stock_quantity")
        img = _text(item, "IMGURL")
        products.append(
            ParsedProduct(
                code=code,
                title=_text(item, "PRODUCTNAME"),
                url=_text(item, "URL"),
                ean=_text(item, "EAN"),
                manufacturer=_text(item, "MANUFACTURER"),
                price_purchase=_purchase_excl_vat(_text(item, "PRICE_VAT")),
                stock=int(stock_text) if stock_text is not None else None,
                weight=_weight_grams(item),
                availability=_text(item, "DELIVERY_DATE"),
                category_path=_text(item, "CATEGORYTEXT"),
                image_urls=[img] if img else [],
                params=_params(item),
            )
        )
    return products
