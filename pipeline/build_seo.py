#!/usr/bin/env python3
"""Baut die suchmaschinenlesbare Fassung des Kulturzettels.

- schreibt die Termine fertig gerendert in index.html, kino.html und quellen.html
  (die Seiten rendern sich im Browser wie bisher selbst neu; der Inhalt ist nur
  zusätzlich schon im Quelltext, damit Suchmaschinen ihn ohne JavaScript sehen)
- erzeugt Unterseiten je Sparte (sparte/*.html) und Spielort (ort/*.html)
- ergänzt Titel, Beschreibung, Canonical, Open-Graph-Angaben und
  strukturierte Termindaten (schema.org/Event, JSON-LD)
- schreibt sitemap.xml und die Liste geänderter Adressen für IndexNow

Aufruf aus dem Repository-Hauptordner: python pipeline/build_seo.py
Benötigt: pip install playwright && python -m playwright install chromium
"""
import datetime as dt, html, json, os, re, socket, subprocess, sys, threading, time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SITE = "https://kulturzettel-bayreuth.de/"
TZ = ZoneInfo("Europe/Berlin")
TODAY = dt.datetime.now(TZ).date()
OG_IMAGE = SITE + "og.png"

CATS = [  # Sparte, Slug, Überschrift
    ("Pop, Rock & Jazz", "pop-rock-jazz", "Pop-, Rock- und Jazzkonzerte in Bayreuth"),
    ("Klassik", "klassik", "Klassische Konzerte in Bayreuth"),
    ("Oper & Musiktheater", "oper-musiktheater", "Oper und Musiktheater in Bayreuth"),
    ("Theater", "theater", "Theater in Bayreuth"),
    ("Tanz", "tanz", "Tanz in Bayreuth"),
    ("Club & Party", "club-party", "Clubs und Partys in Bayreuth"),
    ("Kabarett & Comedy", "kabarett-comedy", "Kabarett und Comedy in Bayreuth"),
    ("Literatur", "literatur", "Lesungen und Literatur in Bayreuth"),
    ("Ausstellung", "ausstellungen", "Ausstellungen in Bayreuth"),
    ("Vortrag & Diskurs", "vortraege", "Vorträge und Diskussionen in Bayreuth"),
    ("Film", "film", "Filmvorführungen und Filmreihen in Bayreuth"),
    ("Kinder & Familie", "kinder-familie", "Kultur für Kinder und Familien in Bayreuth"),
    ("Führung", "fuehrungen", "Führungen in Bayreuth"),
    ("Festival", "festivals", "Festivals in Bayreuth"),
    ("Games", "games", "Games, LAN und E-Sport in Bayreuth"),
]
HOUSE_HEAD = {"Kino": "Kino-Sonderveranstaltungen in Bayreuth"}


def slug(s):
    s = s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss").replace("&", " ")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def esc(s):
    return html.escape(str(s or ""), quote=True)


# ---------------------------------------------------------------- Daten
data = json.load(open("events.json", encoding="utf-8"))


def expand(evs):
    out = []
    for e in evs:
        t = e.get("termine")
        if isinstance(t, list) and t:
            for x in t:
                if x and x.get("date"):
                    out.append(dict(e, date=x["date"], end_date=None, time=x.get("time") or e.get("time"), termine=None))
        else:
            out.append(e)
    return out


EVENTS = [e for e in expand(data.get("events", [])) if (e.get("end_date") or e["date"]) >= TODAY.isoformat()]
HOUSES = sorted({e.get("house") for e in EVENTS if e.get("house") and e.get("house") != "Weitere Orte"}, key=lambda h: h.lower())


# ---------------------------------------------------------------- JSON-LD
def iso_start(d, t):
    if not t:
        return d
    y, m, dd = map(int, d.split("-"))
    hh, mm = map(int, t.split(":"))
    return dt.datetime(y, m, dd, hh, mm, tzinfo=TZ).isoformat()


FREI = re.compile(r"^\s*(eintritt\s+)?(frei|kostenfrei|kostenlos)\b(?!\s+bis)", re.I)
TICKET_HOSTS = ("reservix", "eventim", "okticket", "tickets4arts", "region-bayreuth", "online-ticket", "ticket", "eventfinder", "bayreuth4u", "kurier.de", "regioactive")


