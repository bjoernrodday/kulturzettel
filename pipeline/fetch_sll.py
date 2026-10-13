"""Holt die Termine aus "Stadt, Land, Leben" (api.region-bayreuth.de) für die kommenden
zwei Monate, nur Stadt Bayreuth, und schreibt sie kompakt nach pipeline/sll.json.
Läuft nachts als GitHub Action; der Kulturzettel-Lauf liest die Datei, statt die API
selbst abzufragen. Rohdaten, keine Bewertung: Auswahl, Kategorien und eigene Texte
macht der Kulturzettel-Lauf."""
import json, re, sys, time, datetime, calendar, urllib.request, urllib.parse, zoneinfo, os

API = "https://api.region-bayreuth.de/event-management/events"
UA = {"User-Agent": "kulturzettel-bayreuth.de (privater Kulturkalender; Kontakt: siehe Impressum)",
      "Accept": "application/json"}
DROP = re.compile(r"image|media|picture|photo|gallery|geo|coordinat|latitude|longitude|seo|thumbnail|logo|video", re.I)
OUT = os.path.join(os.path.dirname(__file__), "sll.json")

def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                print("FEHLER", url, e, file=sys.stderr); return None
            time.sleep(2 * (i + 1))

def items_of(d):
    if isinstance(d, list): return d
    if isinstance(d, dict):
        for k in ("items", "content", "events", "data", "results"):
            if isinstance(d.get(k), list): return d[k]
        for v in d.values():
            if isinstance(v, list) and v and isinstance(v[0], dict): return v
    return []

def total_of(d):
    if isinstance(d, dict):
        for k in ("totalItems", "totalElements", "total"):
            if isinstance(d.get(k), int): return d[k]
    return None

def trim(x):
    if isinstance(x, dict):
        return {k: trim(v) for k, v in x.items() if not DROP.search(k) and v not in (None, "", [], {})}
    if isinstance(x, list):
        return [trim(v) for v in x]
    return x

def city(e):
    dc = e.get("districtCity") or {}
    return (dc.get("city") if isinstance(dc, dict) else dc) or ""

def slug(e):
    if e.get("slug"): return str(e["slug"])
    link = e.get("detailLink") or ""
    return link.rstrip("/").split("/")[-1] if link else None

def plus2m(d):
    m, y = d.month + 2, d.year
    if m > 12: m, y = m - 12, y + 1
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))

today = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Berlin")).date()
end = plus2m(today)
series = {}   # slug -> Eintrag mit Liste der Daten
day, failed = today, 0
while day <= end:
    page = 0
    while True:
        q = urllib.parse.urlencode({"from": day.isoformat(), "to": day.isoformat(), "size": 50, "page": page})
        d = get(f"{API}/search?{q}")
        if d is None: failed += 1; break
        its = items_of(d)
        for e in its:
            if city(e).strip().lower() != "bayreuth": continue
            s = slug(e) or f"{e.get('title')}|{day}"
            if s not in series:
                series[s] = {"slug": s, "dates": [], "item": trim(e)}
            di = e.get("dateInfo") if isinstance(e.get("dateInfo"), dict) else {}
            when = day.isoformat() + (" " + str(di["start"]) if di.get("start") else "")
            if when not in series[s]["dates"]:
                series[s]["dates"].append(when)
        tot = total_of(d)
        page += 1
        if not its or (tot is not None and page * 50 >= tot) or page > 20: break
        time.sleep(0.3)
    day += datetime.timedelta(days=1)
    time.sleep(0.3)

for s, v in list(series.items())[:900]:
    if v["slug"] and "|" not in v["slug"]:
        det = get(f"{API}/details/{urllib.parse.quote(v['slug'])}")
        if det is not None: v["detail"] = trim(det)
        time.sleep(0.3)

events = sorted(series.values(), key=lambda v: (v["dates"][0], v["item"].get("title", "")))
data = {"source": "Stadt, Land, Leben (api.region-bayreuth.de)", "from": today.isoformat(), "to": end.isoformat(),
        "count": len(events), "failed_requests": failed, "events": events}
old = None
if os.path.exists(OUT):
    try: old = json.load(open(OUT, encoding="utf-8"))
    except Exception: pass
if old and {k: v for k, v in old.items() if k != "fetched"} == data:
    print("unverändert", len(events)); sys.exit(0)
data = {"fetched": datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Berlin")).isoformat(timespec="minutes"), **data}
if len(events) == 0:
    print("keine Termine erhalten – Datei bleibt unverändert", file=sys.stderr); sys.exit(1)
json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("geschrieben", len(events), "Serien/Termine,", failed, "fehlgeschlagene Abrufe")
