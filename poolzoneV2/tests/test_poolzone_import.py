from app.models import Category, Product, ProductCategory, ProductImage
from app.sync import poolzone

PRODUCTS_XML = """<?xml version="1.0"?>
<PRODUCTS>
  <PRODUCT>
    <CODE>AK1</CODE>
    <ACTIVE_YN>1</ACTIVE_YN>
    <MANUFACTURER>Aseko</MANUFACTURER>
    <EAN>111</EAN>
    <AVAILABILITY>Skladem</AVAILABILITY>
    <STOCK>7</STOCK>
    <WEIGHT>250</WEIGHT>
    <DESCRIPTIONS><DESCRIPTION language="cz">
      <TITLE>Feed title</TITLE>
      <SHORT_DESCRIPTION>short</SHORT_DESCRIPTION>
    </DESCRIPTION></DESCRIPTIONS>
    <CATEGORIES>
      <CATEGORY><CODE>poolzone|bazeny</CODE><PRIMARY_YN>1</PRIMARY_YN><POSITION>2</POSITION></CATEGORY>
      <CATEGORY><CODE>poolzone|unknown</CODE><PRIMARY_YN>0</PRIMARY_YN><POSITION>1</POSITION></CATEGORY>
    </CATEGORIES>
    <IMAGES><IMAGE><URL>http://img/1.jpg</URL></IMAGE></IMAGES>
    <PARAMETERS><PARAMETER><NAME language="cz">Barva</NAME><VALUE language="cz">modrá</VALUE></PARAMETER></PARAMETERS>
  </PRODUCT>
</PRODUCTS>""".encode()

CATEGORIES_XML = """<?xml version="1.0"?>
<CATEGORIES>
  <CATEGORY>
    <CODE>poolzone|bazeny</CODE><CATEGORY_ID>10</CATEGORY_ID><PARENT_ID>20</PARENT_ID>
    <DESCRIPTIONS><DESCRIPTION language="cz"><NAME>Bazeny</NAME></DESCRIPTION></DESCRIPTIONS>
    <SEO_OPTIMALIZATION><SEO language="cz"><SEO_TITLE>Bazeny SEO</SEO_TITLE>
      <SEO_META_DESCRIPTION>desc</SEO_META_DESCRIPTION></SEO></SEO_OPTIMALIZATION>
  </CATEGORY>
  <CATEGORY>
    <CODE>poolzone|root</CODE><CATEGORY_ID>20</CATEGORY_ID><PARENT_ID></PARENT_ID>
    <DESCRIPTIONS><DESCRIPTION language="cz"><NAME>Root</NAME></DESCRIPTION></DESCRIPTIONS>
  </CATEGORY>
</CATEGORIES>""".encode()


def _run_cats(db, whitelist):
    return poolzone.import_categories(db, CATEGORIES_XML, whitelist)


def test_category_import_creates_and_wires_parents(db_session):
    stats = _run_cats(db_session, poolzone.CATEGORY_FIELDS)
    assert stats["created"] == 2
    child = db_session.query(Category).filter_by(upgates_code="poolzone|bazeny").one()
    root = db_session.query(Category).filter_by(upgates_code="poolzone|root").one()
    assert child.parent_id == root.id
    assert child.seo_title == "Bazeny SEO"


def test_category_update_respects_whitelist(db_session):
    _run_cats(db_session, poolzone.CATEGORY_FIELDS)
    cat = db_session.query(Category).filter_by(upgates_code="poolzone|bazeny").one()
    cat.name = "OWNER EDIT"
    db_session.flush()
    # Re-run with name NOT whitelisted.
    _run_cats(db_session, ["seo_title"])
    cat = db_session.query(Category).filter_by(upgates_code="poolzone|bazeny").one()
    assert cat.name == "OWNER EDIT"  # not overwritten


def test_product_import_full_create(db_session):
    _run_cats(db_session, poolzone.CATEGORY_FIELDS)
    stats = poolzone.import_products(db_session, PRODUCTS_XML, poolzone.PRODUCT_FIELDS)
    assert stats["created"] == 1
    p = db_session.query(Product).filter_by(code="AK1").one()
    assert p.title == "Feed title"
    assert p.short_description == "short"
    assert p.manufacturer == "Aseko"
    assert p.stock == 7
    assert p.active is True
    assert db_session.query(ProductImage).filter_by(product_id=p.id).count() == 1
    # Only the known category is linked; unknown code is skipped.
    links = db_session.query(ProductCategory).filter_by(product_id=p.id).all()
    assert len(links) == 1
    assert links[0].primary_yn is True


def test_product_update_respects_whitelist(db_session):
    _run_cats(db_session, poolzone.CATEGORY_FIELDS)
    poolzone.import_products(db_session, PRODUCTS_XML, poolzone.PRODUCT_FIELDS)
    p = db_session.query(Product).filter_by(code="AK1").one()
    p.title = "OWNER EDIT"
    db_session.flush()
    # Re-run with title NOT whitelisted but stock whitelisted.
    stats = poolzone.import_products(db_session, PRODUCTS_XML, ["stock"])
    assert stats["updated"] == 1
    p = db_session.query(Product).filter_by(code="AK1").one()
    assert p.title == "OWNER EDIT"  # not overwritten
    assert p.stock == 7  # whitelisted
