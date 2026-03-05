#!/usr/bin/env python3
"""
Ovalados Agent — Scraper de resultados Super Rugby Américas
Lee la nota de ESPN que se actualiza manualmente con resultados y posiciones.
"""
import requests, re, os, sys, json
from datetime import datetime, timezone
from html.parser import HTMLParser

FIREBASE_URL    = os.environ.get("FIREBASE_URL")
FIREBASE_SECRET = os.environ.get("FIREBASE_SECRET")

ESPN_URL = "https://www.espn.com.ar/rugby/nota/_/id/14697755/super-rugby-americas-rugby-resultados-posiciones-fixture-pampas-dogos-xv-tarucas-cobras-selknam-penarol-yacare-capibaras"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-AR,es;q=0.9",
}

# Nombres canónicos
TEAMS = ["Capibaras XV","Tarucas","Dogos XV","Pampas","Selknam","Yacare XV","Cobras BR","Peñarol"]
TEAM_ALIASES = {
    "capibaras xv":"Capibaras XV","capibaras":"Capibaras XV",
    "tarucas":"Tarucas","los tarucas":"Tarucas",
    "dogos xv":"Dogos XV","dogos":"Dogos XV",
    "pampas xv":"Pampas","pampas":"Pampas",
    "selknam":"Selknam",
    "yacaré xv":"Yacare XV","yacare xv":"Yacare XV","yacare":"Yacare XV",
    "cobras br":"Cobras BR","cobras":"Cobras BR","os cobras":"Cobras BR",
    "peñarol":"Peñarol","peñarol rugby":"Peñarol",
}
def normalize(name):
    return TEAM_ALIASES.get(name.lower().strip(), name.strip())

def fetch_page():
    r = requests.get(ESPN_URL, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.text

def parse_scores(html):
    """
    Busca patrones de resultados en el HTML.
    ESPN escribe los resultados en formato texto dentro de la nota.
    Patrones comunes: "Tarucas 41-13 Selknam" o "Tarucas 41 - Selknam 13"
    """
    results = []
    
    # Limpiar HTML básico
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'\s+', ' ', text)
    
    print(f"  Texto extraído: {len(text)} chars")
    
    # Patrón 1: "Equipo A XX - XX Equipo B" o "Equipo A XX-XX Equipo B"
    pattern1 = r'([A-Za-záéíóúÁÉÍÓÚñÑüÜ\s]+?)\s+(\d+)\s*[-–]\s*(\d+)\s+([A-Za-záéíóúÁÉÍÓÚñÑüÜ\s]+?)(?=\s*\d|\s*$|\s*[A-Z])'
    
    # Patrón 2: buscar líneas con scores conocidos de equipos SRA
    team_pattern = '|'.join([re.escape(t) for t in TEAMS] + list(TEAM_ALIASES.keys()))
    
    # Buscar segmentos relevantes del texto
    for match in re.finditer(
        r'(Tarucas|Dogos|Pampas|Selknam|Capibaras|Yacare|Cobras|Peñarol)[^.]*?(\d+)[^.]*?[-–][^.]*?(\d+)[^.]*?(Tarucas|Dogos|Pampas|Selknam|Capibaras|Yacare|Cobras|Peñarol)',
        text, re.IGNORECASE
    ):
        home = normalize(match.group(1))
        hs   = int(match.group(2))
        as_  = int(match.group(3))
        away = normalize(match.group(4))
        if home != away:
            result = {"home": home, "away": away, "hs": hs, "as": as_, "played": True}
            if result not in results:
                results.append(result)
                print(f"  ✓ Resultado: {home} {hs} - {as_} {away}")
    
    return results

def parse_standings_table(html):
    """Busca la tabla de posiciones en el HTML."""
    standings = []
    
    # Buscar filas de tabla con datos de equipos conocidos
    # ESPN usa tablas HTML estándar en sus notas
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
    
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL | re.IGNORECASE)
        cells_text = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        cells_text = [c for c in cells_text if c]
        
        if len(cells_text) >= 7:
            team_name = normalize(cells_text[0])
            if team_name in TEAMS:
                try:
                    standings.append({
                        "name": team_name,
                        "pj":  int(cells_text[1]),
                        "g":   int(cells_text[2]),
                        "p":   int(cells_text[3]),
                        "e":   0,
                        "pf":  int(cells_text[4]) if len(cells_text) > 4 else 0,
                        "pc":  int(cells_text[5]) if len(cells_text) > 5 else 0,
                        "bp":  int(cells_text[6]) if len(cells_text) > 6 else 0,
                        "pts": int(cells_text[-1]),
                    })
                    print(f"  ✓ Standings: {team_name} {cells_text[-1]} pts")
                except (ValueError, IndexError) as e:
                    pass
    
    return standings

def firebase_put(path, data):
    if not FIREBASE_URL or not FIREBASE_SECRET:
        print("⚠ Firebase no configurado"); return False
    url = f"{FIREBASE_URL.rstrip('/')}/{path}.json?auth={FIREBASE_SECRET}"
    try:
        r = requests.put(url, json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"  Firebase error: {e}"); return False

def firebase_patch(path, data):
    if not FIREBASE_URL or not FIREBASE_SECRET: return False
    url = f"{FIREBASE_URL.rstrip('/')}/{path}.json?auth={FIREBASE_SECRET}"
    try:
        r = requests.patch(url, json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"  Firebase error: {e}"); return False

def main():
    print(f"\n{'='*50}")
    print(f"Ovalados Agent — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")

    print(f"→ Scrapeando ESPN nota SRA...")
    try:
        html = fetch_page()
        print(f"  Página obtenida: {len(html)} bytes")
    except Exception as e:
        print(f"✗ Error fetching ESPN: {e}"); sys.exit(1)

    print("\n→ Parseando resultados...")
    results = parse_scores(html)
    print(f"  Resultados encontrados: {len(results)}")

    print("\n→ Parseando posiciones...")
    standings = parse_standings_table(html)
    print(f"  Equipos en tabla: {len(standings)}")

    print("\n→ Escribiendo a Firebase...")
    if results:
        matches_data = {
            f"{r['home'].replace(' ','_')}_vs_{r['away'].replace(' ','_')}": r
            for r in results
        }
        ok = firebase_put("superrugby/matches", matches_data)
        print(f"  Partidos ({len(results)}) → {'✓' if ok else '✗'}")

    if standings:
        ok = firebase_put("superrugby/standings", {t["name"]: t for t in standings})
        print(f"  Standings ({len(standings)}) → {'✓' if ok else '✗'}")

    ok = firebase_patch("superrugby/meta", {
        "lastUpdate": datetime.now(timezone.utc).isoformat(),
        "matchesFound": len(results),
        "source": "espn-nota-sra",
    })
    print(f"  Metadata → {'✓' if ok else '✗'}")
    print("\n✓ Listo\n")

if __name__ == "__main__":
    main()
