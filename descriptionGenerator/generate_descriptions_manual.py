#!/usr/bin/env python3
"""
Manual description generator — first 10 products in export XML.
All specs sourced from official PDF manuals. No API calls.
Run: python3 descriptionGenerator/generate_descriptions_manual.py
"""

from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_XML = OUTPUT_DIR / "descriptions_import.xml"


# ── helpers ────────────────────────────────────────────────────────────────

def _safe(text: str) -> str:
    return text.replace("]]>", "]]]]><![CDATA[>")


def build_xml(products: list) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<PRODUCTS version="2.0">']
    for code, short, long_desc in products:
        lines += [
            "  <PRODUCT>",
            f"    <CODE>{code}</CODE>",
            "    <DESCRIPTIONS>",
            '      <DESCRIPTION language="cz">',
            f"        <SHORT_DESCRIPTION><![CDATA[{_safe(short)}]]></SHORT_DESCRIPTION>",
            f"        <LONG_DESCRIPTION><![CDATA[{_safe(long_desc)}]]></LONG_DESCRIPTION>",
            "      </DESCRIPTION>",
            "    </DESCRIPTIONS>",
            "  </PRODUCT>",
        ]
    lines.append("</PRODUCTS>")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
#  410005 — Badu Picco II/5
#  Source: badu-picco-navod.pdf
#  P1=0,39 kW | P2=0,20 kW | I=1,95 A | Hmax=11 m | IPX5 | třída F
#  Hmotnost 6,6 kg | Max teplota vody 60 °C | Max tlak 2,5 bar
#  Hlučnost <70 dB(A) | Sání 38 mm | Výtlak 32 nebo 38 mm
#  Tělo PP | Oběžné kolo PA 66 GF 30/PC | Mech. těsnění vlnovcové
# ═══════════════════════════════════════════════════════════════════════════

SHORT_410005 = (
    "Čerpadlo Badu Picco II/5 je samonasávací jednofázové bazénové čerpadlo německé výroby Speck "
    "s průtokem 5 m³/h a maximální dopravní výškou 11 m, určené pro bazény o objemu 5–25 m³. "
    "Tělo z polypropylenu (PP) a oběžné kolo z vysoce pevného polyamidu PA 66 GF 30/PC zaručují "
    "výjimečnou odolnost vůči korozi, bazénovým chemikáliím i slané vodě do koncentrace 0,5 %. "
    "Krytí IPX5 a hmotnost 6,6 kg umožňují snadnou instalaci i v prostorově omezených technických šachtách."
)

