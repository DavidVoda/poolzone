import pandas as pd
import xml.etree.ElementTree as ET
from unidecode import unidecode

# Načtení dat z Excelu
df = pd.read_excel('./configs/poolzone_categories.xlsx')

# Vytvoření XML pro Upgates
categories_xml = ET.Element("CATEGORIES", attrib={"version": "1.0"})

# Procházení XLSX souboru pro vytvoření XML elementů
for _, row in df.iterrows():
    # Kontrola, zda je řádek prázdný (všechny hodnoty jsou NaN nebo prázdné)
    if row.isnull().all() or all(str(v).strip() == "" for v in row):
        continue  # Přeskočí prázdné řádky

    # Vytvoření url z Názvu kategorie
    url_safe_name = unidecode(str(row['Název kategorie']).lower().replace(" ", "-"))
    # Konverze ACTIVE_YN na 1 nebo 0
    active_yn = "1" if row['ACTIVE_YN'] else "0"
    # Konverze SHOW_IN_MENU_YN na 1 nebo 0
    show_in_menu_yn = "1" if row['SHOW_IN_MENU_YN'] else "0"

    # CATEGORY
    category_elem = ET.SubElement(categories_xml, "CATEGORY")
    ET.SubElement(category_elem, "CODE").text = str(row['Kód kategorie'])
    ET.SubElement(category_elem, "CATEGORY_ID").text = str(row['ID kategorie'])
    ET.SubElement(category_elem, "PARENT_ID").text = str(row['ID nadřazené kategorie']) if pd.notna(
        row['ID nadřazené kategorie']) else ""
    ET.SubElement(category_elem, "ACTIVE_YN").text = active_yn
    ET.SubElement(category_elem, "SHOW_IN_MENU_YN").text = show_in_menu_yn

    # DESCRIPTIONS
    decritpions_elem = ET.SubElement(category_elem, "DESCRIPTIONS")
    decritpion_elem_cs = ET.SubElement(decritpions_elem, "DESCRIPTION", attrib={"language": "cs"})
    ET.SubElement(decritpion_elem_cs, "NAME").text = str(row['Název kategorie'])
    ET.SubElement(decritpion_elem_cs, "NAME_H1").text = str(row['Název kategorie'])
    ET.SubElement(decritpion_elem_cs, "DESCRIPTION_TEXT").text = str(row['DESCRIPTION_TEXT'])
    ET.SubElement(decritpion_elem_cs, "URL").text = url_safe_name
    ET.SubElement(decritpion_elem_cs, "LINK_URL").text = url_safe_name

    # SEO OPTIMIZATION
    seo_optimization_elem = ET.SubElement(category_elem, "SEO_OPTIMALIZATION")
    seo_elem = ET.SubElement(seo_optimization_elem, "SEO", attrib={"language": "cs"})
    ET.SubElement(seo_elem, "SEO_URL").text = url_safe_name
    ET.SubElement(seo_elem, "SEO_TITLE").text = str(row['SEO_TITLE'])
    ET.SubElement(seo_elem, "SEO_META_DESCRIPTION").text = str(row['SEO_META_DESCRIPTION'])
    ET.SubElement(seo_elem, "SEO_KEYWORDS").text = str(row['SEO_KEYWORDS'])

# Uložení XML do souboru
tree = ET.ElementTree(categories_xml)
tree.write("./configs/poolzone_categories.xlsx", encoding="utf-8", xml_declaration=True)

print("XML soubor pro import kategorií byl úspěšně vytvořen.")
