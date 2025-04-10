import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from unidecode import unidecode
import pandas as pd

# Načtení Excel souboru pro cenotvorbu
cenotvorba_df = pd.read_excel('produkty_cenotvorba.xlsx')

# Kód produktů, na které neplatí sleva a mají svůj vlastní koeficient
codes = {}
for index, row in cenotvorba_df.iterrows():
    product_code = str(row['Kód']).strip()
    coefficient = float(row['Koeficient'])
    codes[product_code] = coefficient

# Načtení Excel souboru a odstranění prázdných řádků
poolzone_df = pd.read_excel('poolzone_categories.xlsx')

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

# PRODUCTS
# Vytvoření kořenového elementu pro výstupní XML
products = ET.Element('PRODUCTS', version='1.0')

# Funkce pro vytvoření sub-elementů s textem
def create_sub_element(parent, tag, text):
    element = ET.SubElement(parent, tag)
    element.text = str(text).strip()
    return element

# Iterace přes každý SHOPITEM v input XML
for shopitem in root.findall('SHOPITEM'):
    # Vytvoření elementu PRODUCT
    product = ET.SubElement(products, 'PRODUCT')

    # Mapování ITEM_ID na CODE
    item_id = shopitem.find('ITEM_ID')
    if item_id is not None:
        create_sub_element(product, 'CODE', item_id.text)

    # Mapování PRODUCTNAME na DESCRIPTIONS/DESCRIPTION/TITLE
    productname = shopitem.find('PRODUCTNAME')
    if productname is not None:
        descriptions = ET.SubElement(product, 'DESCRIPTIONS')
        description = ET.SubElement(descriptions, 'DESCRIPTION', language='cs')
        create_sub_element(description, 'TITLE', productname.text)

    ## Po konzultaci s Jonášem zatím odebíráme (pravděpodobně na furt)
    ## Mapování DESCRIPTION na DESCRIPTIONS/DESCRIPTION/LONG_DESCRIPTION
    #description_text = shopitem.find('DESCRIPTION')
    #if description_text is not None:
    #    if 'descriptions' not in locals():
    #        descriptions = ET.SubElement(product, 'DESCRIPTIONS')
    #        description = ET.SubElement(descriptions, 'DESCRIPTION', language='cs')
    #    create_sub_element(description, 'LONG_DESCRIPTION', description_text.text)

    # Mapování URL na DESCRIPTIONS/DESCRIPTION/URL
    url = shopitem.find('URL')
    if url is not None:
        if 'descriptions' not in locals():
            descriptions = ET.SubElement(product, 'DESCRIPTIONS')
            description = ET.SubElement(descriptions, 'DESCRIPTION', language='cs')
        create_sub_element(description, 'URL', url.text)

    # Mapování IMGURL na IMAGES/IMAGE/URL
    imgurl = shopitem.find('IMGURL')
    if imgurl is not None:
        images = ET.SubElement(product, 'IMAGES')
        image = ET.SubElement(images, 'IMAGE')
        create_sub_element(image, 'URL', imgurl.text)

    # Cenotvorba
    price_vat = shopitem.find('PRICE_VAT')
    item_id = shopitem.find('ITEM_ID')
    if price_vat is not None:
        realPrice_discount = 0.12
        aseko_discount = 0.32
        others_discount = 0.45
        tax_rate = 0.21
        
        price_vat =  float(price_vat.text.replace(',','.'))

        if item_id.text.startswith("AK"):
            price_without_vat = price_vat / (1 + tax_rate)
            price_purchase = price_without_vat * ((1 - aseko_discount) * (1 + tax_rate))
            # Produkt v codes z produkty_cenotvorba.xsls - tedy produkt s přirážkou nebo bez slevy 
            # U produktů z Aseka ale není sleva, takže jen s přirážkou
            if item_id.text in codes:
                price_vat = price_vat * codes[item_id.text]
        else:
            price_without_vat = price_vat / (1 + tax_rate)
            price_purchase = price_without_vat * ((1 - others_discount) * (1 + tax_rate))
            # Produkt v codes z produkty_cenotvorba.xsls - tedy produkt s přirážkou nebo bez slevy
            if item_id.text in codes:
                price_vat = price_vat * codes[item_id.text]
            else:
                price_vat = price_vat * (1 - realPrice_discount)

        prices = ET.SubElement(product, 'PRICES')
        price = ET.SubElement(prices, 'PRICE', language='cs')
        create_sub_element(price, 'PRICE_PURCHASE', price_purchase)
        price_lists = ET.SubElement(price, 'PRICELISTS')
        price_list = ET.SubElement(price_lists, 'PRICELIST')
        create_sub_element(price_list, 'PRICE_ORIGINAL', price_vat)

    # Mapování CATEGORYTEXT na CATEGORIES/CATEGORY/CODE
    categorytext = shopitem.find('CATEGORYTEXT')
    if categorytext is not None:
        category_value = categorytext.text.strip()
        categoriesA = ET.SubElement(product, 'CATEGORIES')

        new_code = None
        parent_category = None
        for index, row in poolzone_df.iterrows():
            ids = row['Pooltechnika ID kategorie']
            pool_ids = str(ids).split(';') if ids else []
            if category_value in pool_ids:
                new_code = row['Kód kategorie']
                parent_category = row['ID nadřazené kategorie']
                break

        if new_code:
            category = ET.SubElement(categoriesA, 'CATEGORY')
            create_sub_element(category, 'CODE', new_code)
            create_sub_element(category, 'PRIMARY_YN', 'true')

        # Iterativně přidat nadřazené kategorie
        while parent_category:
            new_code_sup = None
            next_parent_category = None

            for index, row in poolzone_df.iterrows():
                if row['ID kategorie'] == parent_category:
                    new_code_sup = row['Kód kategorie']
                    next_parent_category = row['ID nadřazené kategorie']
                    break

            if new_code_sup:
                category_parent = ET.SubElement(categoriesA, 'CATEGORY')
                create_sub_element(category_parent, 'CODE', new_code_sup)
                create_sub_element(category_parent, 'PRIMARY_YN', 'false')

            # Přejít na další nadřazenou kategorii
            parent_category = next_parent_category

    ## Po konzultaci s Jonášem bude všude null
    ## Protože EAN buď není nebo nemá správný formát a rozbíjí to srovnávače (Google Merchant, Zbozi.cz atd.)
    ## Mapování EAN na EAN
    #ean = shopitem.find('EAN')
    #if ean is not None:
        create_sub_element(product, 'EAN', '')

    # Mapování stock_quantity na STOCK/AMOUNT
    stock_quantity = shopitem.find('stock_quantity')
    if stock_quantity is not None:
        stock = ET.SubElement(product, 'STOCK')
        stock.text = stock_quantity.text

    ## DELIVERY_DATE je vždy 0 nebo null
    ## Mapování DELIVERY_DATE na AVAILABILITY
    #delivery_date = shopitem.find('DELIVERY_DATE')
    #if delivery_date is not None:
    #    create_sub_element(product, 'AVAILABILITY', delivery_date.text)

    ## Po konzultaci s Jonášem zatím odebíráme (pravděpodobně na furt)
    ## Mapování PARAM na PARAMETERS/PARAMETER
    #params = shopitem.findall('PARAM')
    #if params:
    #    parameters = ET.SubElement(product, 'PARAMETERS')
    #    for param in params:
    #        parameter = ET.SubElement(parameters, 'PARAMETER')
    #        param_name = param.find('PARAM_NAME')
    #        param_value = param.find('VAL')
    #        if param_name is not None and param_value is not None:
    #            create_sub_element(parameter, 'NAME', param_name.text)
    #            create_sub_element(parameter, 'VALUE', param_value.text)

# Zápis výstupního XML do souboru
output_file = 'poolzone_products.xml'
tree = ET.ElementTree(products)
tree.write(output_file, encoding='utf-8', xml_declaration=True)

print(f'XML soubor pro import produktů byl úspěšně vytvořen. Výstupní soubor XML: {output_file}')