LONG_410005 = """<p>Čerpadlo Badu Picco II/5 je kompaktní samonasávací oběhové čerpadlo pro bazény od německého výrobce Speck — jednoho z nejuznávanějších evropských výrobců bazénové techniky. S průtokem 5 m³/h a maximální dopravní výškou 11 m spolehlivě zajišťuje filtraci soukromých bazénů o objemu 5–25 m³.</p>

<h3>🔧 Plastová konstrukce z prémiových materiálů</h3>
<ul>
  <li>Tělo čerpadla a víko z polypropylenu (PP) — výjimečná odolnost vůči bazénovým chemikáliím</li>
  <li>Oběžné kolo z polyamidu PA 66 GF 30/PC — mechanicky pevné, korozivzdorné</li>
  <li>Mechanické těsnění vlnovcového typu — pozitivní oddělení bazénové vody od elektromotoru</li>
  <li>Průhledné víčko předfiltračního koše pro snadnou vizuální kontrolu bez demontáže</li>
  <li>Samonasávání bez nutnosti předchozího plnění potrubí vodou</li>
</ul>
<p>➡️ Prémiovými materiály Speck garantuje dlouhodobou odolnost i v náročných podmínkách slaných bazénů.</p>

<h3>⚙️ Pokročilé funkce</h3>
<ul>
  <li>✔ Krytí IPX5 — ochrana motoru před stříkající vodou ze všech směrů</li>
  <li>✔ Třída izolace F — motor odolný vůči teplotním špičkám až 70 °C na povrchu žeber</li>
  <li>✔ Trvalý provoz — čerpadlo je konstruováno pro nepřetržitý celosezónní chod</li>
  <li>✔ Sání 38 mm / výtlak 32 nebo 38 mm — standardní rozměry pro většinu instalací</li>
  <li>✔ Kompaktní zástavbové rozměry — ideální pro malé technické šachty</li>
  <li>✔ Tělo bez vložek — snadno recyklovatelné, šetrné k životnímu prostředí</li>
</ul>
<p>➡️ Picco II/5 zvládne libovolný standardní filtrační systém bez kompromisů v kvalitě provedení.</p>

<h3>🛡️ Bezpečnost a ochrana</h3>
<ul>
  <li>✔ Zabudovaná tepelná ochrana motoru — automatické odpojení při přehřátí</li>
  <li>✔ Krytí IPX5 chrání svorkovnici i motor před vstřikem vody</li>
  <li>✔ Mechanické těsnění vlnovcového typu bez průsaku vody do motoru</li>
  <li>✔ GS zkoušeno podle normy EN 60335-1 — evropská certifikace bezpečnosti</li>
  <li>✔ Maximální provozní tlak: 2,5 bar</li>
</ul>
<p>➡️ Certifikace GS a kompletní sada bezpečnostních prvků zaručují bezpečný provoz po celou sezónu.</p>

<h3>🔌 Instalace a provoz</h3>
<ul>
  <li>Napájení: 230 V / 50 Hz (jednofázové)</li>
  <li>Příkon (P1): 0,39 kW | Výkon (P2): 0,20 kW</li>
  <li>Jmenovitý proud: 1,95 A</li>
  <li>Otáčky motoru: přibližně 2 840 ot/min</li>
  <li>Připojení sání: 38 mm | Výtlak: 32 nebo 38 mm</li>
  <li>Krytí: IPX5 | Třída izolace: F</li>
  <li>Maximální dopravní výška: 11 m</li>
  <li>Maximální teplota vody: 60 °C</li>
  <li>Maximální tlak v systému: 2,5 bar</li>
  <li>Hlučnost: méně než 70 dB(A)</li>
  <li>Hmotnost: 6,6 kg</li>
</ul>

<h3>🏊 Ideální využití</h3>
<ul>
  <li>Soukromé bazény o objemu 5–25 m³</li>
  <li>Sladkovodní i slanovodní bazény (max. 0,5 % NaCl)</li>
  <li>Instalace v malých technických šachtách nebo domcích</li>
  <li>Bazény s pískovými, kazetovými nebo DE filtry</li>
  <li>Uživatelé hledající kompaktní čerpadlo německé kvality za rozumnou cenu</li>
</ul>

<h3>🟢 Jak to funguje</h3>
<p>Badu Picco II/5 je jednostupňové odstředivé čerpadlo s asynchronním jednofázovým motorem. Samonasávací vlastnost zajišťuje zabudovaný předfiltrační koš a hermetická sací komora — čerpadlo vytvoří podtlak samo a nasaje vodu bez ručního plnění potrubí. Oběžné kolo z polyamidu PA 66 GF 30/PC roztočí vodu a vytvoří tlak potřebný pro transport přes filtraci zpět do bazénu. Mechanické těsnění vlnovcového typu umístěné v náboji oběžného kola odděluje bazénovou vodu od elektromotoru a zároveň umožňuje kompaktní zástavbu. Integrovaná tepelná pojistka odpojí motor automaticky, pokud dojde k přehřátí.</p>

<h3>🟢 Technické parametry — Badu Picco II/5</h3>
<ul>
  <li>Průtok: 5 m³/h</li>
  <li>Maximální dopravní výška: 11 m</li>
  <li>Příkon (P1): 0,39 kW</li>
  <li>Výkon (P2): 0,20 kW</li>
  <li>Jmenovitý proud: 1,95 A</li>
  <li>Napájení: 230 V / 50 Hz</li>
  <li>Otáčky motoru: ~2 840 ot/min</li>
  <li>Připojení sání: 38 mm (1½")</li>
  <li>Připojení výtlaku: 32 mm (1¼") nebo 38 mm (1½")</li>
  <li>Krytí: IPX5</li>
  <li>Třída izolace: F</li>
  <li>Maximální teplota vody: 60 °C</li>
  <li>Maximální tlak: 2,5 bar</li>
  <li>Hlučnost: méně než 70 dB(A)</li>
  <li>Materiál těla: polypropylen (PP)</li>
  <li>Materiál oběžného kola: PA 66 GF 30/PC</li>
  <li>Těsnění: mechanické vlnovcové těsnění</li>
  <li>Hmotnost: 6,6 kg</li>
  <li>Pro slanou vodu: Ano (max. 0,5 % NaCl)</li>
  <li>Doporučený objem bazénu: 5–25 m³</li>
  <li>Certifikace: GS, CE (EN 60335-1)</li>
</ul>

<h3>🟢 Časté dotazy</h3>
<p><strong>Pro jak velký bazén je Badu Picco II/5 vhodné?</strong><br>
Čerpadlo je dimenzováno pro bazény o objemu 5–25 m³. Pro větší bazény (25–55 m³) doporučujeme modely Badu Magic II/8 nebo Magic II/11.</p>

<p><strong>Je čerpadlo kompatibilní se slanou vodou?</strong><br>
Ano — plastové díly v kontaktu s vodou jsou z PP a PA 66 GF 30/PC. Čerpadlo snese koncentraci soli až 0,5 % (5 g/l), což pokrývá standardní solné bazény.</p>

<p><strong>Musím čerpadlo před spuštěním naplnit vodou?</strong><br>
Ne, čerpadlo je samonasávací. Pro urychlení prvního spuštění doporučujeme mírně navlhčit předfiltrační komoru — nasátí pak proběhne rychleji.</p>

<p><strong>Jaká je maximální teplota vody?</strong><br>
Čerpadlo je certifikováno pro provoz s vodou do 60 °C, takže je vhodné i pro vyhřívané bazény nebo whirlpoolové aplikace.</p>

<p><strong>Kde sehnat náhradní díly?</strong><br>
Originální náhradní díly Speck — oběžné kolo, mechanické těsnění, předfiltrační koš, O-kroužky — jsou dostupné v sekci náhradních dílů Speck v našem e-shopu.</p>"""


