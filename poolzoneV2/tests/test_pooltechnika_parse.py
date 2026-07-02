from decimal import Decimal
from pathlib import Path

from app.sync.suppliers.pooltechnika import parse

FIXTURE = (Path(__file__).parent / "fixtures" / "pooltechnika_sample.xml").read_bytes()


def test_parse_returns_all_items():
    products = parse(FIXTURE)
    assert len(products) == 2


def test_parse_maps_first_item_fields():
    first = parse(FIXTURE)[0]
    assert first.code == "AK13327"
    assert first.title == "OXY Pure Ag 5L"
    assert first.url == "https://www.pooltechnika.cz/oxy-pure-ag-5l"
    assert first.ean == "8594000000017"
    assert first.manufacturer == "Aseko"
    assert first.stock == 7
    assert first.category_path == "Chemie | Kyslíková"
    assert first.image_urls == ["https://img.pooltechnika.cz/oxy5l.jpg"]


def test_parse_computes_purchase_price_excl_vat():
    # 1210,00 incl 21% VAT -> 1000.00 excl VAT
    first = parse(FIXTURE)[0]
    assert first.price_purchase == Decimal("1000.00")


def test_parse_extracts_weight_grams_from_param():
    first = parse(FIXTURE)[0]
    assert first.weight == 5200


def test_parse_keeps_all_params():
    first = parse(FIXTURE)[0]
    names = {p.name for p in first.params}
    assert names == {"Hmotnost", "Objem"}


def test_parse_handles_missing_optional_fields():
    second = parse(FIXTURE)[1]
    assert second.code == "20031-14"
    assert second.url is None
    assert second.manufacturer is None
    assert second.image_urls == []
    assert second.weight is None
    assert second.stock == 0
