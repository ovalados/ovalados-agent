#!/usr/bin/env python3
"""
Ovalados Agent — Fetcher multi-torneo
- Super Rugby Américas: scraping nota ESPN  → data/superrugby.json
- Seis Naciones:        scraping nota ESPN  → data/seisNaciones.json
- URBA (todos):         API oficial URBA    → data/urba-{key}.json / data/juvenil-*.json
Todos los JSON se suben automáticamente al repo ovalados-sitio en GitHub.
"""
import requests, re, os, json, base64
from datetime import datetime, timezone

FIREBASE_URL    = os.environ.get("FIREBASE_URL")
FIREBASE_SECRET = os.environ.get("FIREBASE_SECRET")
GH_TOKEN        = os.environ.get("GH_TOKEN")
GH_REPO = "ovalados/ovalados-ysisi"

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
SN_URL        = "https://www.espn.com.ar/rugby/nota/_/id/15203928/rugby-seis-naciones-fixture-resultados-tabla-posiciones-2026-francia-irlanda-gales-escocia-inglaterra-italia-partidos"
URBA_API_BASE = "https://api.urba.org.ar/api/championship"

# ── Torneos URBA activos 2026 — lista completa ────────────────────────────────
URBA_TORNEOS = [

    # ── TOP 14 y sus divisiones ───────────────────────────────────────────────
    {"id": "2025176", "nombre": "Top 14",            "json_file": "data/urba.json",                  "firebase_key": "urbaTop14"},
    {"id": "2025184", "nombre": "Intermedia",         "json_file": "data/urba-intermedia.json",       "firebase_key": "urbaIntermedia"},
    {"id": "2025185", "nombre": "Pre-Inter A",        "json_file": "data/urba-preinter-a.json",       "firebase_key": "urbaPreInterA"},
    {"id": "2025186", "nombre": "Pre-Inter B",        "json_file": "data/urba-preinter-b.json",       "firebase_key": "urbaPreInterB"},
    {"id": "2025197", "nombre": "Pre-Inter C",        "json_file": "data/urba-preinter-c.json",       "firebase_key": "urbaPreInterC"},
    {"id": "2025198", "nombre": "Pre-Inter D",        "json_file": "data/urba-preinter-d.json",       "firebase_key": "urbaPreInterD"},
    {"id": "2025200", "nombre": "Pre-Inter E",        "json_file": "data/urba-preinter-e.json",       "firebase_key": "urbaPreInterE"},
    {"id": "2025201", "nombre": "Pre-Inter F",        "json_file": "data/urba-preinter-f.json",       "firebase_key": "urbaPreInterF"},
    {"id": "2025206", "nombre": "M22",                "json_file": "data/urba-m22.json",              "firebase_key": "urbaM22"},

    # ── PRIMERA A y sus divisiones ────────────────────────────────────────────
    {"id": "2025177", "nombre": "Primera A",          "json_file": "data/urba-primera-a.json",        "firebase_key": "urbaPrimeraA"},
    {"id": "2025187", "nombre": "1A Intermedia",      "json_file": "data/primera-a-intermedia.json",  "firebase_key": "urba1AIntermedia"},
    {"id": "2025188", "nombre": "1A Pre-Inter A",     "json_file": "data/primera-a-preinter-a.json",  "firebase_key": "urba1APreInterA"},
    {"id": "2025189", "nombre": "1A Pre-Inter B",     "json_file": "data/primera-a-preinter-b.json",  "firebase_key": "urba1APreInterB"},
    {"id": "2025202", "nombre": "1A Pre-Inter C",     "json_file": "data/primera-a-preinter-c.json",  "firebase_key": "urba1APreInterC"},
    {"id": "2025203", "nombre": "1A Pre-Inter D",     "json_file": "data/primera-a-preinter-d.json",  "firebase_key": "urba1APreInterD"},

    # ── PRIMERA B y sus divisiones ────────────────────────────────────────────
    {"id": "2025178", "nombre": "Primera B",          "json_file": "data/urba-primera-b.json",        "firebase_key": "urbaPrimeraB"},
    {"id": "2025190", "nombre": "1B Intermedia",      "json_file": "data/primera-b-intermedia.json",  "firebase_key": "urba1BIntermedia"},
    {"id": "2025191", "nombre": "1B Pre-Inter A",     "json_file": "data/primera-b-preinter-a.json",  "firebase_key": "urba1BPreInterA"},
    {"id": "2025192", "nombre": "1B Pre-Inter B",     "json_file": "data/primera-b-preinter-b.json",  "firebase_key": "urba1BPreInterB"},
    {"id": "2025204", "nombre": "1B Pre-Inter C",     "json_file": "data/primera-b-preinter-c.json",  "firebase_key": "urba1BPreInterC"},

    # ── PRIMERA C y sus divisiones ────────────────────────────────────────────
    {"id": "2025179", "nombre": "Primera C",          "json_file": "data/urba-primera-c.json",        "firebase_key": "urbaPrimeraC"},
    {"id": "2025193", "nombre": "1C Intermedia",      "json_file": "data/primera-c-intermedia.json",  "firebase_key": "urba1CIntermedia"},
    {"id": "2025195", "nombre": "1C Pre-Inter A",     "json_file": "data/primera-c-preinter-a.json",  "firebase_key": "urba1CPreInterA"},
    {"id": "2025205", "nombre": "1C Pre-Inter B",     "json_file": "data/primera-c-preinter-b.json",  "firebase_key": "urba1CPreInterB"},

    # ── SEGUNDA y TERCERA ─────────────────────────────────────────────────────
    {"id": "2025180", "nombre": "Segunda Superior",   "json_file": "data/urba-segunda.json",          "firebase_key": "urbaSegunda"},
    {"id": "2025196", "nombre": "Segunda Intermedia", "json_file": "data/segunda-intermedia.json",    "firebase_key": "urbaSegundaIntermedia"},
    {"id": "2025181", "nombre": "Tercera Superior",   "json_file": "data/urba-tercera.json",          "firebase_key": "urbaTercera"},
    {"id": "2025199", "nombre": "Tercera Intermedia", "json_file": "data/tercera-intermedia.json",    "firebase_key": "urbaTerceraIntermedia"},

    # ── M19 (15 divisiones) ───────────────────────────────────────────────────
    {"id": "2025213", "nombre": "M19 N1-G2-ZA-EqA",  "json_file": "data/juvenil-m19-n1-g2-za-eqa.json",  "firebase_key": "urbaM19N1ZaEqA"},
    {"id": "2025214", "nombre": "M19 N1-G2-ZA-EqB",  "json_file": "data/juvenil-m19-n1-g2-za-eqb.json",  "firebase_key": "urbaM19N1ZaEqB"},
    {"id": "2025215", "nombre": "M19 N1-G2-ZB-EqA",  "json_file": "data/juvenil-m19-n1-g2-zb-eqa.json",  "firebase_key": "urbaM19N1ZbEqA"},
    {"id": "2025216", "nombre": "M19 N1-G2-ZB-EqB",  "json_file": "data/juvenil-m19-n1-g2-zb-eqb.json",  "firebase_key": "urbaM19N1ZbEqB"},
    {"id": "2025217", "nombre": "M19 N2-G2-ZC-EqA",  "json_file": "data/juvenil-m19-n2-g2-zc-eqa.json",  "firebase_key": "urbaM19N2ZcEqA"},
    {"id": "2025218", "nombre": "M19 N2-G2-ZC-EqB",  "json_file": "data/juvenil-m19-n2-g2-zc-eqb.json",  "firebase_key": "urbaM19N2ZcEqB"},
    {"id": "2025219", "nombre": "M19 N2-G2-ZD-EqA",  "json_file": "data/juvenil-m19-n2-g2-zd-eqa.json",  "firebase_key": "urbaM19N2ZdEqA"},
    {"id": "2025220", "nombre": "M19 N2-G2-ZD-EqB",  "json_file": "data/juvenil-m19-n2-g2-zd-eqb.json",  "firebase_key": "urbaM19N2ZdEqB"},
    {"id": "2025221", "nombre": "M19 G2-ZDes-EqB",   "json_file": "data/juvenil-m19-g2-zdes-eqb.json",   "firebase_key": "urbaM19G2ZDesEqB"},
    {"id": "2025222", "nombre": "M19 Form-ZB",        "json_file": "data/juvenil-m19-form-zb.json",        "firebase_key": "urbaM19FormZB"},
    {"id": "2025223", "nombre": "M19 Form-ZC",        "json_file": "data/juvenil-m19-form-zc.json",        "firebase_key": "urbaM19FormZC"},
    {"id": "2025224", "nombre": "M19 G1-ZA",          "json_file": "data/juvenil-m19-g1-za.json",          "firebase_key": "urbaM19G1ZA"},
    {"id": "2025225", "nombre": "M19 G1-ZB",          "json_file": "data/juvenil-m19-g1-zb.json",          "firebase_key": "urbaM19G1ZB"},
    {"id": "2025226", "nombre": "M19 Form-ZA",        "json_file": "data/juvenil-m19-form-za.json",        "firebase_key": "urbaM19FormZA"},
    {"id": "2025227", "nombre": "M19 G2-ZDes-EqA",   "json_file": "data/juvenil-m19-g2-zdes-eqa.json",   "firebase_key": "urbaM19G2ZDesEqA"},

    # ── M17 (12 divisiones) ───────────────────────────────────────────────────
    {"id": "2025228", "nombre": "M17 Form-ZA",        "json_file": "data/juvenil-m17-form-za.json",        "firebase_key": "urbaM17FormZA"},
    {"id": "2025229", "nombre": "M17 Form-ZB",        "json_file": "data/juvenil-m17-form-zb.json",        "firebase_key": "urbaM17FormZB"},
    {"id": "2025230", "nombre": "M17 Form-ZC",        "json_file": "data/juvenil-m17-form-zc.json",        "firebase_key": "urbaM17FormZC"},
    {"id": "2025231", "nombre": "M17 N1-G2-ZA-EqA",  "json_file": "data/juvenil-m17-n1-g2-za-eqa.json",  "firebase_key": "urbaM17N1ZaEqA"},
    {"id": "2025232", "nombre": "M17 N1-G2-ZA-EqB",  "json_file": "data/juvenil-m17-n1-g2-za-eqb.json",  "firebase_key": "urbaM17N1ZaEqB"},
    {"id": "2025233", "nombre": "M17 N1-G2-ZB-EqA",  "json_file": "data/juvenil-m17-n1-g2-zb-eqa.json",  "firebase_key": "urbaM17N1ZbEqA"},
    {"id": "2025234", "nombre": "M17 N1-G2-ZB-EqB",  "json_file": "data/juvenil-m17-n1-g2-zb-eqb.json",  "firebase_key": "urbaM17N1ZbEqB"},
    {"id": "2025235", "nombre": "M17 N2-G2-ZC-EqA",  "json_file": "data/juvenil-m17-n2-g2-zc-eqa.json",  "firebase_key": "urbaM17N2ZcEqA"},
    {"id": "2025236", "nombre": "M17 N2-G2-ZC-EqB",  "json_file": "data/juvenil-m17-n2-g2-zc-eqb.json",  "firebase_key": "urbaM17N2ZcEqB"},
    {"id": "2025237", "nombre": "M17 G1-ZA",          "json_file": "data/juvenil-m17-g1-za.json",          "firebase_key": "urbaM17G1ZA"},
    {"id": "2025238", "nombre": "M17 G1-ZB",          "json_file": "data/juvenil-m17-g1-zb.json",          "firebase_key": "urbaM17G1ZB"},
    {"id": "2025239", "nombre": "M17 G1-ZC",          "json_file": "data/juvenil-m17-g1-zc.json",          "firebase_key": "urbaM17G1ZC"},

    # ── M16 (12 divisiones) ───────────────────────────────────────────────────
    {"id": "2025240", "nombre": "M16 Form-ZB",        "json_file": "data/juvenil-m16-form-zb.json",        "firebase_key": "urbaM16FormZB"},
    {"id": "2025241", "nombre": "M16 Form-ZA",        "json_file": "data/juvenil-m16-form-za.json",        "firebase_key": "urbaM16FormZA"},
    {"id": "2025242", "nombre": "M16 G1-ZB",          "json_file": "data/juvenil-m16-g1-zb.json",          "firebase_key": "urbaM16G1ZB"},
    {"id": "2025243", "nombre": "M16 N1-G2-ZA-EqA",  "json_file": "data/juvenil-m16-n1-g2-za-eqa.json",  "firebase_key": "urbaM16N1ZaEqA"},
    {"id": "2025244", "nombre": "M16 N1-G2-ZA-EqB",  "json_file": "data/juvenil-m16-n1-g2-za-eqb.json",  "firebase_key": "urbaM16N1ZaEqB"},
    {"id": "2025245", "nombre": "M16 N1-G2-ZB-EqA",  "json_file": "data/juvenil-m16-n1-g2-zb-eqa.json",  "firebase_key": "urbaM16N1ZbEqA"},
    {"id": "2025246", "nombre": "M16 N1-G2-ZB-EqB",  "json_file": "data/juvenil-m16-n1-g2-zb-eqb.json",  "firebase_key": "urbaM16N1ZbEqB"},
    {"id": "2025247", "nombre": "M16 N2-G2-ZC-EqA",  "json_file": "data/juvenil-m16-n2-g2-zc-eqa.json",  "firebase_key": "urbaM16N2ZcEqA"},
    {"id": "2025248", "nombre": "M16 N2-G2-ZC-EqB",  "json_file": "data/juvenil-m16-n2-g2-zc-eqb.json",  "firebase_key": "urbaM16N2ZcEqB"},
    {"id": "2025249", "nombre": "M16 G2-ZDes-EqA",   "json_file": "data/juvenil-m16-g2-zdes-eqa.json",   "firebase_key": "urbaM16G2ZDesEqA"},
    {"id": "2025250", "nombre": "M16 G2-ZDes-EqB",   "json_file": "data/juvenil-m16-g2-zdes-eqb.json",   "firebase_key": "urbaM16G2ZDesEqB"},
    {"id": "2025251", "nombre": "M16 G1-ZA",          "json_file": "data/juvenil-m16-g1-za.json",          "firebase_key": "urbaM16G1ZA"},

    # ── M15 (10 divisiones) ───────────────────────────────────────────────────
    {"id": "2025252", "nombre": "M15 G1-ZB",          "json_file": "data/juvenil-m15-g1-zb.json",          "firebase_key": "urbaM15G1ZB"},
    {"id": "2025253", "nombre": "M15 Form-ZA",        "json_file": "data/juvenil-m15-form-za.json",        "firebase_key": "urbaM15FormZA"},
    {"id": "2025254", "nombre": "M15 Form-ZB",        "json_file": "data/juvenil-m15-form-zb.json",        "firebase_key": "urbaM15FormZB"},
    {"id": "2025255", "nombre": "M15 N1-G2-ZA-EqA",  "json_file": "data/juvenil-m15-n1-g2-za-eqa.json",  "firebase_key": "urbaM15N1ZaEqA"},
    {"id": "2025256", "nombre": "M15 N1-G2-ZA-EqB",  "json_file": "data/juvenil-m15-n1-g2-za-eqb.json",  "firebase_key": "urbaM15N1ZaEqB"},
    {"id": "2025257", "nombre": "M15 N1-G2-ZB-EqA",  "json_file": "data/juvenil-m15-n1-g2-zb-eqa.json",  "firebase_key": "urbaM15N1ZbEqA"},
    {"id": "2025258", "nombre": "M15 N1-G2-ZB-EqB",  "json_file": "data/juvenil-m15-n1-g2-zb-eqb.json",  "firebase_key": "urbaM15N1ZbEqB"},
    {"id": "2025259", "nombre": "M15 G2-ZDes-EqA",   "json_file": "data/juvenil-m15-g2-zdes-eqa.json",   "firebase_key": "urbaM15G2ZDesEqA"},
    {"id": "2025260", "nombre": "M15 G2-ZDes-EqB",   "json_file": "data/juvenil-m15-g2-zdes-eqb.json",   "firebase_key": "urbaM15G2ZDesEqB"},
    {"id": "2025261", "nombre": "M15 G1-ZA",          "json_file": "data/juvenil-m15-g1-za.json",          "firebase_key": "urbaM15G1ZA"},
]