# ═══════════════════════════════════════════════════════════════════════════
#  Badu Magic II family helper
#  Source: cerp-badu-magic-cz.pdf
#  Motor: IPX4 | třída F | ~2840 rpm | hlučnost <70 dB(A) | max temp 60°C
#  Max tlak 2,5 bar | Tělo PP | Oběžné kolo PA 66 GF 30/PC | mech. těsnění
#  Připojení: lepená zástrčka d50 + hadicová tryska 1¼" nebo 1½"
# ═══════════════════════════════════════════════════════════════════════════

def _magic_short(model, flow, hmax, p1, p2, current, weight, pool):
    return (
        f"Čerpadlo Badu Magic II/{model} je samonasávací jednofázové bazénové čerpadlo "
        f"německé výroby Speck s průtokem {flow} m³/h a maximální dopravní výškou {hmax} m, "
        f"navržené pro bazény o objemu {pool} m³. "
        f"Plastová konstrukce z polypropylenu s mechanickým těsněním vlnovcového typu garantuje "
        f"odolnost vůči korozi, bazénovým chemikáliím i slané vodě. "
        f"Hmotnost {weight} kg a napojení přes lepenou zástrčku d50 nebo hadicové trysky "
        f"1¼\"/1½\" umožňují snadné zapojení do stávající bazénové instalace."
    )