def ld_offer(e):
    """Angebot nur, wenn der Preis eindeutig ist; nie etwas erfinden."""
    pr = (e.get("price") or "").strip()
    if not pr:
        return None
    off = {"@type": "Offer", "url": e.get("url"), "priceCurrency": "EUR"}
    if re.search(r"ausverkauft", pr, re.I):
        # Google erwartet zu jedem Angebot einen Preis; ohne Preisangabe lieber kein Angebot (Search Console 27.10.2026)
        zahlen = re.findall(r"\d+(?:[.,]\d+)?", pr)
        if not zahlen or "€" not in pr:
            return None
        off["availability"] = "https://schema.org/SoldOut"
        off["price"] = round(float(zahlen[0].replace(".", "").replace(",", ".")), 2)
        return off
    if FREI.search(pr):
        off["price"] = 0
        return off
    if re.search(r"zzgl|spende|unkosten|anmeldung|semester", pr, re.I):
        return None
    zahlen = [float(z.replace(".", "").replace(",", ".")) for z in re.findall(r"\d+(?:[.,]\d+)?", pr)]
    if not zahlen or "€" not in pr:
        return None
    off["price"] = 0 if re.match(r"\s*frei\s+bis", pr, re.I) else round(zahlen[0], 2)  # erste Zahl = regulärer bzw. niedrigster Bereichspreis
    return off


def ld_veranstalter_url(e):
    from urllib.parse import urlsplit
    u = e.get("url") or ""
    host = urlsplit(u).netloc.lower()
    if not host or any(t in host for t in TICKET_HOSTS):
        return None
    return f"https://{host}/"


def ld_event(e):
    multi = e.get("end_date") and e["end_date"] > e["date"]
    venue = e.get("venue") or "Bayreuth"
    parts = [p.strip() for p in venue.split(",")]
    street = next((p for p in parts[1:] if re.search(r"\d", p)), None)
    addr = {"@type": "PostalAddress", "addressLocality": "Bayreuth", "addressRegion": "Bayern", "addressCountry": "DE"}
    if street:
        addr["streetAddress"] = street
    ev = {
        "@type": "Event",
        "name": e["title"] + (" – " + e["subtitle"] if e.get("subtitle") else ""),
        "startDate": iso_start(e["date"], None if multi else e.get("time")),
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": {"@type": "Place", "name": parts[0], "address": addr},
        "url": e.get("url"),
    }
    if multi:
        ev["endDate"] = e["end_date"]
    elif e.get("category") != "Club & Party":
        ev["endDate"] = e["date"]  # endet am selben Tag; Partys laufen oft über Mitternacht, daher dort ohne
    ev["image"] = [OG_IMAGE]
    off = ld_offer(e)
    if off:
        ev["offers"] = off
    if e.get("description"):
        ev["description"] = e["description"]
    if e.get("organizer") or e.get("source"):
        name = e.get("organizer") or re.sub(r"\s*\(.*\)$", "", e.get("source", ""))
        if name and not name.startswith("Hinweis"):
            ev["organizer"] = {"@type": "Organization", "name": name}
            vu = ld_veranstalter_url(e)
            if vu:
                ev["organizer"]["url"] = vu
    return ev


def ld_block(evs, limit=None):
    evs = sorted(evs, key=lambda e: (e["date"], e.get("time") or "99"))
    if limit:
        evs = evs[:limit]
    graph = [ld_event(e) for e in evs]
    if not graph:
        return ""
    txt = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">' + txt.replace("</", "<\\/") + "</script>"


# ---------------------------------------------------------------- Kopf
def seo_head(title, desc, path, base=False):
    url = SITE + path
    h = [f"<title>{esc(title)}</title>", f'<meta name="description" content="{esc(desc)}">',
         f'<link rel="canonical" href="{url}">', '<meta property="og:type" content="website">',
         '<meta property="og:locale" content="de_DE">', '<meta property="og:site_name" content="Kulturzettel Bayreuth">',
         f'<meta property="og:title" content="{esc(title)}">', f'<meta property="og:description" content="{esc(desc)}">',
         f'<meta property="og:url" content="{url}">', f'<meta property="og:image" content="{OG_IMAGE}">',
         '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
         '<meta name="twitter:card" content="summary_large_image">']
    if base:
        h.insert(0, '<base href="/">')
    return "".join(h)


def put(s, marker, content):
    pat = re.compile(r"<!--%s-->.*?<!--/%s-->" % (marker, marker), re.S)
    if not pat.search(s):
        raise SystemExit(f"Markierung {marker} fehlt")
    return pat.sub(lambda m: f"<!--{marker}-->{content}<!--/{marker}-->", s, count=1)