# ── SRA / SN teams ────────────────────────────────────────────────────────────
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
SN_TEAMS = ["Francia","Escocia","Irlanda","Italia","Inglaterra","Gales"]
SN_ALIASES = {
    "france":"Francia","scotland":"Escocia","ireland":"Irlanda",
    "italy":"Italia","england":"Inglaterra","wales":"Gales",
    "francia":"Francia","escocia":"Escocia","irlanda":"Irlanda",
    "italia":"Italia","inglaterra":"Inglaterra","gales":"Gales",
}

def norm_sra(name): return SRA_ALIASES.get(name.lower().strip(), name.strip())
def norm_sn(name):  return SN_ALIASES.get(name.lower().strip(), name.strip())

# ── GitHub ────────────────────────────────────────────────────────────────────
def github_push(path, content_str, message):
    if not GH_TOKEN:
        print("  ⚠ GH_TOKEN no configurado"); return False
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    api_url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    sha = None
    try:
        r = requests.get(api_url, headers=headers, timeout=10)
        if r.status_code == 200:
            sha = r.json().get("sha")
    except Exception:
        pass
    payload = {
        "message": message,
        "content": base64.b64encode(content_str.encode()).decode(),
    }
    if sha:
        payload["sha"] = sha
    try:
        r = requests.put(api_url, headers=headers, json=payload, timeout=15)
        ok = r.status_code in (200, 201)
        print(f"  GitHub {path} → {'✓' if ok else '✗ ' + str(r.status_code)}")
        return ok
    except Exception as e:
        print(f"  GitHub error: {e}"); return False

