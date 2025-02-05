import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from unidecode import unidecode

# URL feedu
feed_url = "https://www.pooltechnika.cz/feed/heureka?token=5f0dac7b23e1d"

# Extrakce domény z feedu
parsed_url = urlparse(feed_url)
hostname = parsed_url.netloc
domain_name = hostname.split('.')[1]

# Stáhnutí feedu
response = requests.get(feed_url)
if response.status_code == 200:
    feed_data = response.content
    print(f"Feed z {hostname} úspěšně načten.")
else:
    print(f"Chyba při načítání feedu, status code: {response.status_code}.")
    exit()

# Načtení feedu
root = ET.fromstring(feed_data)

# Mapa kategorií (ID, nadřazená ID, název)
categories = {}  # Klíč bude tuple (název_kategorie, parent_id)
id_counter = 1  # Start ID na 1

for item in root.findall('SHOPITEM'):
    category_text = item.find('CATEGORYTEXT')
    if category_text is not None and category_text.text.strip():
        # Zpracování kategorií
        categories_list = [cat.strip() for cat in category_text.text.split('|')]
        categories_list.reverse()  # Obrácení pořadí kategorií
        parent_id = None
        for category in categories_list:
            key = (category, parent_id)  # Klíčem je tuple (název_kategorie, parent_id)
            if key not in categories:
                categories[key] = {"id": id_counter, "parent_id": parent_id, "name": category}
                id_counter += 1
            parent_id = categories[key]["id"]
    else:
        # Pokud CATEGORYTEXT chybí nebo je prázdný, přiřaď do kategorie "Další"
        key = ("Další", None)
        if key not in categories:
            categories[key] = {"id": id_counter, "parent_id": None, "name": "Další"}
            id_counter += 1

print(f"Kategorie úspěšně vyextrahovány, celkem: {len(categories)} kategorií.")

# Vytvoření XML pro Upgates
categories_xml = ET.Element("CATEGORIES", attrib={"version": "1.0"})
for (category_name, parent_id), details in categories.items():
    # Najdeme název nadřazené kategorie (parent_name), pokud existuje
    parent_name = ""
    if parent_id:
        for (parent_category_name, _), parent_details in categories.items():
            if parent_details["id"] == parent_id:
                parent_name = f"|{unidecode(parent_category_name.lower().replace(' ', '-'))}"
                break

    # CATEGORY
    category_elem = ET.SubElement(categories_xml, "CATEGORY")
    # CODE obsahuje doménu, category_name bez diakritiky, malými písmeny a s pomlčkami
    code_value = f"{domain_name}{parent_name}|{unidecode(category_name.lower().replace(' ', '-'))}"
    ET.SubElement(category_elem, "CODE").text = code_value
    ET.SubElement(category_elem, "CATEGORY_ID").text = str(details["id"])
    ET.SubElement(category_elem, "PARENT_ID").text = str(details["parent_id"]) if details["parent_id"] else ""
    ET.SubElement(category_elem, "ACTIVE_YN").text = "true"

    # DESCRIPTIONS
    decritpions_elem = ET.SubElement(category_elem, "DESCRIPTIONS")
    # DESCRIPTION CS
    decritpion_elem_cs = ET.SubElement(decritpions_elem, "DESCRIPTION", attrib={"language": "cs"})
    ET.SubElement(decritpion_elem_cs, "ACTIVE_YN").text = "true"
    ET.SubElement(decritpion_elem_cs, "NAME").text = category_name
    ET.SubElement(decritpion_elem_cs, "NAME_H1").text = category_name
    ET.SubElement(decritpion_elem_cs, "URL").text = unidecode(category_name.lower().replace(" ", "-"))
    ET.SubElement(decritpion_elem_cs, "LINK_URL").text = unidecode(category_name.lower().replace(" ", "-"))
    # SEO OPTIMIZATION
    seo_optimization_elem = ET.SubElement(category_elem, "SEO_OPTIMALIZATION")
    seo_elem = ET.SubElement(seo_optimization_elem, "SEO", attrib={"language": "cs"})
    ET.SubElement(seo_elem, "SEO_URL").text = unidecode(category_name.lower().replace(" ", "-"))
    ET.SubElement(seo_elem, "SEO_TITLE").text = f"{category_name} pro bazény – Skvělý výběr online na Poolzone.cz"
    ET.SubElement(seo_elem, "SEO_META_DESCRIPTION").text = f"{category_name} pro bazény. Nabízíme kvalitní produkty za skvělé ceny. Prohlédněte si náš výběr ještě dnes!"

print(f"XML soubor pro import kategorií vytvořen.")

# Ulož výsledný XML
output_file = f"{domain_name}_categories.xml"
tree = ET.ElementTree(categories_xml)
tree.write(output_file, encoding='utf-8', xml_declaration=True)

print(f"Feed byl úspěšně zpracován. Výstupní soubor: {output_file}.")