def _magic_long(model, flow, hmax, p1, p2, current, weight, pool, pipe_suction, pipe_discharge):
    model_name = f"Badu Magic II/{model}"
    return f"""<p>Čerpadlo {model_name} je samonasávací oběhové a filtrační čerpadlo z německé produkce Speck, určené pro bazény o objemu {pool} m³. S průtokem {flow} m³/h a maximální dopravní výškou {hmax} m spolehlivě zvládne cirkulaci i u objemnějších rekreačních bazénů.</p>

<h3>🔧 Plastová konstrukce prémiové kvality Speck</h3>
<ul>
  <li>Tělo čerpadla a víko z polypropylenu (PP) — chemicky odolné, nevyžadující povrchovou úpravu</li>
  <li>Oběžné kolo z polyamidu PA 66 GF 30/PC — vysoká mechanická pevnost a korozivzdornost</li>
  <li>Mechanické těsnění vlnovcového typu v náboji oběžného kola — bezpečné oddělení vody od motoru</li>
  <li>Průhledné víčko předfiltračního koše — vizuální kontrola znečištění bez demontáže</li>
  <li>Samonasávání — čerpadlo nasaje vodu samo bez ručního plnění potrubí</li>
</ul>
<p>➡️ Prémiové materiály Speck garantují spolehlivý provoz i po letech používání se slanou vodou nebo agresivními chemikáliemi.</p>

<h3>⚙️ Pokročilé funkce</h3>
<ul>
  <li>✔ Krytí IPX4 — ochrana motoru před stříkající vodou</li>
  <li>✔ Třída izolace F — motor odolný vůči teplotním špičkám</li>
  <li>✔ Trvalý provoz S1 — konstruováno pro nepřetržitý celosezónní chod</li>
  <li>✔ Napojení přes lepenou zástrčku d50 nebo hadicové trysky 1¼"/1½"</li>
  <li>✔ Vestavěný předfiltrační koš zachytává hrubé nečistoty před vstupem do čerpadla</li>
  <li>✔ Tělo bez vložek — snadno recyklovatelné provedení</li>
</ul>
<p>➡️ Univerzální připojovací systém a samonasávací vlastnost umožňují instalaci bez speciálního nářadí nebo znalostí.</p>

<h3>🛡️ Bezpečnost a ochrana</h3>
<ul>
  <li>✔ Zabudovaná tepelná ochrana motoru — automatické odpojení při přehřátí</li>
  <li>✔ Krytí IPX4 chrání motor před postřikem vodou</li>
  <li>✔ Mechanické těsnění vlnovcového typu — bez průsaku vody do motoru</li>
  <li>✔ GS zkoušeno podle EN 60335-1 — evropská certifikace bezpečnosti</li>
  <li>✔ Maximální tlak v systému: 2,5 bar</li>
</ul>
<p>➡️ Speck buduje bezpečnostní prvky přímo do konstrukčního řešení čerpadla — bez nutnosti externích pojistek.</p>

<h3>🔌 Instalace a provoz</h3>
<ul>
  <li>Napájení: 230 V / 50 Hz (jednofázové)</li>
  <li>Příkon (P1): {p1} kW | Výkon (P2): {p2} kW</li>
  <li>Jmenovitý proud: {current} A</li>
  <li>Otáčky motoru: přibližně 2 840 ot/min</li>
  <li>Připojení: lepená zástrčka d50 + hadicová tryska pro hadici 1¼" nebo 1½"</li>
  <li>Doporučený průměr potrubí: sání {pipe_suction} mm / výtlak {pipe_discharge} mm</li>
  <li>Krytí: IPX4 | Třída izolace: F</li>
  <li>Maximální dopravní výška: {hmax} m</li>
  <li>Maximální teplota vody: 60 °C</li>
  <li>Maximální tlak v systému: 2,5 bar</li>
  <li>Hlučnost: méně než 70 dB(A)</li>
  <li>Hmotnost: {weight} kg</li>
</ul>

<h3>🏊 Ideální využití</h3>
<ul>
  <li>Soukromé bazény o objemu {pool} m³</li>
  <li>Sladkovodní i slanovodní bazény</li>
  <li>Bazény s pískovými, kazetovými nebo DE filtry</li>
  <li>Instalace s předřazeným čističem dna — vynikající sací schopnost modulu</li>
  <li>Majitelé bazénů hledající spolehlivé čerpadlo německé kvality</li>
</ul>

<h3>🟢 Jak to funguje</h3>
<p>Badu Magic II/{model} je jednostupňové odstředivé čerpadlo s asynchronním střídavým motorem. Samonasávací vlastnost zajišťuje předfiltrační komora a těsná sací trasa — čerpadlo nasaje vodu bez ručního plnění, a to i při instalaci nad hladinou vody (do 2 m). Oběžné kolo z polyamidu PA 66 GF 30/PC přenáší otáčky motoru na průtok vody a vytváří dopravní výšku potřebnou pro překonání odporu filtrační nádoby a potrubí. Vestavěný předfiltrační koš zachytí hrubé nečistoty ještě před vstupem do hydraulické části. Mechanické těsnění vlnovcového typu odděluje bazénovou vodu od elektromotoru, čímž chrání motor před korozí i v agresivním prostředí slaných bazénů.</p>

<h3>🟢 Technické parametry — {model_name}</h3>
<ul>
  <li>Průtok: {flow} m³/h</li>
  <li>Maximální dopravní výška: {hmax} m</li>
  <li>Příkon (P1): {p1} kW</li>
  <li>Výkon (P2): {p2} kW</li>
  <li>Jmenovitý proud: {current} A</li>
  <li>Napájení: 230 V / 50 Hz</li>
  <li>Otáčky motoru: ~2 840 ot/min</li>
  <li>Připojení: zástrčka d50 + tryska 1¼" nebo 1½"</li>
  <li>Doporučený průměr potrubí: sání {pipe_suction} / výtlak {pipe_discharge} mm</li>
  <li>Krytí: IPX4</li>
  <li>Třída izolace: F</li>
  <li>Maximální teplota vody: 60 °C</li>
  <li>Maximální tlak: 2,5 bar</li>
  <li>Hlučnost: méně než 70 dB(A)</li>
  <li>Materiál těla: polypropylen (PP)</li>
  <li>Materiál oběžného kola: PA 66 GF 30/PC</li>
  <li>Těsnění: mechanické vlnovcové těsnění</li>
  <li>Hmotnost: {weight} kg</li>
  <li>Pro slanou vodu: Ano</li>
  <li>Doporučený objem bazénu: {pool} m³</li>
  <li>Certifikace: GS, CE (EN 60335-1)</li>
</ul>

<h3>🟢 Časté dotazy</h3>
<p><strong>Pro jak velký bazén je {model_name} vhodné?</strong><br>
Čerpadlo je navrženo pro bazény o objemu {pool} m³. Celá řada Magic II pokrývá bazény od 5 m³ (model II/4) až po 55 m³ (model II/11), takže lze snadno vybrat přesně dimenzovaný model.</p>

<p><strong>Jaký je rozdíl mezi Badu Magic II a Badu Picco II?</strong><br>
Magic II je větší a výkonnější řada se závitovým / lepeným připojením d50, vhodná pro střední a větší bazény. Picco II je kompaktnější s hadicovým napojením 38 mm, ideální pro menší bazény.</p>

<p><strong>Je čerpadlo kompatibilní se slanou vodou?</strong><br>
Ano — plastové části v kontaktu s vodou jsou z PP a PA 66 GF 30/PC, které odolávají jak bazénovým chemikáliím, tak slané vodě.</p>

<p><strong>Musím čerpadlo naplnit vodou před prvním spuštěním?</strong><br>
Čerpadlo je samonasávací, avšak doporučujeme před prvním spuštěním naplnit předfiltrační komoru čistou vodou — zkrátí se tak čas potřebný k nasátí a zabrání se poškození mechanického těsnění suchým chodem.</p>

<p><strong>Kde sehnat náhradní díly pro Badu Magic II?</strong><br>
Originální náhradní díly Speck — mechanické těsnění, oběžné kolo, O-kroužky, předfiltrační koš — jsou dostupné v sekci náhradních dílů Speck v našem e-shopu.</p>"""


# ═══════════════════════════════════════════════════════════════════════════
#  Badu TOP II / Bettar family helper
#  Source: cerp-bettar-cz.pdf
#  Motor: IPX4 | třída F | ~2820 rpm | max temp 60°C | max tlak 2,5 bar
#  Těsnění: KERAMICKÁ ucpávka (odlišuje od Magic!)
#  Připojení: sání 2" / výtlak 1½" (Rp)
# ═══════════════════════════════════════════════════════════════════════════