# ── Firebase ──────────────────────────────────────────────────────────────────
def firebase_put(path, data):
    if not FIREBASE_URL or not FIREBASE_SECRET:
        return False
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

# ── Scraper ESPN ──────────────────────────────────────────────────────────────
def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS_HTML, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  Error fetching {url}: {e}"); return ""

def scrape_scores(url, teams_list, normalize_fn):
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
        if len(cells) == 4:   _, home_cell, score_cell, away_cell = cells
        elif len(cells) == 3: home_cell, score_cell, away_cell = cells
        else: continue
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

# ── Super Rugby Américas ──────────────────────────────────────────────────────
def fetch_sra():
    print("\n── SUPER RUGBY AMÉRICAS ─────────────────────────")
    results = scrape_scores(SRA_URL, SRA_TEAMS, norm_sra)
    print(f"  Total resultados: {len(results)}")
    now = datetime.now(timezone.utc).isoformat()

    current = {}
    if GH_TOKEN:
        try:
            headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
            r = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/data/superrugby.json", headers=headers, timeout=10)
            if r.status_code == 200:
                current = json.loads(base64.b64decode(r.json()["content"]).decode())
        except Exception: pass

    matches = current.get("matches", {})
    teams_data = current.get("teams", [])

    for r in results:
        found = False
        for rnd_key in sorted(matches.keys(), key=lambda x: int(x)):
            if found: break
            rnd = matches[rnd_key]
            for m in rnd.get("ms", []):
                if m["home"] == r["home"] and m["away"] == r["away"] and not m.get("played"):
                    m["hs"] = r["hs"]; m["as"] = r["as"]; m["played"] = True
                    found = True
                    break

    output = {**current, "matches": matches, "teams": teams_data,
              "lastUpdate": now, "matchesScraped": len(results)}
    github_push("data/superrugby.json", json.dumps(output, ensure_ascii=False, indent=2),
                f"bot: SRA update {now[:10]}")
    firebase_patch("superrugby/meta", {"lastUpdate": now, "matchesFound": len(results), "source": "espn-nota-sra"})

