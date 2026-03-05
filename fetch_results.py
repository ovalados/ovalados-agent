#!/usr/bin/env python3
import requests, json, os, sys
from datetime import datetime, timezone

FIREBASE_URL    = os.environ.get("FIREBASE_URL")
FIREBASE_SECRET = os.environ.get("FIREBASE_SECRET")
ESPN_SLUGS = ["276687", "270559", "slar", "super.rugby.americas"]
ESPN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.espn.com/",
}
TEAM_NAME_MAP = {
    "Capibaras":"Capibaras XV","Capibaras XV":"Capibaras XV",
    "Tarucas":"Tarucas","Los Tarucas":"Tarucas",
    "Dogos XV":"Dogos XV","Dogos":"Dogos XV",
    "Pampas":"Pampas","Pampas XV":"Pampas",
    "Selknam":"Selknam",
    "Cobras":"Cobras BR","Cobras Brasil":"Cobras BR","Os Cobras":"Cobras BR","Cobras BR":"Cobras BR",
    "Yacare":"Yacare XV","Yacaré XV":"Yacare XV","Yacare XV":"Yacare XV",
    "Peñarol":"Peñarol","Peñarol Rugby":"Peñarol",
}
def normalize(name): return TEAM_NAME_MAP.get(name, name)

def find_espn_scoreboard():
    for slug in ESPN_SLUGS:
        url = f"https://site.api.espn.com/apis/site/v2/sports/rugby/{slug}/scoreboard"
        try:
            r = requests.get(url, headers=ESPN_HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if "events" in data:
                    print(f"✓ ESPN slug: {slug} | eventos: {len(data['events'])}")
                    return data, slug
        except Exception as e:
            print(f"  {slug} → {e}")
    return None, None

def find_espn_standings(slug):
    url = f"https://site.api.espn.com/apis/site/v2/sports/rugby/{slug}/standings"
    try:
        r = requests.get(url, headers=ESPN_HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
        print(f"  Standings HTTP {r.status_code}")
    except Exception as e:
        print(f"  Standings error: {e}")
    return None

def parse_events(data):
    results = []
    for event in data.get("events", []):
        comp = (event.get("competitions") or [{}])[0]
        status_type = comp.get("status", {}).get("type", {})
        completed = status_type.get("completed", False)
        state = status_type.get("name", "")
        if state in ("STATUS_FINAL", "STATUS_FULL_TIME", "STATUS_END_PERIOD"):
            completed = True
        competitors = comp.get("competitors", [])
        if len(competitors) < 2: continue
        home = next((c for c in competitors if c.get("homeAway")=="home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway")=="away"), competitors[1])
        home_name = normalize(home.get("team",{}).get("displayName",""))
        away_name = normalize(away.get("team",{}).get("displayName",""))
        try:
            hs = int(float(home.get("score",0))) if completed else None
            as_ = int(float(away.get("score",0))) if completed else None
        except: hs = as_ = None
        date_str = event.get("date","")[:10]
        print(f"  {home_name} vs {away_name} | state={state} | completed={completed} | {hs}-{as_}")
        results.append({"id":event.get("id"),"date":date_str,"home":home_name,"away":away_name,"hs":hs,"as":as_,"played":completed})
    return results

def parse_standings(data):
    standings = []
    try:
        print(f"  Standings top keys: {list(data.keys())[:8]}")
        # Try multiple structures
        groups = (data.get("standings") or {}).get("groups", [])
        if not groups:
            for child in data.get("children", []):
                groups = (child.get("standings") or {}).get("groups", [])
                if groups: break
        if not groups:
            groups = data.get("groups", [])
        if not groups:
            print("  No groups found in standings")
            return []
        entries = groups[0].get("standings",{}).get("entries", groups[0].get("entries",[]))
        print(f"  Entries: {len(entries)}")
        for entry in entries:
            name = normalize(entry.get("team",{}).get("displayName",""))
            stats = {s["name"]: s.get("value",0) for s in entry.get("stats",[])}
            print(f"  {name}: {list(stats.keys())[:6]}")
            standings.append({
                "name": name,
                "pts": int(float(stats.get("points", stats.get("totalPoints", stats.get("pts",0))))),
                "pj":  int(float(stats.get("gamesPlayed", stats.get("played",0)))),
                "g":   int(float(stats.get("wins", stats.get("won",0)))),
                "e":   int(float(stats.get("ties", stats.get("draws", stats.get("drawn",0))))),
                "p":   int(float(stats.get("losses", stats.get("lost",0)))),
                "pf":  int(float(stats.get("pointsFor", stats.get("runsScored",0)))),
                "pc":  int(float(stats.get("pointsAgainst", stats.get("runsAgainst",0)))),
                "bp":  int(float(stats.get("bonusPoints", stats.get("triesBonus",0)))),
                "bf":  int(float(stats.get("losingBonusPoints", stats.get("losingBonus",0)))),
            })
    except Exception as e:
        import traceback; traceback.print_exc()
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

    print("→ Consultando ESPN scoreboard...")
    scoreboard, slug = find_espn_scoreboard()
    if not scoreboard:
        print("✗ No se pudo conectar con ESPN"); sys.exit(1)

    events = parse_events(scoreboard)
    played = [e for e in events if e["played"]]
    print(f"\n  Total eventos: {len(events)} | Jugados: {len(played)}")

    print("\n→ Consultando ESPN standings...")
    standings_data = find_espn_standings(slug)
    standings = parse_standings(standings_data) if standings_data else []

    print("\n→ Escribiendo a Firebase...")
    if played:
        matches_data = {f"{e['home'].replace(' ','_')}_vs_{e['away'].replace(' ','_')}_{e['date']}": e for e in played}
        ok = firebase_put("superrugby/matches", matches_data)
        print(f"  Partidos ({len(played)}) → {'✓' if ok else '✗'}")

    if standings:
        ok = firebase_put("superrugby/standings", {t["name"]: t for t in standings})
        print(f"  Standings ({len(standings)} equipos) → {'✓' if ok else '✗'}")

    ok = firebase_patch("superrugby/meta", {
        "lastUpdate": datetime.now(timezone.utc).isoformat(),
        "matchesPlayed": len(played),
        "source": f"espn/{slug}",
    })
    print(f"  Metadata → {'✓' if ok else '✗'}")
    print("\n✓ Listo\n")

if __name__ == "__main__":
    main()
