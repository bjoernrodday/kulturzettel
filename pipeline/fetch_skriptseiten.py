"""Rendert Veranstalterseiten, deren Terminlisten erst per Skript laden, und schreibt den
sichtbaren Text samt Links nach pipeline/skriptseiten.json. Läuft nachts als GitHub Action;
der Kulturzettel-Lauf liest die Datei, statt die Seiten selbst abzurufen. Rohdaten, keine
Bewertung: Auswahl, Kategorien und eigene Texte macht der Kulturzettel-Lauf.

Regeln: robots.txt wird vor jedem Abruf geprüft und befolgt (auch für die Zieladresse nach
einer Weiterleitung), der Browser gibt sich offen als Kulturzettel zu erkennen, jede Seite
wird einmal abgerufen, Sperren werden nicht umgangen."""
import json, os, re, sys, time, datetime, zoneinfo, urllib.error, urllib.request, urllib.parse, urllib.robotparser
from playwright.sync_api import sync_playwright

UA = "kulturzettel-bayreuth.de (privater Kulturkalender; Kontakt: siehe Impressum)"
OUT = os.path.join(os.path.dirname(__file__), "skriptseiten.json")
MAX_TEXT = 80000
PAGES = [
    ("Tanzbar", "https://www.tanzbar-bayreuth.de/veranstaltungen/"),
    ("Winterdorf", "https://winterdorf-bayreuth.de/veranstaltungen/"),
    ("Neuneinhalb", "https://www.neuneinhalb.org/veranstaltungen/"),
    ("Neuneinhalb – Veranstalterseite", "https://www.neuneinhalb.org/eventer-organizer/neuneinhalb/"),
    ("Urwelt-Museum – Veranstaltungen", "https://urwelt-museum.snsb.de/veranstaltungen/"),
    ("Bayreuth Tourismus – Veranstaltungen", "https://www.bayreuth-tourismus.de/veranstaltungen/"),
    ("Kunstmuseum – Veranstaltungskalender", "https://www.kunstmuseum-bayreuth.de/aktuelles/vermittlung/veranstaltungskalender"),
    ("Studiobühne – Kalender", "https://www.studiobuehne-bayreuth.de/theater/de/spielplan/kalender/"),
    ("Evangelisches Zentrum – Kalender", "https://www.ez-bayreuth.de/veranstaltungskalender"),
    ("RW21 Stadtbibliothek", "https://stadtbibliothek.bayreuth.de/aktuelles/veranstaltungen/"),
    ("Bayreuth Tourismus – Eventkalender", "https://www.bayreuth-tourismus.de/eventkalender/"),
]
MORE = re.compile(r"^\s*(load more|mehr laden|mehr anzeigen|weitere (termine|veranstaltungen|laden)|more events)\s*$", re.I)
_robots = {}


def allowed(url):
    """True nur, wenn robots.txt den Abruf erlaubt. Ist robots.txt nicht lesbar, wird nicht abgerufen."""
    parts = urllib.parse.urlsplit(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as e:
            # Wie im Standard: fehlende robots.txt (4xx außer 401/403) heißt erlaubt
            if e.code in (401, 403) or e.code >= 500:
                rp.disallow_all = True
            else:
                rp.allow_all = True
        except Exception as e:
            print("robots.txt nicht lesbar:", base, e, file=sys.stderr)
            rp.disallow_all = True
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


def fetch(ctx, name, url):
    rec = {"name": name, "url": url, "final_url": None, "status": None, "text": "", "links": []}
    if not allowed(url):
        rec["status"] = "robots"
        return rec
    page = ctx.new_page()
    try:
        resp = page.goto(url, wait_until="networkidle", timeout=45000)
        rec["final_url"] = page.url
        rec["status"] = resp.status if resp else None
        if not allowed(page.url):
            rec["status"] = "robots (Weiterleitung)"
            return rec
        if rec["status"] and rec["status"] >= 400:
            return rec
        for _ in range(15):
            btn = page.get_by_role("button", name=MORE).or_(page.get_by_role("link", name=MORE)).first
            if not btn.count() or not btn.is_visible():
                break
            btn.click(timeout=5000)
            page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(1)
        texts = [page.inner_text("body")]
        for frame in page.frames[1:]:  # eingebettete Terminlisten; auch hier gilt robots.txt
            if frame.url.startswith("http") and allowed(frame.url):
                try:
                    texts.append(f"[Eingebettet: {frame.url}]\n" + frame.inner_text("body", timeout=5000))
                except Exception:
                    pass
        rec["text"] = "\n\n".join(texts)[:MAX_TEXT]
        seen, links = set(), []
        for text, href in page.eval_on_selector_all("a[href]", "e=>e.map(a=>[a.innerText.trim(),a.href])"):
            if href not in seen and href.startswith("http"):
                seen.add(href)
                links.append({"text": text[:150], "href": href})
        rec["links"] = links[:800]
    except Exception as e:
        rec["status"] = f"fehler: {type(e).__name__}"
        print("FEHLER", url, e, file=sys.stderr)
    finally:
        page.close()
    return rec


def main():
    out = {"fetched": datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Berlin")).isoformat(timespec="minutes"), "pages": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(user_agent=UA, locale="de-DE", timezone_id="Europe/Berlin")
        for name, url in PAGES:
            rec = fetch(ctx, name, url)
            out["pages"].append(rec)
            print(name, rec["status"], len(rec["text"]))
            time.sleep(3)
        browser.close()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main()