# ── Seis Naciones ─────────────────────────────────────────────────────────────
def fetch_seis_naciones():
    print("\n── SEIS NACIONES ────────────────────────────────")
    results = scrape_scores(SN_URL, SN_TEAMS, norm_sn)
    print(f"  Total resultados: {len(results)}")
    now = datetime.now(timezone.utc).isoformat()

    current = {}
    if GH_TOKEN:
        try:
            headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
            r = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/data/seisNaciones.json", headers=headers, timeout=10)
            if r.status_code == 200:
                current = json.loads(base64.b64decode(r.json()["content"]).decode())
        except Exception: pass

    matches = current.get("matches", {})
    for r in results:
        found = False
        for rnd_key in sorted(matches.keys(), key=lambda x: int(x)):
            if found: break
            rnd = matches[rnd_key]
            for m in rnd.get("ms", []):
                if m["home"] == r["home"] and m["away"] == r["away"] and not m.get("played"):
                    m["hs"] = r["hs"]; m["as"] = r["as"]; m["played"] = True
                    found = True
                    break

    output = {**current, "matches": matches,
              "lastUpdate": now, "matchesScraped": len(results)}
    github_push("data/seisNaciones.json", json.dumps(output, ensure_ascii=False, indent=2),
                f"bot: SN update {now[:10]}")
    firebase_patch("seisNaciones/meta", {"lastUpdate": now, "matchesFound": len(results), "source": "espn-nota-sn"})