def _bettar_short(model, flow, hmax, p1, p2, noise, weight, pool, pipe_s, pipe_d):
    return (
        f"Čerpadlo BADU TOP II/{model} (Bettar) je samonasávací jednofázové bazénové čerpadlo "
        f"německé výroby Speck s průtokem {flow} m³/h a maximální dopravní výškou {hmax} m, "
        f"navržené pro bazény o objemu {pool} m³. "
        f"Plastové tělo z polypropylenu s keramickou ucpávkou hřídele zajišťuje vynikající "
        f"odolnost vůči korozi a slané vodě, přičemž hlučnost pouhých {noise} dB(A) řadí "
        f"čerpadlo mezi tichá řešení bazénové filtrace."
    )


def _bettar_long(model, flow, hmax, p1, p2, current, noise, weight, pool, pipe_s, pipe_d):
    model_name = f"BADU TOP II/{model} (Bettar)"
    return f"""<p>Čerpadlo {model_name} je samonasávací oběhové a filtrační čerpadlo od německého výrobce Speck, navržené pro spolehlivou filtraci bazénů o objemu {pool} m³. S průtokem {flow} m³/h a maximální dopravní výškou {hmax} m nabízí výrazně vyšší výkon než kompaktnější modely řady Picco nebo Magic, přičemž si zachovává nízkou hlučnost {noise} dB(A).</p>

<h3>🔧 Keramická ucpávka a plastová konstrukce</h3>
<ul>
  <li>Tělo čerpadla z polypropylenu (PP) — chemická odolnost bez nutnosti povrchové úpravy</li>
  <li>Keramická ucpávka hřídele — vyšší životnost a těsnost ve srovnání s gumovými ucpávkami</li>
  <li>Integrovaný sací koš s výjimečnou sací schopností — efektivní odsávání ze dna bazénu</li>
  <li>Průhledné víčko předfiltru pro vizuální kontrolu znečištění bez zastavení čerpadla</li>
  <li>Samonasávání bez ručního plnění sacího potrubí</li>
</ul>
<p>➡️ Keramická ucpávka prodlužuje životnost čerpadla a snižuje nároky na údržbu i v agresivním prostředí slaných bazénů.</p>

<h3>⚙️ Pokročilé funkce</h3>
<ul>
  <li>✔ Krytí IPX4 — ochrana motoru před stříkající vodou</li>
  <li>✔ Třída izolace F — vinutí motoru odolné vůči teplotním špičkám</li>
  <li>✔ Trvalý provoz S1 — čerpadlo je konstruováno pro nepřetržitý chod po celou sezónu</li>
  <li>✔ Připojení sání 2" / výtlak 1½" (Rp závity) — kompatibilní s instalacemi pro větší bazény</li>
  <li>✔ Doporučené potrubí: sání {pipe_s} mm / výtlak {pipe_d} mm pro optimální průtok</li>
  <li>✔ Spoje na závitech se těsní teflonovou páskou — bezpečné a trvalé spojení</li>
</ul>
<p>➡️ Větší připojovací průměry a výkonnější hydraulika zvládnou i delší potrubní trasy typické pro větší bazény.</p>

<h3>🛡️ Bezpečnost a ochrana</h3>
<ul>
  <li>✔ Zabudovaná tepelná ochrana motoru — automatické odpojení při přehřátí</li>
  <li>✔ Keramická ucpávka hřídele — eliminuje riziko průsaku vody do elektromotoru</li>
  <li>✔ Krytí IPX4 chrání motor před postřikem ze všech směrů</li>
  <li>✔ CE certifikace — shoda s evropskými bezpečnostními normami</li>
  <li>✔ Maximální tlak v systému: 2,5 bar</li>
</ul>
<p>➡️ Kombinace keramické ucpávky a tepelné ochrany motoru zajišťuje spolehlivý bezporuchový provoz na celé roky.</p>

<h3>🔌 Instalace a provoz</h3>
<ul>
  <li>Napájení: 230 V / 50 Hz (jednofázové)</li>
  <li>Příkon (P1): {p1} kW | Výkon (P2): {p2} kW</li>
  <li>Jmenovitý proud: {current} A</li>
  <li>Otáčky motoru: přibližně 2 820 ot/min</li>
  <li>Připojení sání: Rp 2" | Výtlak: Rp 1½"</li>
  <li>Doporučený průměr potrubí: sání {pipe_s} mm / výtlak {pipe_d} mm</li>
  <li>Krytí: IPX4 | Třída izolace: F</li>
  <li>Maximální dopravní výška: {hmax} m</li>
  <li>Maximální teplota vody: 60 °C</li>
  <li>Maximální tlak v systému: 2,5 bar</li>
  <li>Hlučnost: {noise} dB(A) ve vzdálenosti 1 m</li>
  <li>Hmotnost: {weight} kg</li>
</ul>

<h3>🏊 Ideální využití</h3>
<ul>
  <li>Soukromé a polokomunitní bazény o objemu {pool} m³</li>
  <li>Sladkovodní i slanovodní bazény</li>
  <li>Bazény s předřazeným čističem dna — vynikající sací schopnost</li>
  <li>Instalace s delšími potrubními trasami díky vyšší dopravní výšce {hmax} m</li>
  <li>Bazény s pískovými, kazetovými nebo DE filtry vyžadující vyšší průtok</li>
</ul>

<h3>🟢 Jak to funguje</h3>
<p>BADU TOP II/{model} (Bettar) je jednostupňové odstředivé čerpadlo s asynchronním střídavým motorem při ~2 820 ot/min. Samonasávací konstrukční princip zajišťuje spolehlivé nasátí vody i při instalaci čerpadla nad hladinou bazénu (do 2 m). Voda prochází přes předfiltrační sítko zachycující hrubé nečistoty, poté je urychlena oběžným kolem a přes výtlačné potrubí dopravena do filtrace. Keramická ucpávka hřídele — na rozdíl od klasického gumového těsnění — poskytuje vyšší odolnost vůči chemikáliím a delší životnost bez nutnosti výměny. Integrovaná tepelná ochrana automaticky odpojí čerpadlo při překročení bezpečné teploty motoru.</p>

<h3>🟢 Technické parametry — {model_name}</h3>
<ul>
  <li>Průtok: {flow} m³/h</li>
  <li>Maximální dopravní výška: {hmax} m</li>
  <li>Příkon (P1): {p1} kW</li>
  <li>Výkon (P2): {p2} kW</li>
  <li>Jmenovitý proud: {current} A</li>
  <li>Napájení: 230 V / 50 Hz</li>
  <li>Otáčky motoru: ~2 820 ot/min</li>
  <li>Připojení sání: Rp 2" | Výtlak: Rp 1½"</li>
  <li>Doporučený průměr potrubí sání: {pipe_s} mm | výtlak: {pipe_d} mm</li>
  <li>Krytí: IPX4</li>
  <li>Třída izolace: F</li>
  <li>Maximální teplota vody: 60 °C</li>
  <li>Maximální tlak: 2,5 bar</li>
  <li>Hlučnost: {noise} dB(A) @ 1 m</li>
  <li>Materiál těla: polypropylen (PP)</li>
  <li>Těsnění hřídele: keramická ucpávka</li>
  <li>Hmotnost: {weight} kg</li>
  <li>Pro slanou vodu: Ano</li>
  <li>Doporučený objem bazénu: {pool} m³</li>
  <li>Certifikace: CE</li>
</ul>

<h3>🟢 Časté dotazy</h3>
<p><strong>Pro jak velký bazén je {model_name} vhodné?</strong><br>
Čerpadlo je dimenzováno pro bazény o objemu {pool} m³. Řada Bettar pokrývá bazény od 25 m³ (model 8) po 55 m³ (modely 12 a 14), přičemž každý model nabízí odlišnou výšku dopravy.</p>

<p><strong>Jaký je rozdíl mezi keramickou a mechanickou ucpávkou?</strong><br>
Keramická ucpávka má výrazně vyšší tvrdost a odolnost vůči chemikáliím než klasická grafitová nebo pryžová mechanická ucpávka, díky čemuž déle drží těsnost a nevyžaduje tak časté výměny.</p>

<p><strong>Je čerpadlo vhodné pro slaný bazén?</strong><br>
Ano — plastové části jsou z polypropylenu (PP), který je odolný vůči slané vodě i standardním bazénovým chemikáliím.</p>

<p><strong>Musím přidat pojistný ventil na sací potrubí?</strong><br>
Pokud je čerpadlo instalováno nad hladinou vody, doporučujeme osadit zpětný ventil na sací potrubí. Ten zabrání samovolnému vyprázdnění potrubí při odstavení čerpadla a zkrátí dobu opětovného nasátí.</p>

<p><strong>Kde sehnat náhradní díly?</strong><br>
Originální náhradní díly Speck pro řadu Bettar — keramická ucpávka, oběžné kolo, předfiltrační sítko, O-kroužky, motorová jednotka — jsou dostupné v sekci náhradních dílů Speck v našem e-shopu.</p>"""