def current_head(s):
    m = re.search(r"<!--seo-->(.*?)<!--/seo-->", s, re.S)
    t = re.search(r"<title>(.*?)</title>", m.group(1), re.S).group(1)
    d = re.search(r'<meta name="description" content="([^"]*)"', m.group(1))
    return html.unescape(t), html.unescape(d.group(1)) if d else None


# ---------------------------------------------------------------- Rendern im Browser
def serve():
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(Quiet, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def snapshot(page, port, path, wait_sel):
    page.goto(f"http://127.0.0.1:{port}/{path}", wait_until="networkidle")
    page.wait_for_function(wait_sel, timeout=20000)
    page.wait_for_timeout(300)
    return page.content()


def clean(s):
    # Zustand des Browsers nicht mitspeichern
    s = re.sub(r'<html lang="de"[^>]*>', '<html lang="de">', s, count=1)
    # Kalender-Menüs nicht vorab ausliefern (lange Links, für Suchmaschinen wertlos); das Skript ergänzt sie im Browser
    m = re.search(r'(<main[^>]*id="prog"[^>]*>)(.*?)(</main>)', s, re.S)
    if m:
        body = re.sub(r'<details class="cal">.*?</details>', '', m.group(2), flags=re.S)
        s = s[:m.start(2)] + body + s[m.end(2):]
    if not s.lstrip().lower().startswith("<!doctype"):
        s = "<!doctype html>" + s
    return s


def main():
    from playwright.sync_api import sync_playwright
    srv, port = serve()
    changed = []
    written = {}

    index_src = open("index.html", encoding="utf-8").read()
    intro_home = "Kulturveranstaltungen in Bayreuth für die kommenden zwei Monate: Konzerte, Theater, Ausstellungen, Lesungen, Kino und mehr. Täglich aktualisiert aus den Programmen der Häuser."
    home_title = "Kulturzettel Bayreuth – Veranstaltungen, Konzerte, Theater und Ausstellungen"

    # Unterseiten aus der Startseite ableiten
    sub = []  # (pfad, titel, beschreibung, überschrift, preset, events)
    for cat, sl, head in CATS:
        evs = [e for e in EVENTS if e.get("category") == cat]
        desc = f"{head}: Termine der kommenden zwei Monate mit Uhrzeit, Ort und Link zum Veranstalter. Täglich aktualisiert."
        lead = "Termine der kommenden zwei Monate mit Uhrzeit, Ort und Link zum Veranstalter. Täglich aktualisiert aus den veröffentlichten Programmen der Bayreuther Häuser."
        sub.append((f"sparte/{sl}.html", f"{head} – Kulturzettel", desc, head, {"cats": [cat]}, evs, lead))
    for h in HOUSES:
        evs = [e for e in EVENTS if e.get("house") == h]
        head = HOUSE_HEAD.get(h, f"{h}: Programm und Termine in Bayreuth")
        desc = f"{head} – Veranstaltungen der kommenden zwei Monate mit Uhrzeit und Link zum Veranstalter. Täglich aktualisiert."
        lead = "Veranstaltungen der kommenden zwei Monate mit Uhrzeit und Link zum Veranstalter. Täglich aktualisiert aus den veröffentlichten Programmen."
        sub.append((f"ort/{slug(h)}.html", f"{head} – Kulturzettel", desc, head, {"house": h}, evs, lead))

    os.makedirs("sparte", exist_ok=True); os.makedirs("ort", exist_ok=True)
    tmpl = index_src
    for path, title, desc, head, preset, evs, lead in sub:
        s = put(tmpl, "seo", seo_head(title, desc, path, base=True) +
                "<script>window.KZ_PRESET=" + json.dumps(preset, ensure_ascii=False) + "</script>")
        s = put(s, "pagehead", f'<p class="back"><a href="./">← Gesamtes Programm</a></p><h2 class="page-h">{esc(head)}</h2>'
                f'<p>{esc(lead)}</p>')
        s = put(s, "ld", "")
        written[path] = (s, evs)

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        ctx = b.new_context(locale="de-DE", timezone_id="Europe/Berlin")
        # Statistikdienst beim Bauen nicht aufrufen
        ctx.route(re.compile(r"^https?://(?!127\.0\.0\.1)"), lambda r: r.abort())
        page = ctx.new_page()

        def render(path, src, wait_sel, ld=""):
            tmp = path + ".tmp.html"
            open(tmp, "w", encoding="utf-8").write(src)
            try:
                out = clean(snapshot(page, port, tmp, wait_sel))
            finally:
                os.remove(tmp)
            out = put(out, "ld", ld) if "<!--ld-->" in out else out
            return out

        prog_ready = "document.querySelector('#prog .load')===null"
        # Startseite
        s = put(index_src, "seo", seo_head(home_title, intro_home, ""))
        s = put(s, "pagehead", "<p>Kulturveranstaltungen in Bayreuth für die kommenden zwei Monate – auf Bühnen, in Sälen, Museen und Clubs. Täglich aktualisiert aus den veröffentlichten Programmen der Häuser.</p>")
        soon = [e for e in EVENTS if e["date"] <= (TODAY + dt.timedelta(days=14)).isoformat()]
        out = render("index.html", s, prog_ready, ld_block(soon, limit=300))
        save("index.html", out, changed, "")
        # Unterseiten
        for path, (src, evs) in written.items():
            out = render(path, src, prog_ready, ld_block(evs))
            save(path, out, changed, path)
        # alte Ortsseiten entfernen, die keine Termine mehr haben
        keep = {os.path.basename(x) for x in written if x.startswith("ort/")}
        for f in os.listdir("ort"):
            if f.endswith(".html") and f not in keep:
                os.remove(os.path.join("ort", f)); print("entfernt: ort/" + f)
        # Kino
        ks = open("kino.html", encoding="utf-8").read()
        t, d = current_head(ks)
        ks = put(ks, "seo", seo_head(t, d, "kino.html"))
        out = render("kino.html", ks, "document.querySelector('#prog .load')===null")
        save("kino.html", out, changed, "kino.html")
        # Quellen
        qs = open("quellen.html", encoding="utf-8").read()
        t, d = current_head(qs)
        qs = put(qs, "seo", seo_head(t, d or "Die Programme und Veranstalter, aus denen der Kulturzettel Bayreuth täglich zusammengestellt wird.", "quellen.html"))
        out = render("quellen.html", qs, "document.querySelector('#srcs .small')===null")
        save("quellen.html", out, changed, "quellen.html")
        b.close()
    srv.shutdown()

    # statische Seiten: nur Kopf ergänzen
    extra = {"ueber.html": "Was der Kulturzettel Bayreuth ist, wie er entsteht und wer dahintersteht.",
             "impressum.html": "Impressum des Kulturzettel Bayreuth.",
             "datenschutz.html": "Datenschutzerklärung des Kulturzettel Bayreuth."}
    for f, dd in extra.items():
        s = open(f, encoding="utf-8").read()
        t, d = current_head(s)
        save(f, put(s, "seo", seo_head(t, d or dd, f)), changed, f)

    # Sitemap
    urls = [("", "daily", "1.0"), ("kino.html", "daily", "0.8")]
    urls += [(p, "daily", "0.7") for p in written]
    urls += [("quellen.html", "weekly", "0.3"), ("ueber.html", "monthly", "0.3"), ("impressum.html", "yearly", "0.1"), ("datenschutz.html", "yearly", "0.1")]
    lastmod = {}
    try:
        old = open("sitemap.xml", encoding="utf-8").read()
        for loc, lm in re.findall(r"<loc>(.*?)</loc><lastmod>(.*?)</lastmod>", old):
            lastmod[loc] = lm
    except FileNotFoundError:
        pass
    today = TODAY.isoformat()
    rows = []
    for path, freq, prio in urls:
        loc = SITE + path
        lm = today if (path in changed or loc not in lastmod) else lastmod[loc]
        rows.append(f"<url><loc>{loc}</loc><lastmod>{lm}</lastmod><changefreq>{freq}</changefreq><priority>{prio}</priority></url>")
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"
    open("sitemap.xml", "w", encoding="utf-8").write(sm)
    open("pipeline/geaendert.txt", "w", encoding="utf-8").write("\n".join(SITE + c for c in changed) + ("\n" if changed else ""))
    print(f"{len(changed)} Seiten geändert, {len(written)} Unterseiten, {len(EVENTS)} Termine")


def norm(s):
    # Für den Vergleich: Uhrzeit-/Datumsabhängiges ignorieren, das sich bei jedem Lauf ändert
    return re.sub(r'(id="(issue|upd|kino-t|kino-s)"[^>]*>)[^<]*', r"\1", s)


def save(path, out, changed, key):
    try:
        old = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        old = ""
    if norm(old) != norm(out):
        changed.append(key)
    if old != out:
        open(path, "w", encoding="utf-8").write(out)


if __name__ == "__main__":
    main()
