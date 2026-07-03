from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ParsedParam:
    name: str
    value: str


@dataclass
class ParsedProduct:
    code: str
    title: str | None = None
    url: str | None = None
    ean: str | None = None
    manufacturer: str | None = None
    price_purchase: Decimal | None = None  # excl VAT
    stock: int | None = None
    weight: int | None = None  # grams
    availability: str | None = None
    category_path: str | None = None  # raw CATEGORYTEXT
    image_urls: list[str] = field(default_factory=list)
    params: list[ParsedParam] = field(default_factory=list)