# ═══════════════════════════════════════════════════════════════════════════
#  Astral Sena family helper
#  Source: sena-cz-web.pdf + TÜV certificate
#  Motor: IP-55 | třída F | Tepelná ochrana (1f.) | Max teplota 35°C
#  Certifikace: TÜV SÜD, CE, EN 60335-2-41:2004
#  Tělo: termoplast nejnovější generace
# ═══════════════════════════════════════════════════════════════════════════

def _sena_short(code, flow, hp, p2_kw, pool, hmax):
    return (
        f"Čerpadlo Sena {flow} m³/h je samonasávací jednofázové bazénové čerpadlo španělského výrobce "
        f"AstralPool (Fluidra) s výkonem {hp} HP ({p2_kw} kW) a maximální dopravní výškou {hmax} m, "
        f"navržené pro bazény o objemu {pool} m³. "
        f"Těleso z termoplastů nejnovější generace s integrovaným zachycovačem hrubých nečistot, "
        f"motor s krytím IP-55 a certifikace TÜV SÜD zajišťují spolehlivý a bezpečný provoz po celou sezónu. "
        f"Maximální přípustná teplota vody 35 °C předurčuje čerpadlo pro standardní venkovní bazény."
    )


def _sena_long(code, flow, hp, p2_kw, pool, hmax, weight_dim):
    model_name = f"Sena {flow} m³/h"
    return f"""<p>Čerpadlo Astral Sena {flow} m³/h je samonasávací oběhové čerpadlo od španělského výrobce AstralPool — člena skupiny Fluidra, světového lídra v bazénové technice. S průtokem {flow} m³/h a maximální dopravní výškou {hmax} m zajistí spolehlivou filtraci bazénů o objemu {pool} m³ při nízkých provozních nákladech.</p>

<h3>🔧 Samonasávací konstrukce s integrovaným předfiltrem</h3>
<ul>
  <li>Tělo čerpadla z termoplastů nejnovější generace — odolnost vůči UV záření, chemikáliím i slané vodě</li>
  <li>Integrovaný zachycovač hrubých nečistot s košem — zabraňuje vniknutí cizích těles do hydraulické části</li>
  <li>Sítko zachycovače podmiňuje horizontální montáž čerpadla — jednoduchá instalace na rovný podklad</li>
  <li>Samonasávací vlastnost — efektivní nasátí i při instalaci až 2 m nad hladinou vody</li>
  <li>Sací potrubí napojeno se sklonem 2 % k čerpadlu — eliminuje vzduchové sifony</li>
</ul>
<p>➡️ Integrovaný předfiltr chrání hydrauliku a prodlužuje životnost čerpadla bez nutnosti externího košového filtru.</p>

<h3>⚙️ Pokročilé funkce</h3>
<ul>
  <li>✔ Motor s krytím IP-55 — ochrana před prachem i stříkající vodou ze všech stran</li>
  <li>✔ Třída izolace F — vinutí motoru odolné vůči teplotním špičkám</li>
  <li>✔ Tepelná ochrana ve vinutí (jednofázové modely) — automatická ochrana před přetížením</li>
  <li>✔ Podstavec pro pevné ukotvení k podlaze je součástí dodávky</li>
  <li>✔ Těsnění a tvarovky pro připojení sacího a výtlačného potrubí v balení</li>
  <li>✔ Certifikace TÜV SÜD — nezávislé ověření bezpečnosti a kvality</li>
</ul>
<p>➡️ Kompletní příslušenství v balení a snadná montáž umožňují instalaci bez nutnosti shánět dodatečné díly.</p>

<h3>🛡️ Bezpečnost a ochrana</h3>
<ul>
  <li>✔ Tepelná ochrana ve vinutí motoru — automatické odpojení při přetížení</li>
  <li>✔ Krytí IP-55 — ochrana před prachem i vodním postřikem</li>
  <li>✔ Proudový chránič 30 mA jako povinná součást elektrické instalace</li>
  <li>✔ Certifikace TÜV SÜD (EN 60335-2-41:2004) — testováno nezávislou zkušebnou</li>
  <li>✔ Maximální teplota vody: 35 °C</li>
</ul>
<p>➡️ TÜV certifikace a IP-55 krytí zaručují bezpečný provoz po celou sezónu v souladu s evropskými normami.</p>

<h3>🔌 Instalace a provoz</h3>
<ul>
  <li>Napájení: 230 V / 50 Hz (jednofázové)</li>
  <li>Výkon motoru: {hp} HP / {p2_kw} kW</li>
  <li>Krytí: IP-55 | Třída izolace: F</li>
  <li>Maximální dopravní výška: {hmax} m</li>
  <li>Maximální teplota vody: 35 °C</li>
  <li>Sací potrubí: sklon 2 % směrem k čerpadlu</li>
  <li>Maximální výška instalace nad hladinou: 2 m</li>
  <li>Připojení: přiložené tvarovky a těsnění</li>
  <li>Certifikace: TÜV SÜD, CE (EN 60335-2-41:2004)</li>
</ul>

<h3>🏊 Ideální využití</h3>
<ul>
  <li>Soukromé bazény o objemu {pool} m³</li>
  <li>Sladkovodní i slanovodní bazény</li>
  <li>Bazény s pískovými, kazetovými nebo DE filtry</li>
  <li>Instalace do zahradních technických šachet nebo domků</li>
  <li>Uživatelé hledající certifikované španělské čerpadlo s komplexním příslušenstvím</li>
</ul>

<h3>🟢 Jak to funguje</h3>
<p>Astral Sena {flow} m³/h je samonasávací odstředivé čerpadlo s jednofázovým asynchronním motorem s krytím IP-55. Před spuštěním je nutné naplnit zachycovač hrubých nečistot vodou až po sací otvor — poté čerpadlo nasává automaticky. Koš zachycovače hrubých nečistot zachytí kamínky, listí a jiné hrubé nečistoty dříve, než by mohly poškodit oběžné kolo nebo difuzor. Voda proudí přes hydraulickou část, kde oběžné kolo urychlí průtok a vytvoří potřebný tlak pro transport přes filtraci zpět do bazénu. Jednofázový motor je vybaven tepelnou ochranou ve vinutí, která při přetížení automaticky odpojí napájení a po ochlazení opět umožní spuštění.</p>

<h3>🟢 Technické parametry — Astral {model_name}</h3>
<ul>
  <li>Průtok: {flow} m³/h</li>
  <li>Maximální dopravní výška: {hmax} m</li>
  <li>Výkon motoru: {hp} HP / {p2_kw} kW</li>
  <li>Napájení: 230 V / 50 Hz</li>
  <li>Krytí: IP-55</li>
  <li>Třída izolace: F</li>
  <li>Maximální teplota vody: 35 °C</li>
  <li>Materiál těla: termoplast nejnovější generace</li>
  <li>Pro slanou vodu: Ano</li>
  <li>Doporučený objem bazénu: {pool} m³</li>
  <li>Certifikace: TÜV SÜD, CE (EN 60335-2-41:2004, EN-ISO 9906:1999)</li>
</ul>

<h3>🟢 Časté dotazy</h3>
<p><strong>Pro jak velký bazén je Astral Sena {flow} m³/h vhodné?</strong><br>
Čerpadlo je navrženo pro bazény o objemu {pool} m³. Celá řada Sena pokrývá průtoky od 4 m³/h (model 25461) po 14 m³/h (model 25467) — vyberte model odpovídající objemu vašeho bazénu.</p>

<p><strong>Musím čerpadlo před spuštěním naplnit vodou?</strong><br>
Ano — před každým spuštěním je nutné naplnit zachycovač hrubých nečistot vodou až po sací otvor a řádně dotáhnout víko. Čerpadlo nikdy nespouštějte nasucho — riskujete poškození ucpávky.</p>

<p><strong>Je čerpadlo vhodné pro slaný bazén?</strong><br>
Ano, termoplastové tělo odolá slané vodě i standardním bazénovým chemikáliím. Čerpadlo je certifikováno pro standardní bazénové použití dle TÜV SÜD.</p>

<p><strong>Jaká je maximální teplota vody?</strong><br>
Maximální přípustná teplota vody je 35 °C. Čerpadlo je primárně určeno pro standardní venkovní bazény, nikoliv pro přehřívané vany nebo whirlpool aplikace.</p>

<p><strong>Kde sehnat náhradní díly?</strong><br>
Originální náhradní díly AstralPool — oběžné kolo, ucpávka, koš zachycovače, O-kroužky — jsou dostupné v sekci náhradních dílů AstralPool / Sena v našem e-shopu.</p>"""


