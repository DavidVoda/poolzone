import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import pandas as pd


# ============================================================
# NASTAVENÍ
# ============================================================

FEED_URL = "https://www.pooltechnika.cz/feed/heureka?token=5f0dac7b23e1d&customer=231"

PRICING_FILE = "produkty_cenotvorba.xlsx"
CATEGORIES_FILE = "poolzone_categories.xlsx"

OUTPUT_FILE = "poolzone_products.xml"
PRICE_REPORT_FILE = "price_changes.csv"

# Standardní požadovaná marže pro produkty bez individuálního pravidla
STANDARD_MARGIN = 0.35


# ============================================================
# POMOCNÉ FUNKCE
# ============================================================

def parse_price(value):
    """
    Bezpečně převede cenu z XML na float.
    Podporuje desetinnou čárku i tečku.
    """
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        return float(value.replace(",", "."))
    except (ValueError, TypeError):
        return None


def create_sub_element(parent, tag, text):
    """
    Vytvoří XML sub-element.
    """
    element = ET.SubElement(parent, tag)
    element.text = str(text).strip()
    return element


def get_text(shopitem, tag):
    """
    Bezpečně získá text XML elementu.
    """
    element = shopitem.find(tag)

    if element is None or element.text is None:
        return None

    return element.text.strip()


# ============================================================
# NAČTENÍ EXCELU S INDIVIDUÁLNÍ CENOTVORBOU
# ============================================================

print("Načítám individuální cenotvorbu...")

cenotvorba_df = pd.read_excel(PRICING_FILE)

codes = {}

for _, row in cenotvorba_df.iterrows():

    if pd.isna(row["Kód"]) or pd.isna(row["Koeficient"]):
        continue

    product_code = str(row["Kód"]).strip()

    try:
        coefficient = float(row["Koeficient"])
    except (ValueError, TypeError):
        print(
            f"VAROVÁNÍ: Neplatný koeficient pro produkt {product_code}. "
            f"Řádek ignorován."
        )
        continue

    codes[product_code] = coefficient

print(f"Načteno individuálních cenových pravidel: {len(codes)}")


# ============================================================
# NAČTENÍ KATEGORIÍ
# ============================================================

print("Načítám mapování kategorií...")

poolzone_df = pd.read_excel(CATEGORIES_FILE)


# ============================================================
# STAŽENÍ POOLTECHNIKA FEEDU
# ============================================================

parsed_url = urlparse(FEED_URL)
hostname = parsed_url.netloc

print(f"Stahuji feed z {hostname}...")

try:
    response = requests.get(
        FEED_URL,
        timeout=60
    )

    response.raise_for_status()

except requests.RequestException as e:

    print(f"CHYBA při stahování feedu: {e}")
    raise SystemExit(1)


feed_data = response.content

print(f"Feed z {hostname} úspěšně načten.")


# ============================================================
# PARSOVÁNÍ XML
# ============================================================

try:
    root = ET.fromstring(feed_data)

except ET.ParseError as e:

    print(f"CHYBA při parsování XML feedu: {e}")
    raise SystemExit(1)


shopitems = root.findall("SHOPITEM")

print(f"Počet produktů ve feedu: {len(shopitems)}")


# ============================================================
# VÝSTUPNÍ XML
# ============================================================

products = ET.Element(
    "PRODUCTS",
    version="1.0"
)


# ============================================================
# REPORT CEN
# ============================================================

price_report = []

stats = {
    "total": 0,
    "aseko": 0,
    "standard_35": 0,
    "individual": 0,
    "individual_fallback": 0,
    "missing_voc": 0,
    "missing_moc_aseko": 0,
}


# ============================================================
# ZPRACOVÁNÍ PRODUKTŮ
# ============================================================

