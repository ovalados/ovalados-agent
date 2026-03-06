#!/usr/bin/env python3
"""
Ovalados Agent — Fetcher multi-torneo
- Super Rugby Américas: scraping nota ESPN
- Seis Naciones: ESPN API (league/180659)
- URBA Top 14: scraping nota ESPN (arranca 14/03)
"""
import requests, re, os, sys, json
from datetime import datetime, timezone

FIREBASE_URL    = os.environ.get("FIREBASE_URL")
FIREBASE_SECRET = os.environ.get("FIREBASE_SECRET")

HEADERS_HTML = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-AR,es;q=0.9",
}
HEADERS_API = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.espn.com/",
}

# ── URLs ──────────────────────────────────────────────────────────────────────
SRA_URL   = "https://www.espn.com.ar/rugby/nota/_/id/14697755/super-rugby-americas-rugby-resultados-posiciones-fixture-pampas-dogos-xv-tarucas-cobras-selknam-penarol-yacare-capibaras"
URBA_URL  = "https://www.espn.com.ar/rugby/nota/_/id/6719883/urba-top-14-fixture-resultados-tablas"

# ── SRA teams ─────────────────────────────────────────────────────────────────
SRA_TEAMS = ["Capibaras XV","Tarucas","Dogos XV","Pampas","Selknam","Yacare XV","Cobras BR","Peñarol"]
SRA_ALIASES = {
    "capibaras xv":"Capibaras XV","capibaras":"Capibaras XV",
    "tarucas":"Tarucas","los tarucas":"Tarucas",
    "dogos xv":"Dogos XV","dogos":"Dogos XV",
    "pampas xv":"Pampas","pampas":"Pampas",
    "selknam":"Selknam",
    "yacaré xv":"Yacare XV","yacare xv":"Yacare XV","yacare":"Yacare XV",
    "cobras br":"Cobras BR","cobras":"Cobras BR","os cobras":"Cobras BR",
    "peñarol":"Peñarol","peñarol rugby":"Peñarol",
}

# ── URBA teams ────────────────────────────────────────────────────────────────
URBA_TEAMS = ["La Plata","Hindu","Champagnat","Alumni","Newman","SIC",
              "Belgrano Athletic","Buenos Aires C&RC","CUBA","CASI",
              "Los Tilos","Atlético del Rosario","Regatas Bella Vista","Los Matreros"]
URBA_ALIASES = {
    "la plata":"La Plata","hindu":"Hindu","champagnat":"Champagnat",
    "alumni":"Alumni","newman":"Newman","sic":"SIC",
    "belgrano athletic":"Belgrano Athletic","belgrano":"Belgrano Athletic",
    "buenos aires c&rc":"Buenos Aires C&RC","bacrc":"Buenos Aires C&RC",
    "cuba":"CUBA","casi":"CASI","los tilos":"Los Tilos",
    "atlético del rosario":"Atlético del Rosario","atletico del rosario":"Atlético del Rosario",
    "regatas bella vista":"Regatas Bella Vista","regatas":"Regatas Bella Vista",
    "los matreros":"Los Matreros","matreros":"Los Matreros",
}

def norm_sra(name):  return SRA_ALIASES.get(name.lower().strip(), name.strip())
def norm_urba(name): return URBA_ALIASES.get(name.lower().strip(), name.strip())

# ── Firebase ──────────────────────────────────────────────────────────────────
def firebase_put(path, data):
    if not FIREBASE_URL or not FIREBASE_SECRET:
        print("  ⚠ Firebase no configurado"); return False
    url = f"{FIREBASE_URL.rstrip('/')}/{path}.json?auth={FIREBASE_SECRET}"
    try:
        r = requests.put(url, json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"  Firebase PUT error: {e}"); return False

def firebase_patch(path, data):
    if not FIREBASE_URL or not FIREBASE_SECRET: return False
    url = f"{FIREBASE_URL.rstrip('/')}/{path}.json?auth={FIREBASE_SECRET}"
    try:
        r = requests.patch(url, json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"  Firebase PATCH error: {e}"); return False

# ── Scraper de tablas ESPN ────────────────────────────────────────────────────
def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS_HTML, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  Error fetching {url}: {e}"); return ""

