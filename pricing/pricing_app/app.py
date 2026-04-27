from pathlib import Path

import pandas as pd
import streamlit as st

from buildPricingDataset import build_pricing_dataset
from buildPricingAnalysis import collect_competitor_prices, build_pricing_analysis


st.set_page_config(page_title="Pricing Tool", layout="wide")

st.title("💰 Pricing analýza")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

COMPETITOR_URLS_PATH = DATA_DIR / "competitor_urls.csv"

VAT_RATE = 0.21


COLUMN_LABELS = {
    "product_code": "Kód produktu",
    "title": "Produkt",
    "url": "URL produktu",
    "price_buy": "Nákupní cena",
    "price_common": "Cena bez DPH",
    "price_with_vat": "Cena s DPH",
    "margin_value": "Marže Kč",
    "margin_pct": "Marže %",
    "market_min_price": "Nejnižší cena trhu",
    "market_avg_price": "Průměr trhu",
    "market_median_price": "Medián trhu",
    "market_max_price": "Nejvyšší cena trhu",
    "market_min_margin_value": "Marže nejnižšího Kč",
    "market_min_margin_pct": "Marže nejnižšího %",
    "competitor_count": "Počet konkurentů",
    "cheapest_competitor": "Nejlevnější konkurent",
    "bazenonline_price": "Bazenonline cena",
    "bazeny24_price": "Bazeny24 cena",
    "bazenyeshop_price": "Bazenyeshop cena",
    "bazenyshop_price": "Bazenyshop cena",
    "diff_vs_min": "Rozdíl vůči min.",
    "price_position": "Pozice ceny",
    "recommendation": "Doporučení",
    "new_price_with_vat": "Nová cena s DPH",
    "update_price": "Upravit cenu",
    "competitor_name": "Konkurent",
    "competitor_product_url": "URL konkurenta",
    "note": "Poznámka",
    "last_checked": "Poslední kontrola",
}


def build_column_config(df: pd.DataFrame) -> dict:
    return {
        col: st.column_config.Column(COLUMN_LABELS.get(col, col))
        for col in df.columns
    }


def calculate_price_without_vat(price_with_vat: pd.Series) -> pd.Series:
    return (price_with_vat / (1 + VAT_RATE)).round(2)


def calculate_margin_value(
    price_without_vat: pd.Series,
    price_buy: pd.Series,
) -> pd.Series:
    return (price_without_vat - price_buy).round(2)


def calculate_margin_pct(
    margin_value: pd.Series,
    price_without_vat: pd.Series,
) -> pd.Series:
    margin_pct = (margin_value / price_without_vat * 100).round(2)
    margin_pct = margin_pct.mask(
        price_without_vat.isna() | (price_without_vat == 0)
    )
    return margin_pct


def apply_number_formatting(
    column_config: dict,
    df: pd.DataFrame,
) -> dict:
    money_columns = [
        "price_buy",
        "price_common",
        "price_with_vat",
        "margin_value",
        "market_min_price",
        "market_avg_price",
        "market_median_price",
        "market_max_price",
        "market_min_margin_value",
        "bazenonline_price",
        "bazeny24_price",
        "bazenyeshop_price",
        "bazenyshop_price",
        "diff_vs_min",
        "new_price_with_vat",
    ]

    percent_columns = [
        "margin_pct",
        "market_min_margin_pct",
    ]

    for col in money_columns:
        if col in df.columns:
            column_config[col] = st.column_config.NumberColumn(
                COLUMN_LABELS.get(col, col),
                format="%,.2f Kč",
            )

    for col in percent_columns:
        if col in df.columns:
            column_config[col] = st.column_config.NumberColumn(
                COLUMN_LABELS.get(col, col),
                format="%,.2f %%",
            )

    return column_config


# -------------------------
# 1. Upload Upgates export
# -------------------------
st.header("1️⃣ Upgates export")

uploaded_file = st.file_uploader("Nahraj Upgates export CSV", type=["csv"])

pricing_df = None

if uploaded_file:
    upgates_df = pd.read_csv(uploaded_file, sep=";", encoding="windows-1250")
    pricing_df = build_pricing_dataset(upgates_df)

    st.success("Export byl nahrán a zpracován.")

    pricing_column_config = build_column_config(pricing_df)
    pricing_column_config = apply_number_formatting(
        pricing_column_config,
        pricing_df,
    )

    st.dataframe(
        pricing_df,
        use_container_width=True,
        column_config=pricing_column_config,
    )


