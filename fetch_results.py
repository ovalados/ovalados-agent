#!/usr/bin/env python3
"""
Ovalados — Agente de resultados Super Rugby Américas
Corre cada 2 horas via GitHub Actions.
Obtiene resultados de ESPN API y los escribe a Firebase Realtime Database.
"""

import requests
import json
import os
import sys
from datetime import datetime, timezone

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
# Estos valores vienen de GitHub Secrets (no los hardcodees nunca)
FIREBASE_URL    = os.environ.get("FIREBASE_URL")     # https://TU-PROYECTO.firebaseio.com
FIREBASE_SECRET = os.environ.get("FIREBASE_SECRET")  # tu database secret o token

# ESPN: Super Rugby Américas — el script prueba slugs conocidos automáticamente
ESPN_SLUGS = ["slar", "super.rugby.americas", "242500", "270559"]

ESPN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.espn.com/",
}

# Mapa de nombres ESPN → nombres en nuestra página
# Ajustá si ESPN usa nombres distintos
TEAM_NAME_MAP = {
    "Capibaras":       "Capibaras XV",
    "Capibaras XV":    "Capibaras XV",
    "Tarucas":         "Tarucas",
    "Los Tarucas":     "Tarucas",
    "Dogos XV":        "Dogos XV",
    "Dogos":           "Dogos XV",
    "Pampas":          "Pampas",
    "Pampas XV":       "Pampas",
    "Selknam":         "Selknam",
    "Cobras":          "Cobras BR",
    "Cobras Brasil":   "Cobras BR",
    "Os Cobras":       "Cobras BR",
    "Cobras BR":       "Cobras BR",
    "Yacare":          "Yacare XV",
    "Yacaré XV":       "Yacare XV",
    "Yacare XV":       "Yacare XV",
    "Peñarol":         "Peñarol",
    "Peñarol Rugby":   "Peñarol",
}

def normalize(name):
    """Convierte nombre ESPN al nombre canónico de nuestra página."""
    return TEAM_NAME_MAP.get(name, name)

