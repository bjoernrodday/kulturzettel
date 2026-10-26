"""Erzeugt ein Karussell, das den Kulturzettel vorstellt (Instagram und LinkedIn).

Aufruf: python3 pipeline/karussell.py [YYYY-MM-DD]   (Stichtag = Tag des Postens; ohne Angabe heute)
Ergebnis in karussell/<stichtag>/ (nicht im Repository):
  slide-NN.png, kulturzettel-<stichtag>-NN.jpg (Instagram, Aufnahmezeit aufsteigend),
  kulturzettel-<stichtag>.pdf (LinkedIn-Dokumentbeitrag), text.md (Instagram), linkedin.md (LinkedIn)
Zahlen wie auf der Startseite: Termine ab Stichtag (Reihen in Einzeltermine aufgelöst), nächste 7 Tage, Spielorte.
Alle Termine gleichrangig: keine Highlights, keine Titel einzelner Veranstaltungen.
"""
import datetime, html, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATS = ["Pop, Rock & Jazz", "Klassik", "Oper & Musiktheater", "Theater", "Tanz", "Club & Party", "Kabarett & Comedy", "Literatur",
        "Ausstellung", "Vortrag & Diskurs", "Film", "Kinder & Familie", "Führung", "Festival", "Games"]
# Sammelrubriken der Website, die keine einzelnen Häuser sind
SAMMEL = {"Clubs": "Clubs und Bars", "Kino": "Kino-Sonderformate", "Kirchen": "Konzerte in Kirchen",
          "Stadtführungen": "Stadtführungen", "Weitere Orte": "weitere Orte"}
WT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MON = ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez."]

PAPER, SHEET, INK, MUTED, RULE, ROT, ROTSOFT = "#EDEFF2", "#F7F8FA", "#14161B", "#5A616C", "#C9CED6", "#A8122A", "#F3DADD"


def termine(stichtag):
    roh = json.load(open(os.path.join(ROOT, "events.json"), encoding="utf-8"))
    aus = []
    for e in roh["events"]:  # wie expand() in index.html
        if isinstance(e.get("termine"), list) and e["termine"]:
            for t in e["termine"]:
                if t and t.get("date"):
                    aus.append(dict(e, date=t["date"], end_date=None))
        else:
            aus.append(e)
    s = stichtag.isoformat()
    return [e for e in aus if (e.get("end_date") or e["date"]) >= s], roh