for shopitem in shopitems:

    stats["total"] += 1

    product = ET.SubElement(products, "PRODUCT")

    # --------------------------------------------------------
    # ZÁKLADNÍ DATA
    # --------------------------------------------------------

    item_id = get_text(shopitem, "ITEM_ID")
    productname = get_text(shopitem, "PRODUCTNAME")

    if item_id:
        create_sub_element(product, "CODE", item_id)

    # --------------------------------------------------------
    # POPIS / NÁZEV / URL
    # --------------------------------------------------------

    descriptions = None
    description = None

    if productname:

        descriptions = ET.SubElement(
            product,
            "DESCRIPTIONS"
        )

        description = ET.SubElement(
            descriptions,
            "DESCRIPTION",
            language="cs"
        )

        create_sub_element(
            description,
            "TITLE",
            productname
        )

    url = get_text(shopitem, "URL")

    if url:

        if descriptions is None:

            descriptions = ET.SubElement(
                product,
                "DESCRIPTIONS"
            )

            description = ET.SubElement(
                descriptions,
                "DESCRIPTION",
                language="cs"
            )

        create_sub_element(
            description,
            "URL",
            url
        )

    # --------------------------------------------------------
    # OBRÁZEK
    # --------------------------------------------------------

    imgurl = get_text(shopitem, "IMGURL")

    if imgurl:

        images = ET.SubElement(
            product,
            "IMAGES"
        )

        image = ET.SubElement(
            images,
            "IMAGE"
        )

        create_sub_element(
            image,
            "URL",
            imgurl
        )

    # ========================================================
    # CENOTVORBA
    # ========================================================

    voc = parse_price(
        get_text(shopitem, "VOC")
    )

    voc_vat = parse_price(
        get_text(shopitem, "VOC_VAT")
    )

    moc = parse_price(
        get_text(shopitem, "MOC")
    )

    moc_vat = parse_price(
        get_text(shopitem, "MOC_VAT")
    )

    selling_price = None
    coefficient = None
    pricing_method = None

    # --------------------------------------------------------
    # 1. KONTROLA NÁKUPNÍ CENY
    # --------------------------------------------------------

    if voc is None or voc <= 0:

        stats["missing_voc"] += 1

        pricing_method = "CHYBÍ VOC - CENA NEIMPORTOVÁNA"

        print(
            f"VAROVÁNÍ: {item_id} | {productname} | "
            f"chybí platná VOC. Cena nebude importována."
        )

    # --------------------------------------------------------
    # 2. INDIVIDUÁLNÍ KOEFICIENT
    #
    # Excel má NEJVYŠŠÍ prioritu.
    # Platí tedy i pro produkty ASEKO (AK...).
    # --------------------------------------------------------

    elif item_id in codes:

        coefficient = codes[item_id]

        if moc is not None and moc > 0:

            calculated_price = moc * coefficient

            # Bezpečnost:
            # Koeficient nikdy nesmí vytvořit cenu
            # nižší nebo rovnou VOC.
            if calculated_price <= voc:

                selling_price = voc / (1 - STANDARD_MARGIN)

                pricing_method = (
                    "INDIVIDUÁLNÍ KOEFICIENT - "
                    "FALLBACK 35% MARŽE"
                )

                stats["individual_fallback"] += 1

                print(
                    f"POZOR: {item_id} | {productname} | "
                    f"koeficient {coefficient} by vytvořil cenu "
                    f"{calculated_price:.2f} Kč při VOC "
                    f"{voc:.2f} Kč. Použita 35% marže."
                )

            else:

                selling_price = calculated_price

                pricing_method = "MOC × INDIVIDUÁLNÍ KOEFICIENT"

                stats["individual"] += 1

        else:

            # Pokud produkt v Excelu nemá MOC,
            # použijeme bezpečný fallback 35% marže.
            selling_price = voc / (1 - STANDARD_MARGIN)

            pricing_method = (
                "CHYBÍ MOC - FALLBACK 35% MARŽE"
            )

            stats["individual_fallback"] += 1

            print(
                f"VAROVÁNÍ: {item_id} | {productname} | "
                f"produkt má individuální koeficient, ale chybí MOC. "
                f"Použita 35% marže."
            )

    # --------------------------------------------------------
    # 3. ASEKO BEZ INDIVIDUÁLNÍHO KOEFICIENTU
    #
    # Produkty AK... bez výjimky v Excelu mají přímo MOC.
    # --------------------------------------------------------

    elif item_id and item_id.upper().startswith("AK"):

        stats["aseko"] += 1

        if moc is not None and moc > 0:

            selling_price = moc

            pricing_method = "ASEKO - MOC"

        else:

            stats["missing_moc_aseko"] += 1

            pricing_method = "ASEKO - CHYBÍ MOC"

            print(
                f"VAROVÁNÍ: ASEKO produkt {item_id} | "
                f"{productname} nemá platnou MOC. "
                f"Prodejní cena nebude importována."
            )

    # --------------------------------------------------------
    # 4. STANDARDNÍ PRODUKT
    #
    # VOC / 0,65 = přesně 35% marže.
    # --------------------------------------------------------

    else:

        selling_price = voc / (1 - STANDARD_MARGIN)

        pricing_method = "STANDARD 35% MARŽE"

        stats["standard_35"] += 1

    # --------------------------------------------------------
    # FINÁLNÍ BEZPEČNOSTNÍ KONTROLA
    # --------------------------------------------------------

    if selling_price is not None:

        # Absolutní ochrana proti prodeji na/pod nákupkou.
        if selling_price <= voc:

            print(
                f"KRITICKÁ OCHRANA: {item_id} | {productname} | "
                f"výsledná cena {selling_price:.2f} <= VOC "
                f"{voc:.2f}. Přepínám na 35% marži."
            )

            selling_price = voc / (1 - STANDARD_MARGIN)

            pricing_method += " | SAFETY 35%"

        selling_price = round(
            selling_price,
            2
        )

        # ----------------------------------------------------
        # XML CENY
        # ----------------------------------------------------

        prices = ET.SubElement(
            product,
            "PRICES"
        )

        price = ET.SubElement(
            prices,
            "PRICE",
            language="cs"
        )

        # Aktuální nákupní cena bez DPH z Pooltechniky
        create_sub_element(
            price,
            "PRICE_PURCHASE",
            f"{voc:.2f}"
        )

        # Běžná prodejní cena bez DPH
        create_sub_element(
            price,
            "PRICE_COMMON",
            f"{selling_price:.2f}"
        )

        price_lists = ET.SubElement(
            price,
            "PRICELISTS"
        )

        price_list = ET.SubElement(
            price_lists,
            "PRICELIST"
        )

        # Prodejní cena bez DPH
        create_sub_element(
            price_list,
            "PRICE_ORIGINAL",
            f"{selling_price:.2f}"
        )

    # --------------------------------------------------------
    # REPORT CEN
    # --------------------------------------------------------

    margin = None

    if (
        selling_price is not None
        and selling_price > 0
        and voc is not None
    ):

        margin = (
            (selling_price - voc)
            / selling_price
        ) * 100

    price_report.append({
        "Kod": item_id,
        "Produkt": productname,
        "VOC_bez_DPH": voc,
        "VOC_s_DPH": voc_vat,
        "MOC_bez_DPH": moc,
        "MOC_s_DPH": moc_vat,
        "Koeficient": coefficient,
        "Nova_cena_bez_DPH": selling_price,
        "Nova_cena_s_DPH":
            round(selling_price * 1.21, 2)
            if selling_price is not None
            else None,
        "Marze_procent":
            round(margin, 2)
            if margin is not None
            else None,
        "Metoda": pricing_method,
    })

    # ========================================================
    # KATEGORIE
    # ========================================================

    categorytext = get_text(
        shopitem,
        "CATEGORYTEXT"
    )

    if categorytext:

        category_value = categorytext.strip()

        categoriesA = ET.SubElement(
            product,
            "CATEGORIES"
        )

        new_code = None
        parent_category = None

        for _, row in poolzone_df.iterrows():

            ids = row["Pooltechnika ID kategorie"]

            if pd.isna(ids):
                continue

            pool_ids = str(ids).split(";")

            pool_ids = [
                x.strip()
                for x in pool_ids
            ]

            if category_value in pool_ids:

                new_code = row["Kód kategorie"]

                parent_category = row[
                    "ID nadřazené kategorie"
                ]

                break

        if new_code:

            category = ET.SubElement(
                categoriesA,
                "CATEGORY"
            )

            create_sub_element(
                category,
                "CODE",
                new_code
            )

            create_sub_element(
                category,
                "PRIMARY_YN",
                "true"
            )

        # ----------------------------------------------------
        # NADŘAZENÉ KATEGORIE
        # ----------------------------------------------------

        while (
            parent_category is not None
            and not pd.isna(parent_category)
        ):

            new_code_sup = None
            next_parent_category = None

            for _, row in poolzone_df.iterrows():

                if (
                    row["ID kategorie"]
                    == parent_category
                ):

                    new_code_sup = row[
                        "Kód kategorie"
                    ]

                    next_parent_category = row[
                        "ID nadřazené kategorie"
                    ]

                    break

            if new_code_sup:

                category_parent = ET.SubElement(
                    categoriesA,
                    "CATEGORY"
                )

                create_sub_element(
                    category_parent,
                    "CODE",
                    new_code_sup
                )

                create_sub_element(
                    category_parent,
                    "PRIMARY_YN",
                    "false"
                )

            parent_category = next_parent_category

    # ========================================================
    # EAN
    # ========================================================

    # EAN z Pooltechniky záměrně NEPOSÍLÁME jako EAN,
    # protože Pooltechnika zde může mít neplatné hodnoty.
    # Původní hodnotu ale používáme jako SUPPLIER_CODE.

    ean = get_text(
        shopitem,
        "EAN"
    )

    if ean is not None:

        create_sub_element(
            product,
            "EAN",
            ""
        )

        create_sub_element(
            product,
            "SUPPLIER_CODE",
            ean
        )

    # ========================================================
    # SKLAD
    # ========================================================

    stock_quantity = get_text(
        shopitem,
        "stock_quantity"
    )

    if stock_quantity is not None:

        stock = ET.SubElement(
            product,
            "STOCK"
        )

        stock.text = stock_quantity

    # ========================================================
    # HMOTNOST
    # ========================================================

    for param in shopitem.findall("PARAM"):

        param_name = param.find(
            "PARAM_NAME"
        )

        val = param.find(
            "VAL"
        )

        if (
            param_name is not None
            and param_name.text is not None
            and val is not None
            and val.text is not None
        ):

            if param_name.text.strip() == "Hmotnost":

                weight_value = (
                    val.text
                    .strip()
                    .replace("g", "")
                    .replace(" ", "")
                )

                create_sub_element(
                    product,
                    "WEIGHT",
                    weight_value
                )

                break


