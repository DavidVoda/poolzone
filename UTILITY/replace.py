import pandas as pd

# Načtení prvního Excel souboru
df1 = pd.read_excel('poolzone_categories.xlsx', engine='openpyxl')

# Načtení druhého Excel souboru
df2 = pd.read_excel('pooltechnika_categories.xlsx', engine='openpyxl')

# Převod ID kategorie na string pro porovnávání
df1['Pooltechnika ID kategorie'] = df1['Pooltechnika ID kategorie'].astype(str)
df2['ID kategorie'] = df2['ID kategorie'].astype(str)

# Funkce pro náhradu IDček
def nahradit_id(pool_ids, df2):
    id_list = pool_ids.split(';')  # Rozdělení ID podle středníku
    new_ids = [df2.loc[df2['ID kategorie'] == id.strip(), 'Název původní'].values[0] for id in id_list if id.strip() in df2['ID kategorie'].values]
    return ';'.join(new_ids)

# Aplikace funkce na celý sloupec
df1['Pooltechnika ID kategorie'] = df1['Pooltechnika ID kategorie'].apply(lambda x: nahradit_id(x, df2))

# Uložení upraveného prvního Excel souboru
df1.to_excel('poolzone_categories_replaced.xlsx', index=False, engine='openpyxl')

print(f"Pooltechnika ID kategorie bylo úspěšně nahrazeno za kódy kategorií.")