def aufzaehlen(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " und " + xs[-1]


def im_zeitraum(e, a, b):
    return e["date"] <= b and (e.get("end_date") or e["date"]) >= a


CSS = """
@import url("{fonts}");
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1080px; height: 1350px; background: {PAPER}; color: {INK}; font-family: "Schibsted Grotesk", sans-serif;
  padding: 84px 84px 72px; display: flex; flex-direction: column; }}
.meta {{ font-family: "IBM Plex Mono", monospace; font-weight: 500; font-size: 25px; letter-spacing: .1em; text-transform: uppercase; color: {MUTED};
  display: flex; justify-content: space-between; border-bottom: 2px solid {INK}; padding-bottom: 22px; }}
.wort {{ font-family: Figtree, sans-serif; font-weight: 700; letter-spacing: -.045em; line-height: .88; }}
.wort span {{ color: {ROT}; }}
h2 {{ font-family: Figtree, sans-serif; font-weight: 700; font-size: 86px; letter-spacing: -.035em; line-height: .95; margin-top: 64px; }}
h2 span {{ color: {ROT}; }}
.lead {{ font-size: 40px; line-height: 1.32; }}
.klein {{ font-size: 29px; line-height: 1.42; color: {MUTED}; }}
.fuss {{ margin-top: auto; font-family: "IBM Plex Mono", monospace; font-size: 24px; color: {MUTED}; display: flex; justify-content: space-between;
  border-top: 2px solid {RULE}; padding-top: 26px; letter-spacing: .04em; }}
.zahlen {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; border-top: 2px solid {INK}; padding-top: 30px; }}
.zahlen b {{ display: block; font-family: Figtree, sans-serif; font-weight: 700; font-size: 104px; letter-spacing: -.04em; line-height: 1; }}
.zahlen small {{ display: block; font-family: "IBM Plex Mono", monospace; font-size: 23px; letter-spacing: .08em; text-transform: uppercase; color: {MUTED}; margin-top: 10px; }}
.spalten {{ display: grid; grid-template-columns: 1fr 1fr; column-gap: 56px; }}
.sp {{ display: grid; grid-template-columns: 1fr auto; border-bottom: 1.5px solid {RULE}; padding: 15px 0 16px; font-size: 31px; align-items: baseline; }}
.sp i {{ font-style: normal; font-family: "IBM Plex Mono", monospace; font-weight: 500; font-size: 30px; color: {ROT}; }}
.tag {{ display: grid; grid-template-columns: 250px 1fr 80px; gap: 24px; align-items: center; border-bottom: 1.5px solid {RULE}; padding: 13px 0; }}
.tag .z {{ font-family: Figtree, sans-serif; font-weight: 700; font-size: 62px; letter-spacing: -.04em; line-height: 1; }}
.tag .w {{ font-family: "IBM Plex Mono", monospace; font-size: 23px; letter-spacing: .1em; text-transform: uppercase; color: {MUTED}; margin-left: 14px; }}
.tag .bar {{ height: 30px; background: {ROT}; border-radius: 3px; }}
.tag .n {{ font-family: "IBM Plex Mono", monospace; font-weight: 500; font-size: 32px; text-align: right; }}
.orte {{ font-size: 33px; line-height: 1.5; margin-top: 46px; }}
.orte span {{ color: {ROT}; padding: 0 .1em 0 .3em; }}
.orte em {{ font-style: normal; white-space: nowrap; }}
.schritt {{ display: grid; grid-template-columns: 100px 1fr; gap: 26px; margin-top: 74px; }}
.schritt .nr {{ font-family: Figtree, sans-serif; font-weight: 700; font-size: 92px; color: {ROT}; line-height: .9; letter-spacing: -.04em; }}
.schritt .t {{ font-family: Figtree, sans-serif; font-weight: 700; font-size: 44px; letter-spacing: -.015em; line-height: 1.1; }}
.schritt .h {{ font-size: 30px; line-height: 1.38; color: {MUTED}; margin-top: 10px; }}
.kasten {{ background: {ROTSOFT}; border-left: 8px solid {ROT}; padding: 30px 34px; font-size: 33px; line-height: 1.4; }}
"""


def seite(inhalt, nr, gesamt):
    fonts = "file://" + os.path.join(ROOT, "fonts", "fonts.css")
    css = CSS.format(fonts=fonts, PAPER=PAPER, SHEET=SHEET, INK=INK, MUTED=MUTED, RULE=RULE, ROT=ROT, ROTSOFT=ROTSOFT)
    return (f"<!doctype html><html lang='de'><head><meta charset='utf-8'><style>{css}</style></head><body>"
            f"{inhalt}<div class='fuss'><span>kulturzettel-bayreuth.de · ohne Gewähr</span><span>{nr}/{gesamt}</span></div></body></html>")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tag = datetime.date.fromisoformat(args[0]) if args else datetime.date.today()
    evs, roh = termine(tag)
    s7 = (tag + datetime.timedelta(days=6)).isoformat()
    woche = [e for e in evs if im_zeitraum(e, tag.isoformat(), s7)]
    orte = sorted({e.get("house") or e["venue"] for e in evs}, key=lambda x: x.lower())
    quellen = len(roh.get("sources") or [])
    ausgabe = (tag - datetime.date(2026, 10, 3)).days + 1
    sparten = [(c, sum(1 for e in evs if e["category"] == c)) for c in CATS]
    sparten = [x for x in sparten if x[1]]
    datum_lang = f"{tag.day}. {MON[tag.month - 1]} {tag.year}"

    inhalte = []
    inhalte.append(
        f"<div class='meta'><span>Bayreuth · Ausgabe {ausgabe}</span><span>{datum_lang}</span></div>"
        "<div class='wort' style='margin-top:110px;font-size:212px'>Kultur<br><span>zettel</span></div>"
        "<p class='lead' style='margin-top:60px;max-width:23ch'>Kulturtermine in Bayreuth für die kommenden zwei Monate – auf Bühnen, in Sälen, Museen und Clubs.</p>"
        f"<div class='zahlen' style='margin-top:64px'><div><b>{len(evs)}</b><small>Termine</small></div>"
        f"<div><b>{len(woche)}</b><small>in 7 Tagen</small></div><div><b>{len(orte)}</b><small>Spielorte</small></div></div>"
        "<p class='klein' style='margin-top:40px'>Zum Durchblättern wischen</p>")
    zeilen = [f"<div class='sp'><span>{html.escape(c)}</span><i>{n}</i></div>" for c, n in sparten]
    halb = (len(zeilen) + 1) // 2
    links, rechts = "".join(zeilen[:halb]), "".join(zeilen[halb:])
    inhalte.append(
        "<div class='meta'><span>Was drinsteht</span><span>Termine je Sparte</span></div>"
        f"<h2>{len(sparten)} Sparten, <span>alle gleichrangig</span></h2>"
        f"<div class='spalten' style='margin-top:48px'><div>{links}</div><div>{rechts}</div></div>"
        "<p class='klein' style='margin-top:40px'>Konzerte, Bühne, Museen, Uni, Bibliothek, Kino-Sonderformate, Clubs und Games – ohne Auswahl und ohne Wertung.</p>")
    tage = []
    for i in range(7):
        d = tag + datetime.timedelta(days=i)
        n = sum(1 for e in evs if not (e.get("end_date") and e["end_date"] > e["date"]) and e["date"] == d.isoformat())
        tage.append((d, n))
    mx = max(n for _, n in tage) or 1
    laufend = sum(1 for e in woche if e.get("end_date") and e["end_date"] > e["date"])
    zeilen = "".join(
        f"<div class='tag'><div><span class='z'>{d.day}.</span><span class='w'>{WT[d.weekday()]}</span></div>"
        f"<div><div class='bar' style='width:{max(4, round(100 * n / mx))}%'></div></div><div class='n'>{n}</div></div>" for d, n in tage)
    inhalte.append(
        f"<div class='meta'><span>Die nächsten 7 Tage</span><span>Termine je Tag</span></div>"
        f"<h2>{len(woche)} Termine <span>in 7 Tagen</span></h2>"
        f"<div style='margin-top:36px'>{zeilen}</div>"
        f"<p class='klein' style='margin-top:30px'>Die Balken zeigen die {len(woche) - laufend} Einzeltermine je Tag. Dazu kommen {laufend} Ausstellungen und Angebote, die die ganze Woche über geöffnet sind.</p>")
    inhalte.append(
        "<div class='meta'><span>Wo</span><span>Spielorte in Bayreuth</span></div>"
        f"<h2>{len(orte)} Spielorte, <span>{quellen} Quellen</span></h2>"
        "<p class='orte'>" + "<span>·</span> ".join(f"<em>{html.escape(o)}</em>" for o in orte if o not in SAMMEL) + "</p>"
        + (f"<p class='klein' style='margin-top:36px'>Dazu {aufzaehlen([SAMMEL[o] for o in orte if o in SAMMEL])}.</p>" if any(o in SAMMEL for o in orte) else ""))
    schritte = [("1", "Filtern", "Nach Tag, Wochenende oder Monat, nach Sparte, Spielort, freiem Eintritt oder mit der Suche."),
                ("2", "Vormerken", "Jeder Termin lässt sich mit einem Klick in den eigenen Kalender übernehmen."),
                ("3", "Zum Veranstalter", "Jeder Eintrag führt zur Originalseite des Hauses, dort gibt es Details und Tickets.")]
    inhalte.append(
        "<div class='meta'><span>So funktioniert es</span><span>Kultur<span style='color:#A8122A'>zettel</span></span></div>"
        + "".join(f"<div class='schritt'{' style=\"margin-top:110px\"' if i == 0 else ''}><div class='nr'>{n}</div><div><div class='t'>{t}</div><div class='h'>{h}</div></div></div>"
                  for i, (n, t, h) in enumerate(schritte))
        + "<div class='kasten' style='margin-top:110px'>Keine Highlights, keine Empfehlungen, keine Werbung. Kostenlos und ohne Anmeldung.</div>")
    inhalte.append(
        "<div class='meta'><span>Kulturzettel</span><span>@bjoern_rodday</span></div>"
        "<div class='wort' style='margin-top:250px;font-size:170px'>Kultur<span>zettel</span></div>"
        "<p class='lead' style='margin-top:72px'>Was in Bayreuth kulturell los ist:<br>kulturzettel-bayreuth.de</p>"
        "<p class='klein' style='margin-top:44px;max-width:38ch'>Ein privates Projekt von Björn Rodday. Ohne Gewähr. Maßgeblich sind allein die Angaben der Veranstalter.</p>")

    gesamt = len(inhalte)
    folien = [seite(h, i + 1, gesamt) for i, h in enumerate(inhalte)]
    aus = os.path.join(ROOT, "karussell", tag.isoformat())
    os.makedirs(aus, exist_ok=True)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for i, h in enumerate(folien, 1):
            pfad = os.path.join(aus, f"slide-{i:02d}.html")
            open(pfad, "w", encoding="utf-8").write(h)
            pg.goto("file://" + pfad)
            pg.wait_for_timeout(300)
            pg.screenshot(path=os.path.join(aus, f"slide-{i:02d}.png"))
            os.remove(pfad)
        b.close()

    hinweis = "Ohne Gewähr – maßgeblich sind die Angaben der Veranstalter."
    text = (f"Kulturzettel: Was in Bayreuth kulturell los ist, an einem Ort.\n\n"
            f"{len(evs)} Termine an {len(orte)} Spielorten für die kommenden zwei Monate, allein in den nächsten sieben Tagen {len(woche)}: "
            "Konzerte, Klassik, Theater, Tanz, Kabarett, Lesungen, Vorträge, Ausstellungen, Führungen, Kino-Sonderformate, Clubabende, Kinderprogramm und Games.\n\n"
            "Alle Termine stehen gleichrangig nebeneinander, ohne Highlights und ohne Werbung. Filtern nach Tag, Sparte, Spielort oder freiem Eintritt, "
            "jeder Eintrag führt direkt zum Veranstalter.\n\n"
            "Kostenlos und ohne Anmeldung. Ein privates Projekt.\n\n"
            f"kulturzettel-bayreuth.de\n{hinweis}\n\n"
            "#Bayreuth #KulturBayreuth #Kulturkalender #Veranstaltungen #Oberfranken")
    li = (f"Neben Kulturtöpfe betreibe ich ein zweites privates Projekt: den Kulturzettel, einen Kulturkalender für Bayreuth.\n\n"
          f"Er bündelt die Kulturtermine der Stadt für die kommenden zwei Monate, derzeit {len(evs)} Termine an {len(orte)} Spielorten aus {quellen} Quellen: "
          "Bühnen und Konzertsäle, Museen, die Universität, Bibliothek und Volkshochschule, Clubs und Szene-Orte.\n\n"
          "Alle Termine stehen gleichrangig nebeneinander, ohne Highlights, ohne Empfehlungen, ohne Werbung. Man filtert nach Tag, Sparte, Spielort oder freiem Eintritt, "
          "übernimmt einen Termin in den eigenen Kalender, und jeder Eintrag führt zur Originalseite des Veranstalters.\n\n"
          "Kostenlos und ohne Anmeldung.\n\n"
          f"https://kulturzettel-bayreuth.de\n{hinweis}\n\n"
          "#Bayreuth #Kultur #Kulturkalender #Oberfranken")
    assert len(text) < 2200 and len(li) < 3000, (len(text), len(li))
    open(os.path.join(aus, "text.md"), "w", encoding="utf-8").write(text)
    open(os.path.join(aus, "linkedin.md"), "w", encoding="utf-8").write(li)

    from PIL import Image
    pngs = [os.path.join(aus, f"slide-{i:02d}.png") for i in range(1, gesamt + 1)]
    basis = datetime.datetime.combine(datetime.date.today(), datetime.time(8, 0))
    for i, png in enumerate(pngs, 1):
        im = Image.open(png).convert("RGB")
        exif = Image.Exif()
        zeit = (basis + datetime.timedelta(minutes=i)).strftime("%Y:%m:%d %H:%M:%S")
        exif[0x0132] = zeit
        exif.get_ifd(0x8769)[0x9003] = zeit
        exif.get_ifd(0x8769)[0x9004] = zeit
        ziel = os.path.join(aus, f"kulturzettel-{tag.isoformat()}-{i:02d}.jpg")
        im.save(ziel, "JPEG", quality=95, exif=exif)
        t = (basis + datetime.timedelta(minutes=i)).timestamp()
        os.utime(ziel, (t, t))
    bilder = [Image.open(x).convert("RGB") for x in pngs]
    bilder[0].save(os.path.join(aus, f"kulturzettel-{tag.isoformat()}.pdf"), save_all=True, append_images=bilder[1:], resolution=144)
    print(aus, gesamt, "Folien", len(evs), "Termine", len(woche), "in 7 Tagen", len(orte), "Orte", len(text), len(li))


if __name__ == "__main__":
    main()