# ═══════════════════════════════════════════════════════════════════════════
#  Assemble all 10 products
# ═══════════════════════════════════════════════════════════════════════════

products = [
    # --- Badu Picco II/5 ---
    ("410005", SHORT_410005, LONG_410005),

    # --- Badu Magic II/4 ---
    (
        "410004",
        _magic_short("4", 4, 10.6, "0,35", "0,18", "1,95", 5.9, "5–25"),
        _magic_long("4", 4, 10.6, "0,35", "0,18", "1,95", 5.9, "5–25", 50, 40),
    ),

    # --- Badu Magic II/6 ---
    (
        "410006",
        _magic_short("6", 6, 12.0, "0,45", "0,25", "2,30", 7.3, "5–25"),
        _magic_long("6", 6, 12.0, "0,45", "0,25", "2,30", 7.3, "5–25", 50, 40),
    ),

    # --- Badu Magic II/8 ---
    (
        "410008",
        _magic_short("8", 8, 14.0, "0,61", "0,40", "2,70", 8.3, "25–35"),
        _magic_long("8", 8, 14.0, "0,61", "0,40", "2,70", 8.3, "25–35", 50, 50),
    ),

    # --- Badu Magic II/11 ---
    (
        "410011",
        _magic_short("11", 11, 14.0, "0,72", "0,45", "3,20", 8.3, "35–55"),
        _magic_long("11", 11, 14.0, "0,72", "0,45", "3,20", 8.3, "35–55", 50, 50),
    ),

    # --- Badu TOP II/8 = Bettar 8 ---
    (
        "420008",
        _bettar_short("8", 8, 14.5, "0,57", "0,30", 56.5, 10, "25–35", 50, 50),
        _bettar_long("8", 8, 14.5, "0,57", "0,30", "2,6", 56.5, 10, "25–35", 50, 50),
    ),

    # --- Badu TOP II/12 = Bettar 12 ---
    (
        "420012",
        _bettar_short("12", 12, 15.5, "0,69", "0,45", 57.8, 10, "35–55", 50, 50),
        _bettar_long("12", 12, 15.5, "0,69", "0,45", "3,2", 57.8, 10, "35–55", 50, 50),
    ),

    # --- Badu TOP II/14 = Bettar 14 ---
    (
        "420014",
        _bettar_short("14", 14, 16.5, "0,97", "0,65", 60.3, 11.5, "35–55", 63, 50),
        _bettar_long("14", 14, 16.5, "0,97", "0,65", "4,7", 60.3, 11.5, "35–55", 63, 50),
    ),

    # --- Astral Sena 9 m³/h (25463) ---
    (
        "25463",
        _sena_short("25463", 9, "0,75", "0,61", "25–35", 10),
        _sena_long("25463", 9, "0,75", "0,61", "25–35", 10, ""),
    ),

    # --- Astral Sena 6 m³/h (25462) ---
    (
        "25462",
        _sena_short("25462", 6, "0,50", "0,45", "5–25", 8),
        _sena_long("25462", 6, "0,50", "0,45", "5–25", 8, ""),
    ),
]


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    xml = build_xml(products)
    OUTPUT_XML.write_text(xml, encoding="utf-8")
    print(f"✓ {len(products)} popisů zapsáno do {OUTPUT_XML}")
