#!/usr/bin/env python3
"""
Poolzone Description Generator
Reads the Upgates export XML, generates Czech product descriptions via Claude API,
and writes a minimal Upgates import XML containing only CODE + DESCRIPTIONS.

Usage:
    python descriptionGenerator/generate_descriptions.py
"""

import io
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import anthropic

# Optional dependencies — both used only for PDF extraction
try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
INPUT_XML = SCRIPT_DIR / "poolzoneData" / "export-products-clRJc2OI9n.xml"
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_XML = OUTPUT_DIR / "descriptions_import.xml"

# ---------------------------------------------------------------------------
# System prompt — cached across all 156 API calls
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Jsi odborný copywriter e-shopu Poolzone.cz specializovaný na bazénové příslušenství.
Píšeš profesionální produktové popisy v češtině. Tvůj styl je informativní, přátelský
a zaměřený na přínosy pro zákazníka.

════════════════════════════════════════
ŠABLONA POPISU
════════════════════════════════════════

Každý popis se skládá ze dvou částí:

──────────────────────────────────────
SHORT_DESCRIPTION  (krátký popis)
──────────────────────────────────────
• 2–3 věty, prostý text — BEZ HTML
• Shrnutí: co produkt je, klíčová technologie nebo výhoda, pro jaký typ/objem bazénu

──────────────────────────────────────
LONG_DESCRIPTION  (dlouhý popis — HTML)
──────────────────────────────────────
Struktura v HTML, sekce v tomto pořadí:

1. Úvodní věta
   Jedna věta: co produkt je + klíčová technologie + hlavní přínos + vhodný bazén.

2. 🔧 [Název primární funkce — např. "Inteligentní řízení výkonu"]
   Bullet body (•) s konkrétními vlastnostmi nebo parametry.
   Uzavřít řádkem: ➡️ [jedna věta — přínos/výsledek pro zákazníka]

3. ⚙️ Pokročilé funkce
   Položky se zaškrtnutím: ✔ [funkce]
   Uzavřít: ➡️ [přínos]

4. 🛡️ Bezpečnost a ochrana
   Položky se zaškrtnutím: ✔ [typ ochrany]
   Uzavřít: ➡️ [statement o spolehlivosti a dlouhé životnosti]

5. 🔌 Instalace a provoz
   Bullet body s instalačními/provozními parametry a hodnotami (výška sání, průměr potrubí,
   rozsah teplot, krytí IP, atd.)

6. 🏊 Ideální využití
   Bullet body: pro koho a pro jaké situace je produkt vhodný

7. 🟢 Jak to funguje
   3–5 vět v srozumitelné češtině popisující princip fungování produktu

8. 🟢 Technické parametry — [název modelu]
   Bullet body se všemi dostupnými technickými parametry a jejich hodnotami

9. 🟢 Časté dotazy
   4–6 párů otázka–odpověď. Formát:
   <strong>Jak velký bazén toto čerpadlo pokryje?</strong>
   [odpověď]
   (Pokrýt: kompatibilitu s velikostí bazénu, hlučnost, automatizaci, údržbu, záruky.)

════════════════════════════════════════
ZÁVAZNÁ PRAVIDLA
════════════════════════════════════════
• NIKDY nevymýšlej technické specifikace — používej POUZE hodnoty z dodaných dat
• Pokud data pro konkrétní sekci chybí, sekci VYNECH — nepište "není k dispozici"
• NEZAHRNUJ ceny, dostupnost, dobu dodání ani skladové informace
• VŠE musí být v češtině
• LONG_DESCRIPTION musí být validní HTML se zachovanou strukturou výše
• Sekce 🟢 Technické parametry zapiš jako <ul> s hodnotami, nikoli jako tabulku

════════════════════════════════════════
FORMÁT ODPOVĚDI
════════════════════════════════════════
Odpovídej VÝHRADNĚ v tomto formátu — nic navíc nepřidávej:

SHORT_DESCRIPTION: [text bez HTML, 2–3 věty]
LONG_DESCRIPTION: [celý HTML obsah začínající úvodní větou]
"""

# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def _fetch_pdf_text(url: str) -> str:
    """Download a PDF and return extracted text (max ~8 000 chars)."""
    if not HAS_REQUESTS or not HAS_PYPDF:
        return ""
    try:
        resp = _requests.get(url, timeout=30)
        resp.raise_for_status()
        reader = pypdf.PdfReader(io.BytesIO(resp.content))
        pages = [page.extract_text() or "" for page in reader.pages[:10]]
        return "\n".join(pages)[:8000]
    except Exception as exc:
        print(f"    [PDF] Nelze zpracovat {url}: {exc}")
        return ""


def get_pdf_text(url: str, cache: dict) -> str:
    if url not in cache:
        cache[url] = _fetch_pdf_text(url)
    return cache[url]


# ---------------------------------------------------------------------------
# XML parsing helpers
# ---------------------------------------------------------------------------

def extract_product(elem: ET.Element) -> dict:
    """Extract relevant fields from a <PRODUCT> element."""
    # <CODE> as direct child (not nested in CATEGORY or RELATED_PRODUCTS)
    code = (elem.findtext("CODE") or "").strip()

    desc = elem.find(".//DESCRIPTIONS/DESCRIPTION[@language='cz']")
    title = short_desc = long_desc = url = ""
    if desc is not None:
        title = (desc.findtext("TITLE") or "").strip()
        short_desc = (desc.findtext("SHORT_DESCRIPTION") or "").strip()
        long_desc = (desc.findtext("LONG_DESCRIPTION") or "").strip()
        url = (desc.findtext("URL") or "").strip()

    manufacturer = (elem.findtext("MANUFACTURER") or "").strip()

    params: dict[str, str] = {}
    for p in elem.findall(".//PARAMETERS/PARAMETER"):
        name_el = p.find("NAME[@language='cz']")
        val_el = p.find("VALUE[@language='cz']")
        if name_el is not None and val_el is not None:
            n = (name_el.text or "").strip()
            v = (val_el.text or "").strip()
            if n and v:
                params[n] = v

    pdf_urls = [
        (f.findtext("URL") or "").strip()
        for f in elem.findall(".//FILES/FILE")
        if (f.findtext("URL") or "").lower().endswith(".pdf")
    ]

    return {
        "code": code,
        "title": title,
        "short_description": short_desc,
        "long_description": long_desc,
        "url": url,
        "manufacturer": manufacturer,
        "parameters": params,
        "pdf_urls": pdf_urls,
    }


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def build_user_prompt(product: dict, pdf_texts: list) -> str:
    parts = [
        f"Produkt: {product['title']}",
    ]
    if product["manufacturer"]:
        parts.append(f"Výrobce: {product['manufacturer']}")
    if product["url"]:
        parts.append(f"URL produktu: {product['url']}")

    parts.append("")
    parts.append("=== EXISTUJÍCÍ KRÁTKÝ POPIS ===")
    parts.append(product["short_description"] or "(žádný)")

    parts.append("")
    parts.append("=== EXISTUJÍCÍ DLOUHÝ POPIS ===")
    parts.append(product["long_description"] or "(žádný)")

    if product["parameters"]:
        parts.append("")
        parts.append("=== PARAMETRY ===")
        for name, value in product["parameters"].items():
            parts.append(f"• {name}: {value}")

    for i, text in enumerate(pdf_texts, 1):
        if text.strip():
            parts.append("")
            parts.append(f"=== OBSAH MANUÁLU (PDF {i}) ===")
            parts.append(text[:4000])

    parts.append("")
    parts.append(
        "Vygeneruj nový SHORT_DESCRIPTION a LONG_DESCRIPTION pro tento produkt "
        "přesně podle šablony a pravidel ze systémové zprávy."
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------

def generate_description(
    client: anthropic.Anthropic,
    product: dict,
    pdf_cache: dict,
) -> tuple:
    """Return (short_desc, long_desc) strings. Empty strings on error."""
    pdf_texts = [get_pdf_text(url, pdf_cache) for url in product["pdf_urls"]]
    user_prompt = build_user_prompt(product, pdf_texts)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text if response.content else ""
        return _parse_response(text)

    except anthropic.APIError as exc:
        print(f"    [API ERROR] {exc}")
        return "", ""


def _parse_response(text: str) -> tuple:
    short_desc = ""
    long_lines: list = []
    in_long = False

    for line in text.strip().splitlines():
        if line.startswith("SHORT_DESCRIPTION:"):
            short_desc = line[len("SHORT_DESCRIPTION:"):].strip()
            in_long = False
        elif line.startswith("LONG_DESCRIPTION:"):
            in_long = True
            remainder = line[len("LONG_DESCRIPTION:"):].strip()
            if remainder:
                long_lines.append(remainder)
        elif in_long:
            long_lines.append(line)

    return short_desc, "\n".join(long_lines).strip()


# ---------------------------------------------------------------------------
# Output XML builder
# ---------------------------------------------------------------------------

def _safe_cdata(text: str) -> str:
    """Escape ]]> sequences so they don't break a CDATA section."""
    return text.replace("]]>", "]]]]><![CDATA[>")


def build_output_xml(results: list) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<PRODUCTS version="2.0">',
    ]
    for r in results:
        short = _safe_cdata(r["short_description"])
        long_ = _safe_cdata(r["long_description"])
        lines += [
            "  <PRODUCT>",
            f"    <CODE>{r['code']}</CODE>",
            "    <DESCRIPTIONS>",
            '      <DESCRIPTION language="cz">',
            f"        <SHORT_DESCRIPTION><![CDATA[{short}]]></SHORT_DESCRIPTION>",
            f"        <LONG_DESCRIPTION><![CDATA[{long_}]]></LONG_DESCRIPTION>",
            "      </DESCRIPTION>",
            "    </DESCRIPTIONS>",
            "  </PRODUCT>",
        ]
    lines.append("</PRODUCTS>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not HAS_REQUESTS:
        print("[WARN] 'requests' not installed — PDF download disabled.")
    if not HAS_PYPDF:
        print("[WARN] 'pypdf' not installed — PDF text extraction disabled.")

    client = anthropic.Anthropic()

    print(f"Načítám {INPUT_XML} …")
    tree = ET.parse(INPUT_XML)
    root = tree.getroot()

    products = [
        p for elem in root.findall("PRODUCT")
        if (p := extract_product(elem))["code"]
    ]
    print(f"Nalezeno {len(products)} produktů.\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_cache: dict = {}
    results: list = []

    for i, product in enumerate(products, 1):
        print(f"[{i}/{len(products)}] Processing {product['code']} — {product['title']} …")
        short_desc, long_desc = generate_description(client, product, pdf_cache)

        results.append({
            "code": product["code"],
            "short_description": short_desc,
            "long_description": long_desc,
        })

        # Save progress every 10 products so a crash doesn't lose everything
        if i % 10 == 0 or i == len(products):
            OUTPUT_XML.write_text(build_output_xml(results), encoding="utf-8")
            print(f"  → Průběžně uloženo ({i} produktů) → {OUTPUT_XML}")

        if i < len(products):
            time.sleep(1)

    OUTPUT_XML.write_text(build_output_xml(results), encoding="utf-8")
    print(f"\n✓ Hotovo! {len(results)} popisů uloženo do {OUTPUT_XML}")


if __name__ == "__main__":
    main()