# ── ESPN API ──────────────────────────────────────────────────────────────────
def find_espn_scoreboard():
    """Prueba slugs hasta encontrar el que funciona para SRA."""
    for slug in ESPN_SLUGS:
        url = f"https://site.api.espn.com/apis/site/v2/sports/rugby/{slug}/scoreboard"
        try:
            r = requests.get(url, headers=ESPN_HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if "events" in data:
                    print(f"✓ ESPN slug encontrado: {slug}")
                    return data, slug
        except Exception as e:
            print(f"  {slug} → {e}")
    return None, None

def find_espn_standings(slug):
    """Obtiene tabla de posiciones de ESPN."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/rugby/{slug}/standings"
    try:
        r = requests.get(url, headers=ESPN_HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"  Standings error: {e}")
    return None

def parse_events(data):
    """Extrae partidos jugados del scoreboard de ESPN."""
    results = []
    for event in data.get("events", []):
        comps = event.get("competitions", [{}])
        if not comps:
            continue
        comp = comps[0]
        
        status = comp.get("status", {}).get("type", {})
        completed = status.get("completed", False)
        
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue
        
        # ESPN: homeTeam = index donde homeAway=="home"
        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
        
        home_name = normalize(home.get("team", {}).get("displayName", ""))
        away_name = normalize(away.get("team", {}).get("displayName", ""))
        home_score = int(home.get("score", 0)) if completed else None
        away_score = int(away.get("score", 0)) if completed else None
        
        # Fecha del partido
        date_str = event.get("date", "")[:10]  # YYYY-MM-DD
        
        results.append({
            "id":      event.get("id"),
            "date":    date_str,
            "home":    home_name,
            "away":    away_name,
            "hs":      home_score,
            "as":      away_score,
            "played":  completed,
        })
    
    return results

def parse_standings(data):
    """Extrae tabla de posiciones de ESPN."""
    standings = []
    try:
        groups = data.get("standings", {}).get("groups", [])
        if not groups:
            # Alternativa: children
            groups = data.get("children", [{}])[0].get("standings", {}).get("groups", [])
        
        entries = groups[0].get("standings", {}).get("entries", [])
        for entry in entries:
            team_name = normalize(entry.get("team", {}).get("displayName", ""))
            stats = {s["name"]: s.get("value", 0) for s in entry.get("stats", [])}
            
            standings.append({
                "name": team_name,
                "pts":  int(stats.get("points", stats.get("pts", 0))),
                "pj":   int(stats.get("gamesPlayed", 0)),
                "g":    int(stats.get("wins", 0)),
                "e":    int(stats.get("ties", stats.get("draws", 0))),
                "p":    int(stats.get("losses", 0)),
                "pf":   int(stats.get("pointsFor", 0)),
                "pc":   int(stats.get("pointsAgainst", 0)),
                "bp":   int(stats.get("bonusPoints", 0)),
                "bf":   int(stats.get("losingBonusPoints", 0)),
            })
    except Exception as e:
        print(f"  Error parseando standings: {e}")
    
    return standings

# ── FIREBASE ──────────────────────────────────────────────────────────────────
def firebase_patch(path, data):
    """Escribe datos a Firebase via REST API."""
    if not FIREBASE_URL or not FIREBASE_SECRET:
        print("⚠ FIREBASE_URL o FIREBASE_SECRET no configurados")
        return False
    
    url = f"{FIREBASE_URL.rstrip('/')}/{path}.json?auth={FIREBASE_SECRET}"
    try:
        r = requests.patch(url, json=data, timeout=10)
        if r.status_code == 200:
            return True
        else:
            print(f"  Firebase error {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  Firebase error: {e}")
        return False

def firebase_put(path, data):
    """Reemplaza datos en Firebase via REST API."""
    if not FIREBASE_URL or not FIREBASE_SECRET:
        print("⚠ FIREBASE_URL o FIREBASE_SECRET no configurados")
        return False
    
    url = f"{FIREBASE_URL.rstrip('/')}/{path}.json?auth={FIREBASE_SECRET}"
    try:
        r = requests.put(url, json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"  Firebase error: {e}")
        return False

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*50}")
    print(f"Ovalados Agent — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")
    
    # 1. Obtener datos de ESPN
    print("→ Consultando ESPN...")
    scoreboard, slug = find_espn_scoreboard()
    
    if not scoreboard:
        print("✗ No se pudo conectar con ESPN. Abortando.")
        sys.exit(1)
    
    # 2. Parsear partidos
    events = parse_events(scoreboard)
    played  = [e for e in events if e["played"]]
    pending = [e for e in events if not e["played"]]
    
    print(f"  Partidos jugados: {len(played)}")
    print(f"  Partidos pendientes: {len(pending)}")
    
    for e in played:
        print(f"  ✓ {e['home']} {e['hs']} - {e['as']} {e['away']} ({e['date']})")
    
    # 3. Obtener standings
    print("\n→ Consultando standings ESPN...")
    standings_data = find_espn_standings(slug)
    standings = parse_standings(standings_data) if standings_data else []
    
    if standings:
        print(f"  Equipos en tabla: {len(standings)}")
        for t in sorted(standings, key=lambda x: -x["pts"]):
            print(f"  {t['name']}: {t['pts']} pts ({t['g']}V {t['e']}E {t['p']}D)")
    else:
        print("  ⚠ No se pudieron obtener standings")
    
    # 4. Escribir a Firebase
    print("\n→ Escribiendo a Firebase...")
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Escribir resultados de partidos jugados
    if played:
        matches_data = {}
        for e in played:
            key = f"{e['home'].replace(' ', '_')}_vs_{e['away'].replace(' ', '_')}_{e['date']}"
            matches_data[key] = {
                "home":   e["home"],
                "away":   e["away"],
                "hs":     e["hs"],
                "as":     e["as"],
                "date":   e["date"],
                "played": True,
            }
        
        ok = firebase_put("superrugby/matches", matches_data)
        print(f"  Partidos → {'✓' if ok else '✗'}")
    
    # Escribir standings
    if standings:
        ok = firebase_put("superrugby/standings", {t["name"]: t for t in standings})
        print(f"  Standings → {'✓' if ok else '✗'}")
    
    # Escribir metadata (última actualización)
    ok = firebase_patch("superrugby/meta", {
        "lastUpdate": timestamp,
        "matchesPlayed": len(played),
        "source": f"espn/{slug}",
    })
    print(f"  Metadata → {'✓' if ok else '✗'}")
    
    print(f"\n✓ Listo\n")

if __name__ == "__main__":
    main()