# -------------------------
# 2. Competitor URLs
# -------------------------
st.header("2️⃣ Competitor URLs")

if COMPETITOR_URLS_PATH.exists():
    competitor_df = pd.read_csv(COMPETITOR_URLS_PATH, encoding="utf-8-sig")
else:
    competitor_df = pd.DataFrame(
        columns=[
            "product_code",
            "competitor_name",
            "competitor_product_url",
            "note",
            "last_checked",
        ]
    )

edited_competitors = st.data_editor(
    competitor_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config=build_column_config(competitor_df),
)

if st.button("💾 Uložit competitor URLs"):
    edited_competitors.to_csv(
        COMPETITOR_URLS_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    st.success("Competitor URLs uloženy.")


# -------------------------
# 3. Pricing analysis
# -------------------------
st.header("3️⃣ Pricing analýza")

if st.button("🚀 Spustit analýzu"):
    if pricing_df is None:
        st.error("Nejdřív nahraj Upgates export.")
    else:
        with st.spinner("Stahuji ceny konkurence a počítám analýzu..."):
            competitor_prices_df = collect_competitor_prices(edited_competitors)
            analysis_df = build_pricing_analysis(
                pricing_df,
                competitor_prices_df,
            )

        st.session_state["analysis_df"] = analysis_df

        st.success("Analýza hotová.")


# -------------------------
# 4. Editable pricing output
# -------------------------
if "analysis_df" in st.session_state:
    st.header("4️⃣ Úprava cen")

    editable_df = st.session_state["analysis_df"].copy()

    editable_df["market_min_price_without_vat"] = calculate_price_without_vat(
        editable_df["market_min_price"]
    )

    editable_df["market_min_margin_value"] = calculate_margin_value(
        editable_df["market_min_price_without_vat"],
        editable_df["price_buy"],
    )

    editable_df["market_min_margin_pct"] = calculate_margin_pct(
        editable_df["market_min_margin_value"],
        editable_df["market_min_price_without_vat"],
    )

    editable_df = editable_df.drop(columns=["market_min_price_without_vat"])

    if "new_price_with_vat" not in editable_df.columns:
        editable_df["new_price_with_vat"] = editable_df["price_with_vat"]

    if "update_price" not in editable_df.columns:
        editable_df["update_price"] = False

    editable_columns_order = [
        "update_price",
        "product_code",
        "title",
        "price_buy",
        "price_with_vat",
        "new_price_with_vat",
        "margin_value",
        "margin_pct",
        "market_min_price",
        "market_min_margin_value",
        "market_min_margin_pct",
        "market_avg_price",
        "market_median_price",
        "market_max_price",
        "diff_vs_min",
        "price_position",
        "recommendation",
        "competitor_count",
        "cheapest_competitor",
        "bazenonline_price",
        "bazeny24_price",
        "bazenyeshop_price",
        "bazenyshop_price",
        "url",
    ]

    editable_columns_order = [
        col for col in editable_columns_order if col in editable_df.columns
    ]

    editable_df = editable_df[editable_columns_order]

    disabled_columns = [
        col
        for col in editable_df.columns
        if col not in [
            "new_price_with_vat",
            "update_price",
        ]
    ]

    editable_column_config = build_column_config(editable_df)
    editable_column_config = apply_number_formatting(
        editable_column_config,
        editable_df,
    )

    editable_column_config["update_price"] = st.column_config.CheckboxColumn(
        COLUMN_LABELS["update_price"],
        default=False,
    )

    editable_column_config["new_price_with_vat"] = st.column_config.NumberColumn(
        COLUMN_LABELS["new_price_with_vat"],
        min_value=0,
        step=1,
        format="%,.2f Kč",
    )

    edited_analysis = st.data_editor(
        editable_df,
        use_container_width=True,
        num_rows="fixed",
        column_config=editable_column_config,
        disabled=disabled_columns,
    )

    st.session_state["edited_analysis_df"] = edited_analysis

    analysis_csv = edited_analysis.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="⬇️ Stáhnout pricing_analysis.csv",
        data=analysis_csv,
        file_name="pricing_analysis.csv",
        mime="text/csv",
    )

    # -------------------------
    # 5. Upgates import
    # -------------------------
    st.header("5️⃣ Import do Upgates")

    rows_to_update = edited_analysis[
        edited_analysis["update_price"] == True
    ].copy()

    if rows_to_update.empty:
        st.info("Zatím není vybraný žádný produkt k úpravě ceny.")
    else:
        st.info(f"Vybráno {len(rows_to_update)} produktů k úpravě ceny.")

        preview_df = rows_to_update[
            [
                "product_code",
                "price_buy",
                "price_with_vat",
                "new_price_with_vat",
            ]
        ].copy()

        preview_df["new_price_without_vat"] = calculate_price_without_vat(
            preview_df["new_price_with_vat"]
        )

        preview_df["price_diff"] = (
            preview_df["new_price_with_vat"] - preview_df["price_with_vat"]
        ).round(2)

        preview_df["new_margin_value"] = calculate_margin_value(
            preview_df["new_price_without_vat"],
            preview_df["price_buy"],
        )

        preview_df["new_margin_pct"] = calculate_margin_pct(
            preview_df["new_margin_value"],
            preview_df["new_price_without_vat"],
        )

        preview_df = preview_df.rename(
            columns={
                "product_code": "Produkt",
                "price_buy": "Nákupní cena",
                "price_with_vat": "Stará cena s DPH",
                "new_price_with_vat": "Nová cena s DPH",
                "new_price_without_vat": "Nová cena bez DPH",
                "price_diff": "Rozdíl",
                "new_margin_value": "Nová marže Kč",
                "new_margin_pct": "Nová marže %",
            }
        )

        preview_column_config = {
            "Nákupní cena": st.column_config.NumberColumn(
                "Nákupní cena",
                format="%,.2f Kč",
            ),
            "Stará cena s DPH": st.column_config.NumberColumn(
                "Stará cena s DPH",
                format="%,.2f Kč",
            ),
            "Nová cena s DPH": st.column_config.NumberColumn(
                "Nová cena s DPH",
                format="%,.2f Kč",
            ),
            "Nová cena bez DPH": st.column_config.NumberColumn(
                "Nová cena bez DPH",
                format="%,.2f Kč",
            ),
            "Rozdíl": st.column_config.NumberColumn(
                "Rozdíl",
                format="%,.2f Kč",
            ),
            "Nová marže Kč": st.column_config.NumberColumn(
                "Nová marže Kč",
                format="%,.2f Kč",
            ),
            "Nová marže %": st.column_config.NumberColumn(
                "Nová marže %",
                format="%,.2f %%",
            ),
        }

        st.subheader("🔍 Náhled změn cen")
        st.dataframe(
            preview_df,
            use_container_width=True,
            column_config=preview_column_config,
        )

        loss_products_df = preview_df[
            preview_df["Nová cena bez DPH"] < preview_df["Nákupní cena"]
        ]

        has_loss_products = not loss_products_df.empty

        if has_loss_products:
            st.error(
                "❌ Některé produkty mají novou prodejní cenu bez DPH nižší "
                "než nákupní cenu. Import není možné stáhnout."
            )

            st.dataframe(
                loss_products_df,
                use_container_width=True,
                column_config=preview_column_config,
            )

        st.warning(
            "⚠️ Tento soubor přepíše ceny produktů v Upgates při importu. "
            "Zkontroluj změny před stažením a importem."
        )

        confirm = st.checkbox("Potvrzuji, že report obsahuje správné ceny.")

        upgates_import_df = pd.DataFrame(
            {
                "[PRODUCT_CODE]": rows_to_update["product_code"],
                "[VARIANT_YN]": 0,
                "[IS_PRICES_WITH_VAT_YN]": 1,
                "[PRICE_ORIGINAL „Výchozí“]": rows_to_update["new_price_with_vat"],
            }
        )

        if confirm and not has_loss_products:
            st.subheader("📄 Importní soubor pro Upgates")
            st.dataframe(upgates_import_df, use_container_width=True)

            upgates_csv_string = upgates_import_df.to_csv(
                index=False,
                sep=";",
            )

            upgates_csv = upgates_csv_string.encode("utf-8-sig")

            st.download_button(
                label="⬇️ Stáhnout import do Upgates",
                data=upgates_csv,
                file_name="upgates_price_import.csv",
                mime="text/csv",
            )
        elif has_loss_products:
            st.info(
                "Oprav ceny produktů uvedených výše, aby šel importní soubor stáhnout."
            )
        else:
            st.info("Pro možnost stažení souboru potvrď checkbox výše.")