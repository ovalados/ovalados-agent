#!/usr/bin/env python3
"""
Ovalados Agent — Fetcher multi-torneo
- Super Rugby Américas: scraping nota ESPN
- Seis Naciones:        scraping nota ESPN
- URBA (todos los torneos): API oficial api.urba.org.ar
"""
import requests, re, os, json
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
    "Referer": "https://fixture.urba.org.ar/",
}

# ── URLs ──────────────────────────────────────────────────────────────────────
SRA_URL       = "https://www.espn.com.ar/rugby/nota/_/id/14697755/super-rugby-americas-rugby-resultados-posiciones-fixture-pampas-dogos-xv-tarucas-cobras-selknam-penarol-yacare-capibaras"
URBA_API_BASE = "https://api.urba.org.ar/api/championship"

# Torneos URBA activos 2026 — id del campeonato y clave en Firebase
URBA_TORNEOS = [
    {"id": "2025176", "nombre": "Top 14",         "firebase_key": "urbaTop14"},
    {"id": "2025184", "nombre": "Intermedia",      "firebase_key": "urbaIntermedia"},
    {"id": "2025185", "nombre": "Pre-Intermedia",  "firebase_key": "urbaPreIntermedia"},
    {"id": "2025186", "nombre": "Pre-Inter B",     "firebase_key": "urbaPreInterB"},
    {"id": "2025197", "nombre": "Pre-Inter C",     "firebase_key": "urbaPreInterC"},
    {"id": "2025198", "nombre": "Pre-Inter D",     "firebase_key": "urbaPreInterD"},
    {"id": "2025200", "nombre": "Pre-Inter E",     "firebase_key": "urbaPreInterE"},
    {"id": "2025201", "nombre": "Pre-Inter F",     "firebase_key": "urbaPreInterF"},
    {"id": "2025206", "nombre": "M22",             "firebase_key": "urbaM22"},
]

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

def norm_sra(name): return SRA_ALIASES.get(name.lower().strip(), name.strip())

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
    Soporta 3 columnas (TeamA | score | TeamB) y 4 (fecha | TeamA | score | TeamB).
    Deduplica ida/vuelta con clave canónica ordenada.
    """
    html = fetch_html(url)
    if not html: return []

    results = []
    seen = set()

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL | re.IGNORECASE)
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        cells = [re.sub(r'\s+', ' ', c).strip() for c in cells]
        cells = [c for c in cells if c]

        if len(cells) == 4:
            _, home_cell, score_cell, away_cell = cells
        elif len(cells) == 3:
            home_cell, score_cell, away_cell = cells
        else:
            continue

        score_match = re.match(r'^(\d{1,3})[-–](\d{1,3})$', score_cell.strip())
        if not score_match: continue

        hs  = int(score_match.group(1))
        as_ = int(score_match.group(2))
        home = normalize_fn(home_cell)
        away = normalize_fn(away_cell)

        if home not in teams_list or away not in teams_list: continue
        if home == away: continue

        canonical = "_vs_".join(sorted([home, away]))
        if canonical in seen: continue
        seen.add(canonical)

        results.append({"home": home, "away": away, "hs": hs, "as": as_, "played": True})
        print(f"  ✓ {home} {hs}–{as_} {away}")

    return results

# ── Seis Naciones ─────────────────────────────────────────────────────────────
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

# ── URBA — función genérica para cualquier torneo ─────────────────────────────
def fetch_urba_torneo(torneo):
    """
    Llama a la API de URBA para un torneo dado y guarda los resultados en Firebase.
    torneo: dict con keys 'id', 'nombre', 'firebase_key'
    """
    nombre      = torneo["nombre"]
    firebase_key = torneo["firebase_key"]
    url         = f"{URBA_API_BASE}/{torneo['id']}"

    print(f"\n── URBA {nombre.upper()} {'─'*(38 - len(nombre))}")
    results = []
    try:
        r = requests.get(url, headers=HEADERS_API, timeout=15)
        r.raise_for_status()
        data = r.json()
        championship = data.get("championship", [{}])[0]
        rounds = championship.get("rounds", [])

        for rnd in rounds:
            for match in rnd.get("matches", []):
                if not match.get("fulfilled"):
                    continue
                home = match["local_team"]["name"].strip()
                away = match["visit_team"]["name"].strip()
                hs   = match["local_team_score"]
                as_  = match["visit_team_score"]
                num_fecha = rnd["name"].split()[-1]
                key  = f"{home.replace(' ','_')}_vs_{away.replace(' ','_')}_F{num_fecha}"
                results.append({
                    "home": home, "away": away,
                    "hs": hs, "as": as_,
                    "played": True, "fecha": rnd["name"]
                })
                print(f"  ✓ [{rnd['name']}] {home} {hs}–{as_} {away}")

    except Exception as e:
        print(f"  Error llamando API URBA ({nombre}): {e}")

    print(f"  Total resultados: {len(results)}")
    if results:
        ok = firebase_put(f"{firebase_key}/matches",
            {f"{r['home'].replace(' ','_')}_vs_{r['away'].replace(' ','_')}_F{r['fecha'].split()[-1]}": r
             for r in results})
        print(f"  Firebase → {'✓' if ok else '✗'}")
    firebase_patch(f"{firebase_key}/meta", {
        "lastUpdate":    datetime.now(timezone.utc).isoformat(),
        "matchesFound":  len(results),
        "source":        "api-urba-org-ar",
        "championshipId": torneo["id"],
    })

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*52}")
    print(f"Ovalados Agent — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*52}")

    fetch_sra()
    fetch_seis_naciones()

    for torneo in URBA_TORNEOS:
        fetch_urba_torneo(torneo)

    print(f"\n✓ Listo\n")

if __name__ == "__main__":
    main()
