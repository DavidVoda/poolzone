import argparse
import re
import unicodedata
from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = [
    "[PRODUCT_CODE]",
    "[TITLE]",
    "[URL]",
    "[MANUFACTURER]",
    "[CATEGORIES]",
    "[STOCK]",
    "[WEIGHT]",
    "[PRICE_BUY]",
    "[PRICE_COMMON]",
    "[PRICE_WITH_VAT „Výchozí“]",
    "[ACTIVE_YN]",
    "[ARCHIVED_YN]",
]

def load_upgates_csv(file_path: str) -> pd.DataFrame:
    # Kontrola existence souboru a načtení CSV s správným oddělovačem a kódováním
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Soubor neexistuje: {file_path}")
    # U Upgates exportu bývá běžně ; a windows-1250
    return pd.read_csv(path, sep=";", encoding="windows-1250")

def normalize_text(text: str) -> str:
    # Normalizace textu pro lepší matching
    # Pokud je text NaN, vrátíme prázdný string
    if pd.isna(text):
        return ""

    # Odstranění diakritiky, speciálních znaků a převod na malá písmena
    text = str(text).lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def build_pricing_dataset(df: pd.DataFrame) -> pd.DataFrame:
    # 1) odfiltrujeme jen produkty, které nás teď zajímají
    filtered_df = df.copy()

    # nechceme archivované
    filtered_df = filtered_df[filtered_df["[ARCHIVED_YN]"] == 0]

    # chceme jen aktivní
    filtered_df = filtered_df[filtered_df["[ACTIVE_YN]"] == 1]

    # nechceme varianty
    if "[VARIANT_YN]" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["[VARIANT_YN]"] == 0]

    # 2) vybereme jen potřebné sloupce
    selected_columns = {
        "[PRODUCT_CODE]": "product_code",
        "[TITLE]": "title",
        "[URL]": "url",
        "[PRICE_BUY]": "price_buy",
        "[PRICE_COMMON]": "price_common",
        "[PRICE_WITH_VAT „Výchozí“]": "price_with_vat",
    }

    pricing_df = (
        filtered_df[list(selected_columns.keys())]
        .rename(columns=selected_columns)
        .copy()
    )

    # 3) převedeme čísla na správný datový typ, pokud se nepodaří převést, bude tam NaN
    numeric_columns = ["price_buy", "price_common", "price_with_vat"]
    for col in numeric_columns:
        pricing_df[col] = pd.to_numeric(pricing_df[col], errors="coerce")

    # 4) normalizace textových sloupců
    text_columns = ["product_code", "title", "url"]
    for col in text_columns:
        pricing_df[col] = pricing_df[col].fillna("").astype(str).str.strip()

    # 5) dopočítávání marže v absolutní i procentuální hodnotě zaokrouhlené na 2 desetinná místa
    pricing_df["margin_value"] = (
        pricing_df["price_common"] - pricing_df["price_buy"]).round(2)
    pricing_df["margin_pct"] = (
        (pricing_df["margin_value"] / pricing_df["price_common"] * 100).round(2)
    )
    pricing_df.loc[
        pricing_df["price_common"].isna() | (pricing_df["price_common"] == 0),
        "margin_pct"
    ] = pd.NA

    # 6) seřazení podle ceny s DPH sestupně
    pricing_df = pricing_df.sort_values(
        by="price_with_vat",
        ascending=False,
        na_position="last"
    )

    return pricing_df

def validate_columns(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            "V CSV chybí povinné sloupce: " + ", ".join(missing)
        )

def main():
    parser = argparse.ArgumentParser(description="Build pricing dataset from Upgates CSV export.")
    parser.add_argument("input_csv", help="Path to Upgates CSV export")
    parser.add_argument(
        "--output",
        default="pricing_dataset.csv",
        help="Output CSV file path"
    )
    args = parser.parse_args()

    df = load_upgates_csv(args.input_csv)
    validate_columns(df)
    pricing_df = build_pricing_dataset(df)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pricing_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Hotovo. Vytvořen soubor: {output_path}")
    print(f"Počet produktů: {len(pricing_df)}")

if __name__ == "__main__":
    main()