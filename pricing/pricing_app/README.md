# Pricing Tool

Streamlit aplikace pro cenovou analýzu produktů z Upgates exportu.

## Funkce

- Načtení exportu produktů z Upgates
- Analýza cen konkurence
- Výpočet marží a tržních statistik
- Úprava cen vybraných produktů
- Export CSV pro malý import do Upgates

## Struktura projektu

```
pricing/pricing_app/
  data/
    competitor_urls.csv
  app.py
  buildPricingAnalysis.py
  buildPricingDataset.py
  requirements.txt
```

## Instalace (lokálně)

```bash
cd pricing/pricing_app
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate # Mac/Linux

pip install -r requirements.txt
streamlit run app.py
```

## Použití aplikace

1. Nahraj CSV export z Upgates
2. Zkontroluj nebo uprav competitor URLs
3. Spusť pricing analýzu
4. V tabulce „Úprava cen“ označ produkty k úpravě
5. Nastav novou cenu s DPH
6. Zkontroluj náhled změn
7. Potvrď změny
8. Stáhni CSV
9. Importuj do Upgates jako malý import

## Competitor URLs

Soubor:

```
data/competitor_urls.csv
```

Formát:

```csv
product_code,competitor_name,competitor_product_url,note,last_checked
```

Podporovaní konkurenti:

- bazenonline
- bazeny24
- bazenyeshop
- bazenyshop

## Samostatné skripty

### Vytvoření pricing datasetu

```bash
python buildPricingDataset.py data/export.csv --output data/pricing_dataset.csv
```

### Vytvoření pricing analýzy

```bash
python buildPricingAnalysis.py data/pricing_dataset.csv data/competitor_urls.csv --output data/pricing_analysis.csv
```

## Streamlit Community Cloud

Main file path:

```
pricing/pricing_app/app.py
```

Dependencies:

```
pricing/pricing_app/requirements.txt
```

## Poznámky

- Importní CSV je určené pro malý import v Upgates
- Aplikace blokuje ceny pod nákupní cenou
- Výstupní CSV není nutné ukládat do repozitáře