def scrape_scores(url, teams_list, normalize_fn):
    """
    Parsea tablas HTML de notas ESPN.
    Formato de fila jugada:  | fecha | TeamA | 18-28 | TeamB |
    Formato de fila pendiente: | fecha | TeamA | vs   | TeamB |
    """
    html = fetch_html(url)
    if not html: return []

    results = []
    seen = set()

    # Extraer filas de tabla
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL | re.IGNORECASE)
        # Limpiar HTML de cada celda
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        cells = [re.sub(r'\s+', ' ', c).strip() for c in cells]
        cells = [c for c in cells if c]

        # Necesitamos exactamente 4 celdas: fecha, home, score, away
        if len(cells) != 4: continue

        date_cell, home_cell, score_cell, away_cell = cells

        # Score debe ser formato X-Y con números razonables
        score_match = re.match(r'^(\d{1,3})[-–](\d{1,3})$', score_cell.strip())
        if not score_match: continue  # "vs" o cualquier otra cosa → salteamos

        hs = int(score_match.group(1))
        as_ = int(score_match.group(2))

        home = normalize_fn(home_cell)
        away = normalize_fn(away_cell)

        # Validar que sean equipos conocidos
        if home not in teams_list or away not in teams_list: continue
        if home == away: continue

        key = f"{home}_vs_{away}"
        if key in seen: continue
        seen.add(key)

        results.append({"home": home, "away": away, "hs": hs, "as": as_, "played": True})
        print(f"  ✓ {home} {hs}–{as_} {away}")

    return results

# ── Seis Naciones via scraping nota ESPN ─────────────────────────────────────
SN_URL = "https://www.espn.com.ar/rugby/nota/_/id/15203928/rugby-seis-naciones-fixture-resultados-tabla-posiciones-2026-francia-irlanda-gales-escocia-inglaterra-italia-partidos"
SN_TEAMS = ["Francia","Escocia","Irlanda","Italia","Inglaterra","Gales"]
SN_ALIASES = {
    "france":"Francia","scotland":"Escocia","ireland":"Irlanda",
    "italy":"Italia","england":"Inglaterra","wales":"Gales",
    "francia":"Francia","escocia":"Escocia","irlanda":"Irlanda",
    "italia":"Italia","inglaterra":"Inglaterra","gales":"Gales",
}
def norm_sn(name): return SN_ALIASES.get(name.lower().strip(), name.strip())

def fetch_seis_naciones():
    print("\n── SEIS NACIONES ────────────────────────────────")
    results = scrape_scores(SN_URL, SN_TEAMS, norm_sn)
    print(f"  Total resultados: {len(results)}")
    if results:
        ok = firebase_put("seisNaciones/matches",
            {f"{r['home']}_vs_{r['away']}": r for r in results})
        print(f"  Firebase → {'✓' if ok else '✗'}")
    firebase_patch("seisNaciones/meta", {
        "lastUpdate": datetime.now(timezone.utc).isoformat(),
        "matchesFound": len(results), "source": "espn-nota-sn"
    })

# ── Super Rugby Américas ──────────────────────────────────────────────────────
def fetch_sra():
    print("\n── SUPER RUGBY AMÉRICAS ─────────────────────────")
    results = scrape_scores(SRA_URL, SRA_TEAMS, norm_sra)
    print(f"  Total resultados: {len(results)}")
    if results:
        ok = firebase_put("superrugby/matches",
            {f"{r['home'].replace(' ','_')}_vs_{r['away'].replace(' ','_')}": r for r in results})
        print(f"  Firebase → {'✓' if ok else '✗'}")
    firebase_patch("superrugby/meta", {
        "lastUpdate": datetime.now(timezone.utc).isoformat(),
        "matchesFound": len(results), "source": "espn-nota-sra"
    })

# ── URBA Top 14 ───────────────────────────────────────────────────────────────
def fetch_urba():
    print("\n── URBA TOP 14 ──────────────────────────────────")
    results = scrape_scores(URBA_URL, URBA_TEAMS, norm_urba)
    print(f"  Total resultados: {len(results)}")
    if results:
        ok = firebase_put("urbaTop14/matches",
            {f"{r['home'].replace(' ','_')}_vs_{r['away'].replace(' ','_')}": r for r in results})
        print(f"  Firebase → {'✓' if ok else '✗'}")
    firebase_patch("urbaTop14/meta", {
        "lastUpdate": datetime.now(timezone.utc).isoformat(),
        "matchesFound": len(results), "source": "espn-nota-urba"
    })

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*52}")
    print(f"Ovalados Agent — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*52}")

    fetch_sra()
    fetch_seis_naciones()
    fetch_urba()

    print(f"\n✓ Listo\n")

if __name__ == "__main__":
    main()
