"""Holt die Besucherstatistik des Kulturzettels von GoatCounter (brodday.goatcounter.com)
und schreibt eine kompakte Zusammenfassung nach pipeline/statistik.json.
Läuft nachts als GitHub Action. Der API-Schlüssel (nur Leserecht) kommt aus dem
Repository-Secret GOATCOUNTER_TOKEN und steht nirgends im Code.
Nur Summen, keine Daten über einzelne Personen."""
import json, os, sys, time, datetime, urllib.request, urllib.parse, zoneinfo

BASE = "https://brodday.goatcounter.com/api/v0"
TOKEN = os.environ.get("GOATCOUNTER_TOKEN", "").strip()
OUT = os.path.join(os.path.dirname(__file__), "statistik.json")
if not TOKEN:
    print("GOATCOUNTER_TOKEN fehlt", file=sys.stderr); sys.exit(1)

def api(path, **q):
    url = f"{BASE}/{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                time.sleep(0.4)
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read()[:200]
            if e.code in (429, 404, 500, 502, 503) and i < 2:
                # 404 kam am 22.10.2026 einmalig bei stats/total (gestern) – kurz warten und erneut versuchen
                print("WIEDERHOLE", path, e.code, body, file=sys.stderr); time.sleep(3); continue
            print("FEHLER", path, e.code, body, file=sys.stderr); return None
        except Exception as e:
            print("FEHLER", path, e, file=sys.stderr); time.sleep(2)
    return None

tz = zoneinfo.ZoneInfo("Europe/Berlin")
today = datetime.datetime.now(tz).date()
yday = today - datetime.timedelta(days=1)

def rng(days):
    # Volle UTC-Tage als Zeitpunkte angeben, damit alle Endpunkte denselben Zeitraum nutzen
    start = today - datetime.timedelta(days=days)
    return {"start": f"{start.isoformat()}T00:00:00Z", "end": f"{yday.isoformat()}T23:59:59Z"}

def block(days, details=False):
    r = rng(days)
    tot = api("stats/total", **r) or {}
    hits = api("stats/hits", limit=15, **r) or {}
    refs = api("stats/toprefs", limit=10, **r) or {}
    out = {"von": r["start"][:10], "bis": yday.isoformat(),
           "besucher": tot.get("total"),
           "seiten": [{"pfad": h.get("path"), "titel": h.get("title"), "besucher": h.get("count")}
                      for h in hits.get("hits", [])],
           "herkunft": [{"name": s.get("name") or "(direkt)", "besucher": s.get("count")}
                        for s in refs.get("stats", [])]}
    pages = (("browsers", "browser"), ("systems", "systeme"), ("sizes", "bildschirm"), ("locations", "laender")) if details else ()
    for page, key in pages:
        d = api(f"stats/{page}", limit=8, **r) or {}
        out[key] = [{"name": s.get("name"), "besucher": s.get("count")} for s in d.get("stats", [])]
    return out, tot

gestern, _ = block(1)
woche, _ = block(7)
monat, tot90 = block(28, details=True)
verlauf_raw = api("stats/total", **rng(90)) or {}
heute = api("stats/total", start=f"{today.isoformat()}T00:00:00Z", end=f"{today.isoformat()}T23:59:59Z") or {}
verlauf = [{"tag": s.get("day"), "besucher": s.get("daily")} for s in verlauf_raw.get("stats", [])]
if gestern.get("besucher") is None:
    # Ersatz, falls die Tagesabfrage scheitert: Wert für gestern aus dem 90-Tage-Verlauf
    v = next((x["besucher"] for x in verlauf if x["tag"] == yday.isoformat()), None)
    if v is not None:
        gestern["besucher"] = v; gestern["hinweis"] = "besucher aus verlauf_90_tage übernommen (Tagesabfrage fehlgeschlagen)"

data = {"quelle": "GoatCounter (brodday.goatcounter.com), Zahlen = eindeutige Besucher laut GoatCounter",
        "abgerufen": datetime.datetime.now(tz).isoformat(timespec="minutes"),
        "hinweis": "browser/systeme/bildschirm/laender nur bei letzte_28_tage; diese GoatCounter-Endpunkte halten den Zeitraum nicht exakt ein, daher nur als grobe Verteilung lesen",
        "heute_bis_abruf": heute.get("total"), "gestern": gestern, "letzte_7_tage": woche, "letzte_28_tage": monat, "verlauf_90_tage": verlauf}
if gestern.get("besucher") is None and woche.get("besucher") is None:
    print("keine Daten erhalten – Datei bleibt unverändert", file=sys.stderr); sys.exit(1)
json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("geschrieben:", gestern.get("besucher"), "gestern,", woche.get("besucher"), "in 7 Tagen")