# ============================================================
# ULOŽENÍ XML
# ============================================================

tree = ET.ElementTree(products)

tree.write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True
)

print("")
print(
    f"XML soubor vytvořen: {OUTPUT_FILE}"
)


# ============================================================
# ULOŽENÍ KONTROLNÍHO REPORTU
# ============================================================

report_df = pd.DataFrame(
    price_report
)

report_df.to_csv(
    PRICE_REPORT_FILE,
    index=False,
    encoding="utf-8-sig",
    sep=";"
)

print(
    f"Report cen vytvořen: {PRICE_REPORT_FILE}"
)


# ============================================================
# STATISTIKY
# ============================================================

print("")
print("============================================")
print("SOUHRN CENOTVORBY")
print("============================================")

print(
    f"Produktů celkem:              {stats['total']}"
)

print(
    f"ASEKO bez výjimky → MOC:      {stats['aseko']}"
)

print(
    f"Standard → 35% marže:         {stats['standard_35']}"
)

print(
    f"Individuální koeficient:      {stats['individual']}"
)

print(
    f"Fallback individuálních:      {stats['individual_fallback']}"
)

print(
    f"Chybějící VOC:                {stats['missing_voc']}"
)

print(
    f"ASEKO bez MOC:                {stats['missing_moc_aseko']}"
)

print("============================================")