# ── URBA — función genérica ───────────────────────────────────────────────────
def fetch_urba_torneo(torneo):
    nombre       = torneo["nombre"]
    firebase_key = torneo["firebase_key"]
    json_file    = torneo["json_file"]
    url          = f"{URBA_API_BASE}/{torneo['id']}"

    print(f"\n── URBA {nombre.upper()} {'─'*(38 - len(nombre))}")
    results = []
    rounds_data = {}

    try:
        r = requests.get(url, headers=HEADERS_API, timeout=15)
        r.raise_for_status()
        data = r.json()
        championship = data.get("championship", [{}])[0]
        rounds = championship.get("rounds", [])
        teams_raw = championship.get("teams", [])

        for rnd in rounds:
            num = rnd["name"].split()[-1]
            ms = []
            for match in rnd.get("matches", []):
                home = match["local_team"]["name"].strip()
                away = match["visit_team"]["name"].strip()
                played = match.get("fulfilled", False)
                m = {"home": home, "away": away, "played": played}
                if played:
                    m["hs"] = match["local_team_score"]
                    m["as"] = match["visit_team_score"]
                    if match.get("local_team_offensive_bonus"):  m["bp_home"] = True
                    if match.get("visit_team_offensive_bonus"):  m["bp_away"] = True
                    if match.get("local_team_defensive_bonus"):  m["bf_home"] = True
                    if match.get("visit_team_defensive_bonus"):  m["bf_away"] = True
                    results.append({"home": home, "away": away,
                                    "hs": m["hs"], "as": m["as"], "played": True})
                    print(f"  ✓ [Fecha {num}] {home} {m['hs']}–{m['as']} {away}")
                ms.append(m)
            date_str = rnd.get("date", "")
            rounds_data[num] = {"date": date_str, "ms": ms}

        # Calcular tabla desde resultados
        team_stats = {}
        for t in teams_raw:
            name = t["name"].strip()
            team_stats[name] = {"name": name, "pts": 0, "pj": 0, "g": 0, "e": 0,
                                "p": 0, "pf": 0, "pc": 0, "bp": 0, "bf": 0, "form": []}

        for rnd_key, rnd in rounds_data.items():
            for match in rnd.get("ms", []):
                if not match.get("played"): continue
                h = team_stats.get(match["home"])
                a = team_stats.get(match["away"])
                if not h or not a: continue
                hs, as_ = match["hs"], match["as"]
                h["pj"] += 1; a["pj"] += 1
                h["pf"] += hs; h["pc"] += as_
                a["pf"] += as_; a["pc"] += hs
                if hs > as_:
                    h["g"] += 1; h["pts"] += 4; a["p"] += 1
                    h["form"].append("w"); a["form"].append("l")
                elif hs < as_:
                    a["g"] += 1; a["pts"] += 4; h["p"] += 1
                    h["form"].append("l"); a["form"].append("w")
                else:
                    h["e"] += 1; a["e"] += 1; h["pts"] += 2; a["pts"] += 2
                    h["form"].append("d"); a["form"].append("d")
                if match.get("bp_home"): h["pts"] += 1; h["bp"] += 1
                if match.get("bp_away"): a["pts"] += 1; a["bp"] += 1
                if match.get("bf_home"): h["pts"] += 1; h["bf"] += 1
                if match.get("bf_away"): a["pts"] += 1; a["bf"] += 1

        teams_list = [dict(v, form=v["form"][-5:]) for v in team_stats.values()]

    except Exception as e:
        print(f"  Error API URBA ({nombre}): {e}")
        return

    print(f"  Total jugados: {len(results)}")
    now = datetime.now(timezone.utc).isoformat()

    output = {
        "teams":          teams_list,
        "matches":        rounds_data,
        "lastUpdate":     now,
        "matchesScraped": len(results),
        "championshipId": torneo["id"],
        "nombre":         nombre,
    }
    github_push(json_file, json.dumps(output, ensure_ascii=False, indent=2),
                f"bot: URBA {nombre} update {now[:10]}")
    firebase_patch(f"{firebase_key}/meta", {
        "lastUpdate": now, "matchesFound": len(results),
        "source": "api-urba-org-ar", "championshipId": torneo["id"],
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
