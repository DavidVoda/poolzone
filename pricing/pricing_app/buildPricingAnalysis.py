import argparse
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
}


PRICING_REQUIRED_COLUMNS = [
    "product_code",
    "title",
    "url",
    "price_buy",
    "price_common",
    "price_with_vat",
    "margin_value",
    "margin_pct",
]

COMPETITOR_REQUIRED_COLUMNS = [
    "product_code",
    "competitor_name",
    "competitor_product_url",
    "note",
    "last_checked",
]


SUPPORTED_COMPETITORS = [
    "bazenonline",
    "bazeny24",
    "bazenyeshop",
    "bazenyshop",
]


def load_csv(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Soubor neexistuje: {file_path}")

    return pd.read_csv(path, encoding="utf-8-sig")


def validate_columns(df: pd.DataFrame, required_columns: list[str], file_name: str) -> None:
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(
            f"V souboru {file_name} chybí povinné sloupce: " + ", ".join(missing)
        )


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.text


def parse_price_text(text: str) -> float:
    text = text.replace("\xa0", " ")
    text = text.replace("Kč", "")
    text = text.replace(",-", "")
    text = text.strip()

    text = re.sub(r"[^0-9,\.\s]", "", text)
    text = text.replace(" ", "").replace(",", ".")

    if not text:
        raise ValueError("Nepodařilo se vyparsovat cenu z textu.")

    return float(text)


def extract_price_bazenonline(soup: BeautifulSoup) -> float:
    price_tag = soup.select_one("span.price#total-price")
    if not price_tag:
        raise ValueError("Na bazenonline.cz nebyla nalezena cena produktu.")

    data_price = price_tag.get("data-price")
    if data_price:
        return float(data_price)

    return parse_price_text(price_tag.get_text(" ", strip=True))


def extract_price_bazeny24(soup: BeautifulSoup) -> float:
    var_price = soup.select_one("input#varCena")
    if var_price:
        value = var_price.get("value")
        if value:
            return float(value)

    price_tag = soup.select_one("span.detail-shop-price#cena")
    if price_tag:
        return parse_price_text(price_tag.get_text(" ", strip=True))

    raise ValueError("Na bazeny24.cz nebyla nalezena cena produktu.")


def extract_price_bazenyeshop(soup: BeautifulSoup) -> float:
    price_tag = soup.select_one(".price-final-holder")
    if price_tag:
        return parse_price_text(price_tag.get_text(" ", strip=True))

    price_tag = soup.select_one(".price-final")
    if price_tag:
        return parse_price_text(price_tag.get_text(" ", strip=True))

    raise ValueError("Na bazenyeshop.cz nebyla nalezena cena produktu.")


def extract_price_bazenyshop(soup: BeautifulSoup) -> float:
    for script_tag in soup.find_all("script", type="application/ld+json"):
        script_text = script_tag.get_text(strip=True)
        match = re.search(r'"price"\s*:\s*"(\d+(?:\.\d+)?)"', script_text)
        if match:
            return float(match.group(1))

    price_tag = soup.select_one("span#total-price.price")
    if price_tag:
        return parse_price_text(price_tag.get_text(" ", strip=True))

    raise ValueError("Na bazenyshop.cz nebyla nalezena cena produktu.")


def extract_price_by_domain(url: str, html: str) -> float:
    soup = BeautifulSoup(html, "html.parser")
    domain = urlparse(url).netloc.lower()

    if "bazenonline.cz" in domain:
        return extract_price_bazenonline(soup)

    if "bazeny24.cz" in domain:
        return extract_price_bazeny24(soup)

    if "bazenyeshop.cz" in domain:
        return extract_price_bazenyeshop(soup)

    if "bazenyshop.cz" in domain:
        return extract_price_bazenyshop(soup)

    raise ValueError(f"Nepodporovaná doména: {domain}")


def collect_competitor_prices(competitor_df: pd.DataFrame) -> pd.DataFrame:
    results = []

    for _, row in competitor_df.iterrows():
        url = row["competitor_product_url"]
        competitor_name = row["competitor_name"]
        product_code = row["product_code"]

        print(f"Zpracovávám: {product_code} | {competitor_name}")

        try:
            html = fetch_html(url)
            price = extract_price_by_domain(url, html)

            results.append({
                "product_code": product_code,
                "competitor_name": competitor_name,
                "competitor_product_url": url,
                "competitor_price": round(price, 2),
                "collection_status": "success",
                "error_message": "",
                "collected_at": str(date.today()),
            })

        except Exception as e:
            results.append({
                "product_code": product_code,
                "competitor_name": competitor_name,
                "competitor_product_url": url,
                "competitor_price": pd.NA,
                "collection_status": "error",
                "error_message": str(e),
                "collected_at": str(date.today()),
            })

    return pd.DataFrame(results)


def build_market_stats(competitor_prices_df: pd.DataFrame) -> pd.DataFrame:
    successful_df = competitor_prices_df[
        (competitor_prices_df["collection_status"] == "success")
        & (competitor_prices_df["competitor_price"].notna())
    ].copy()

    if successful_df.empty:
        empty_columns = [
            "product_code",
            "market_min_price",
            "market_avg_price",
            "market_median_price",
            "market_max_price",
            "competitor_count",
            "cheapest_competitor",
        ] + [f"{competitor}_price" for competitor in SUPPORTED_COMPETITORS]

        return pd.DataFrame(columns=empty_columns)

    stats_df = successful_df.groupby("product_code")["competitor_price"].agg(
        market_min_price="min",
        market_avg_price="mean",
        market_median_price="median",
        market_max_price="max",
        competitor_count="count",
    ).reset_index()

    for col in [
        "market_min_price",
        "market_avg_price",
        "market_median_price",
        "market_max_price",
    ]:
        stats_df[col] = stats_df[col].round(2)

    pivot_df = successful_df.pivot_table(
        index="product_code",
        columns="competitor_name",
        values="competitor_price",
        aggfunc="first",
    ).reset_index()

    pivot_df = pivot_df.rename(
        columns={
            col: f"{col}_price"
            for col in pivot_df.columns
            if col != "product_code"
        }
    )

    for competitor in SUPPORTED_COMPETITORS:
        col = f"{competitor}_price"
        if col not in pivot_df.columns:
            pivot_df[col] = pd.NA

    cheapest_df = successful_df.sort_values(
        by=["product_code", "competitor_price"],
        ascending=[True, True],
    ).drop_duplicates(subset=["product_code"], keep="first")

    cheapest_df = cheapest_df[["product_code", "competitor_name"]].rename(
        columns={"competitor_name": "cheapest_competitor"}
    )

    stats_df = stats_df.merge(pivot_df, on="product_code", how="left")
    stats_df = stats_df.merge(cheapest_df, on="product_code", how="left")

    return stats_df


def get_price_position(row: pd.Series) -> str:
    if pd.isna(row["market_min_price"]):
        return "no_data"

    if row["price_with_vat"] < row["market_min_price"]:
        return "cheapest"

    if row["price_with_vat"] == row["market_min_price"]:
        return "lowest"

    if row["price_with_vat"] <= row["market_avg_price"]:
        return "below_avg"

    if row["price_with_vat"] <= row["market_max_price"]:
        return "above_avg"

    return "expensive"


def get_recommendation(row: pd.Series) -> str:
    if pd.isna(row["market_min_price"]):
        return "no_data"

    if row["diff_vs_min"] > 0:
        return "decrease_price"

    if row["diff_vs_min"] < 0:
        return "increase_price"

    return "keep_price"


def build_pricing_analysis(
    pricing_df: pd.DataFrame,
    competitor_prices_df: pd.DataFrame,
) -> pd.DataFrame:
    market_stats_df = build_market_stats(competitor_prices_df)

    #Starý merge, který ponechával všechny produkty z pricing_df, i když pro ně nebyly data z competitor_prices_df
    #Můžeme zkusit ponechat všechny produkty z pricing_df a doplnit data z competitor_prices_df tam, kde jsou, ale prozatím použijeme inner merge, aby v analýze byly jen produkty, pro které máme data z trhu.
    #analysis_df = pricing_df.merge(
    #    market_stats_df,
    #    on="product_code",
    #    how="left",
    #)

    analysis_df = pricing_df.merge(
        market_stats_df,
        on="product_code",
        how="inner",
    )

    analysis_df["diff_vs_min"] = (
        analysis_df["price_with_vat"] - analysis_df["market_min_price"]
    ).round(2)

    analysis_df["price_position"] = analysis_df.apply(get_price_position, axis=1)
    analysis_df["recommendation"] = analysis_df.apply(get_recommendation, axis=1)

    competitor_price_columns = [
        f"{competitor}_price"
        for competitor in SUPPORTED_COMPETITORS
    ]

    result_columns = [
        "product_code",
        "title",
        "url",
        "price_buy",
        "price_common",
        "price_with_vat",
        "margin_value",
        "margin_pct",
        "market_min_price",
        "market_avg_price",
        "market_median_price",
        "market_max_price",
        "competitor_count",
        "cheapest_competitor",
        *competitor_price_columns,
        "diff_vs_min",
        "price_position",
        "recommendation",
    ]

    for col in result_columns:
        if col not in analysis_df.columns:
            analysis_df[col] = pd.NA

    return analysis_df[result_columns].sort_values(
        by="price_with_vat",
        ascending=False,
        na_position="last",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Build pricing analysis from pricing dataset and competitor URLs."
    )
    parser.add_argument("pricing_dataset", help="Path to pricing_dataset.csv")
    parser.add_argument("competitor_urls", help="Path to competitor_urls.csv")
    parser.add_argument(
        "--output",
        default="pricing_analysis.csv",
        help="Output CSV file path",
    )

    args = parser.parse_args()

    pricing_df = load_csv(args.pricing_dataset)
    competitor_df = load_csv(args.competitor_urls)

    validate_columns(pricing_df, PRICING_REQUIRED_COLUMNS, "pricing_dataset.csv")
    validate_columns(competitor_df, COMPETITOR_REQUIRED_COLUMNS, "competitor_urls.csv")

    competitor_prices_df = collect_competitor_prices(competitor_df)
    analysis_df = build_pricing_analysis(pricing_df, competitor_prices_df)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    analysis_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Hotovo. Vytvořen soubor: {output_path}")
    print(f"Počet produktů v analýze: {len(analysis_df)}")


if __name__ == "__main__":
    main()