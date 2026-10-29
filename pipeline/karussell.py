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

PAPER, SHEET, INK, MUTED, RULE, ROT, ROTSOFT = "#EDEFF2", "#E3E6EB", "#14161B", "#5A616C", "#C9CED6", "#A8122A", "#F3DADD"
MONLANG = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
PFEIL = ("<svg width='{w}' height='{h}' viewBox='0 0 80 64' fill='none' stroke='{c}' stroke-width='4'>"
         "<path d='M0 32H76M48 4L76 32L48 60'/></svg>")

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


# Gestaltung angelehnt an Björns Vorlage vom 29.10.2026: helle und rote Folien im Wechsel,
# Schriftzug zweizeilig, große Zahlen, senkrechte Balken, Fortschrittsstriche. Alles als Vektor/Text gerendert.
CSS = """
@import url("{fonts}");
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1080px; height: 1350px; background: {PAPER}; color: {INK}; font-family: "Schibsted Grotesk", sans-serif;
  padding: 56px 64px 28px; display: flex; flex-direction: column; position: relative; }}
body.rot {{ background: {ROT}; color: {PAPER}; }}
.meta {{ font-family: "IBM Plex Mono", monospace; font-weight: 500; font-size: 25px; letter-spacing: .1em; text-transform: uppercase; color: {MUTED};
  display: flex; justify-content: space-between; border-bottom: 2px solid {INK}; padding-bottom: 22px; }}
.rot .meta {{ color: {PAPER}; border-color: {PAPER}; }}
.meta .z {{ color: {ROT}; }}
.wort {{ font-family: Figtree, sans-serif; font-weight: 800; letter-spacing: -.05em; line-height: .84; padding-bottom: .06em; }}
.wort .z {{ color: {ROT}; display: block; }}
.rot .wort .z {{ color: {PAPER}; }}
h2 {{ font-family: Figtree, sans-serif; font-weight: 800; font-size: 90px; letter-spacing: -.04em; line-height: 1.02; margin-top: 56px; padding-bottom: 8px; }}
h2 span {{ color: {ROT}; }}
.lead {{ font-size: 42px; line-height: 1.3; }}
.klein {{ font-size: 29px; line-height: 1.42; color: {MUTED}; }}
.rot .klein {{ color: {PAPER}; }}
.notiz {{ border-left: 8px solid {ROT}; padding: 4px 0 4px 24px; font-size: 29px; line-height: 1.42; color: {MUTED}; }}
.notiz.box {{ background: {SHEET}; padding: 30px 30px 30px 28px; }}
.fuss {{ margin-top: auto; font-family: "IBM Plex Mono", monospace; font-size: 24px; color: {MUTED}; display: flex; justify-content: space-between;
  border-top: 2px solid {INK}; padding-top: 24px; letter-spacing: .04em; }}
.rot .fuss {{ color: {PAPER}; border-color: {PAPER}; }}
.punkte {{ display: flex; gap: 9px; margin-top: 30px; }}
.punkte i {{ width: 28px; height: 4px; background: {RULE}; }}
.punkte i.an {{ background: {ROT}; }}
.rot .punkte i {{ background: rgba(237,239,242,.4); }}
.rot .punkte i.an {{ background: {PAPER}; }}
.ecke {{ position: absolute; right: 64px; top: 144px; width: 148px; height: 390px; border-top: 16px solid {ROT}; border-right: 16px solid {ROT}; }}
.zahlen {{ display: grid; grid-template-columns: 1.3fr 1fr 1fr; align-items: end; border-top: 2px solid {INK}; padding-top: 36px; }}
.zahlen > div {{ padding-left: 44px; border-left: 2px solid {RULE}; }}
.zahlen > div:first-child {{ padding-left: 0; border-left: 0; }}
.zahlen b {{ display: block; font-family: Figtree, sans-serif; font-weight: 800; font-size: 108px; letter-spacing: -.045em; line-height: 1; }}
.zahlen > div:first-child b {{ color: {ROT}; font-size: 140px; }}
.zahlen small {{ display: block; font-family: "IBM Plex Mono", monospace; font-size: 23px; letter-spacing: .1em; text-transform: uppercase; color: {MUTED}; margin-top: 14px; }}
.wisch {{ display: flex; justify-content: space-between; align-items: center; }}
.spalten {{ display: grid; grid-template-columns: 1fr 1fr; column-gap: 56px; }}
.sp {{ display: grid; grid-template-columns: 1fr auto; border-bottom: 2px solid rgba(237,239,242,.35); padding: 19px 0 20px; font-size: 31px; align-items: baseline; }}
.sp i {{ font-style: normal; font-family: "IBM Plex Mono", monospace; font-weight: 500; font-size: 30px; padding-right: 8px; }}
.kopf3 {{ display: flex; align-items: center; gap: 56px; margin-top: 48px; }}
.kopf3 b {{ font-family: Figtree, sans-serif; font-weight: 800; font-size: 170px; letter-spacing: -.05em; line-height: .9; color: {ROT}; }}
.kopf3 div {{ font-family: Figtree, sans-serif; font-weight: 800; font-size: 72px; letter-spacing: -.04em; line-height: 1.02; }}
.kopf3 div span {{ color: {ROT}; }}
.balken {{ display: grid; grid-template-columns: repeat(7, 1fr); column-gap: 52px; align-items: end; height: 540px; border-bottom: 2px solid {INK}; margin-top: 40px; }}
.balken .s {{ display: flex; flex-direction: column; justify-content: flex-end; align-items: stretch; height: 100%; }}
.balken .n {{ font-family: "IBM Plex Mono", monospace; font-weight: 500; font-size: 32px; color: {ROT}; text-align: center; margin-bottom: 14px; }}
.balken .b {{ background: {ROT}; }}
.tage {{ display: grid; grid-template-columns: repeat(7, 1fr); column-gap: 52px; margin-top: 20px; }}
.tage div {{ font-family: Figtree, sans-serif; font-weight: 800; font-size: 44px; letter-spacing: -.04em; white-space: nowrap; }}
.tage small {{ font-family: "IBM Plex Mono", monospace; font-weight: 400; font-size: 17px; letter-spacing: .1em; color: {MUTED}; margin-left: 8px; }}
.paar {{ display: grid; grid-template-columns: 1fr 1fr; margin-top: 56px; border-bottom: 2px solid {INK}; padding-bottom: 26px; }}
.paar > div + div {{ border-left: 2px solid {RULE}; padding-left: 56px; }}
.paar b {{ display: block; font-family: Figtree, sans-serif; font-weight: 800; font-size: 160px; letter-spacing: -.05em; line-height: .9; }}
.paar span {{ display: block; font-family: Figtree, sans-serif; font-weight: 800; font-size: 56px; letter-spacing: -.035em; margin-top: 10px; }}
.paar .r {{ color: {ROT}; }}
.orte {{ font-size: 33px; line-height: 1.55; margin-top: 30px; }}
.orte span {{ color: {ROT}; padding: 0 .1em 0 .3em; }}
.orte em {{ font-style: normal; white-space: nowrap; }}
.schritt {{ display: grid; grid-template-columns: 100px 1fr; gap: 44px; padding: 40px 0; }}
.schritt + .schritt {{ border-top: 2px solid {RULE}; margin-left: 144px; padding-left: 0; grid-template-columns: 1fr; }}
.schritt + .schritt {{ margin-left: 0; border-top: 0; }}
.trenn {{ border-top: 2px solid {RULE}; margin-left: 144px; }}
.schritt .nr {{ width: 100px; height: 126px; background: {ROT}; color: {PAPER}; font-family: Figtree, sans-serif; font-weight: 800; font-size: 84px;
  display: flex; align-items: center; justify-content: center; letter-spacing: -.04em; }}
.schritt .t {{ font-family: Figtree, sans-serif; font-weight: 800; font-size: 46px; letter-spacing: -.02em; line-height: 1.1; }}
.schritt .h {{ font-size: 30px; line-height: 1.38; color: {MUTED}; margin-top: 16px; }}
.band {{ background: {ROT}; color: {PAPER}; padding: 32px 28px; font-size: 34px; line-height: 1.38; }}
.link {{ background: {INK}; color: {PAPER}; display: flex; justify-content: space-between; align-items: center; padding: 34px 28px; font-size: 50px; margin-top: 44px; }}
"""


def seite(inhalt, nr, gesamt, rot=False):
    fonts = "file://" + os.path.join(ROOT, "fonts", "fonts.css")
    css = CSS.format(fonts=fonts, PAPER=PAPER, SHEET=SHEET, INK=INK, MUTED=MUTED, RULE=RULE, ROT=ROT, ROTSOFT=ROTSOFT)
    punkte = "".join(f"<i class='{'an' if i == nr else ''}'></i>" for i in range(1, gesamt + 1))
    return (f"<!doctype html><html lang='de'><head><meta charset='utf-8'><style>{css}</style></head><body class='{'rot' if rot else ''}'>"
            f"{inhalt}<div class='fuss'><span>kulturzettel-bayreuth.de · ohne Gewähr</span><span>{nr}/{gesamt}</span></div>"
            f"<div class='punkte'>{punkte}</div></body></html>")


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
    datum_voll = f"{tag.day}. {MONLANG[tag.month - 1]} {tag.year}"

    inhalte, rot = [], []
    inhalte.append(
        f"<div class='meta'><span>Bayreuth · Ausgabe {ausgabe}</span><span>{datum_lang}</span></div><div class='ecke'></div>"
        "<div class='wort' style='margin-top:52px;font-size:236px'>Kultur<span class='z'>zettel</span></div>"
        "<p class='lead' style='margin-top:58px;max-width:24ch'>Kulturtermine in Bayreuth für die kommenden zwei Monate</p>"
        f"<div class='zahlen' style='margin-top:96px'><div><b>{len(evs)}</b><small>Termine</small></div>"
        f"<div><b>{len(woche)}</b><small>in 7 Tagen</small></div><div><b>{len(orte)}</b><small>Spielorte</small></div></div>"
        f"<div class='wisch' style='margin-top:58px;margin-bottom:34px'><p class='klein'>Zum Durchblättern wischen</p>{PFEIL.format(w=76, h=60, c=ROT)}</div>")
    rot.append(False)
    zeilen = [f"<div class='sp'><span>{html.escape(c)}</span><i>{n}</i></div>" for c, n in sparten]
    halb = (len(zeilen) + 1) // 2
    links, rechts = "".join(zeilen[:halb]), "".join(zeilen[halb:])
    inhalte.append(
        "<div class='meta'><span>Was drinsteht</span><span>Termine je Sparte</span></div>"
        f"<h2>{len(sparten)} Sparten,<br>alle gleichrangig</h2>"
        f"<div class='spalten' style='margin-top:40px'><div>{links}</div><div>{rechts}</div></div>"
        "<p class='klein' style='margin-top:56px;margin-bottom:48px'>Konzerte, Bühne, Museen, Uni, Bibliothek, Kino-Sonderformate, Clubs und Games – ohne Auswahl und ohne Wertung.</p>")
    rot.append(True)
    tage = []
    for i in range(7):
        d = tag + datetime.timedelta(days=i)
        n = sum(1 for e in evs if not (e.get("end_date") and e["end_date"] > e["date"]) and e["date"] == d.isoformat())
        tage.append((d, n))
    mx = max(n for _, n in tage) or 1
    laufend = sum(1 for e in woche if e.get("end_date") and e["end_date"] > e["date"])
    saeulen = "".join(f"<div class='s'><div class='n'>{n}</div><div class='b' style='height:{max(1, round(470 * n / mx))}px'></div></div>" for _, n in tage)
    daten = "".join(f"<div>{d.day}.<small>{WT[d.weekday()].upper()}</small></div>" for d, _ in tage)
    inhalte.append(
        f"<div class='meta'><span>Die nächsten 7 Tage</span><span>Termine je Tag</span></div>"
        f"<div class='kopf3'><b>{len(woche)}</b><div>Termine<br><span>in 7 Tagen</span></div></div>"
        f"<div class='balken'>{saeulen}</div><div class='tage'>{daten}</div>"
        f"<p class='notiz' style='margin-top:46px;margin-bottom:48px'>Die Balken zeigen die {len(woche) - laufend} Einzeltermine je Tag. Dazu kommen {laufend} Ausstellungen und Angebote, die die ganze Woche über geöffnet sind.</p>")
    rot.append(False)
    inhalte.append(
        "<div class='meta'><span>Wo</span><span>Spielorte in Bayreuth</span></div>"
        f"<div class='paar'><div><b>{len(orte)}</b><span>Spielorte</span></div><div class='r'><b>{quellen}</b><span>Quellen</span></div></div>"
        "<p class='orte'>" + "<span>·</span> ".join(f"<em>{html.escape(o)}</em>" for o in orte if o not in SAMMEL) + "</p>"
        + (f"<p class='notiz box' style='margin-top:44px;margin-bottom:40px'>Dazu {aufzaehlen([SAMMEL[o] for o in orte if o in SAMMEL])}.</p>" if any(o in SAMMEL for o in orte) else ""))
    rot.append(False)
    schritte = [("1", "Filtern", "Nach Tag, Wochenende oder Monat, nach Sparte, Spielort, freiem Eintritt oder mit der Suche."),
                ("2", "Vormerken", "Jeder Termin lässt sich mit einem Klick in den eigenen Kalender übernehmen."),
                ("3", "Zum Veranstalter", "Jeder Eintrag führt zur Originalseite des Hauses, dort gibt es Details und Tickets.")]
    inhalte.append(
        "<div class='meta'><span>So funktioniert es</span><span>Kultur<span class='z'>zettel</span></span></div>"
        + "<div class='trenn'></div>".join(f"<div class='schritt'{' style=\"margin-top:64px\"' if i == 0 else ''}><div class='nr'>{n}</div><div><div class='t'>{t}</div><div class='h'>{h}</div></div></div>"
                  for i, (n, t, h) in enumerate(schritte))
        + "<div class='band' style='margin-top:auto;margin-bottom:48px'>Keine Highlights, keine Empfehlungen, keine Werbung.<br>Kostenlos und ohne Anmeldung.</div>")
    rot.append(False)
    inhalte.append(
        "<div class='meta'><span>Kulturzettel</span><span>@bjoern_rodday</span></div>"
        "<div class='wort' style='margin-top:96px;font-size:236px'>Kultur<span class='z'>zettel</span></div>"
        "<p class='lead' style='margin-top:66px'>Was in Bayreuth kulturell los ist:</p>"
        f"<div class='link'><span>kulturzettel-bayreuth.de</span>{PFEIL.format(w=104, h=66, c=PAPER)}</div>"
        "<p class='klein' style='margin-top:74px;max-width:38ch'>Ein privates Projekt von Björn Rodday. Ohne Gewähr. Maßgeblich sind allein die Angaben der Veranstalter.</p>")
    rot.append(True)

    gesamt = len(inhalte)
    folien = [seite(h, i + 1, gesamt, rot[i]) for i, h in enumerate(inhalte)]
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

    hinweis = f"Stand: {datum_voll}. Ohne Gewähr; maßgeblich sind die Angaben der Veranstalter."
    text = ("Was ist in Bayreuth los?\n\n"
            f"{len(evs)} Kulturtermine. {len(sparten)} Sparten. Ein Kalender.\n\n"
            "Mit dem Kulturzettel findest Du Kulturtermine in Bayreuth für die kommenden zwei Monate – von Konzerten und Theater "
            "über Ausstellungen und Lesungen bis zu Clubabenden, Kinderprogramm und Games.\n\n"
            f"In den nächsten sieben Tagen sind {len(woche)} Termine und laufende Angebote erfasst. Einen Überblick findest Du beim Durchwischen.\n\n"
            "Auf der Website kannst Du nach Tag, Sparte, Spielort oder freiem Eintritt filtern und Termine in Deinen Kalender übernehmen. "
            "Für Details und Tickets führt jeder Eintrag direkt zum Veranstalter.\n\n"
            "Kostenlos und ohne Anmeldung. Ein privates Projekt von mir.\n\n"
            f"kulturzettel-bayreuth.de\n\n{hinweis}\n\n"
            "#Bayreuth #KulturBayreuth #Kulturkalender #Veranstaltungen #Oberfranken")
    li = ("Bayreuth hat viel Kultur. Die Termine dafür findet man auf vielen verschiedenen Websites.\n\n"
          "Mit dem Kulturzettel möchte ich den Überblick erleichtern. Nach Kulturtöpfe, meiner Übersicht über Förderprogramme für Kulturprojekte, "
          "ist das mein zweites privates Projekt: ein Kalender, der die Kulturtermine in Bayreuth für die kommenden zwei Monate bündelt. "
          f"Aktuell sind {len(evs)} Einträge aus {len(sparten)} Sparten und {quellen} Quellen erfasst – an {len(orte)} Spielorten. "
          f"Für die nächsten sieben Tage sind es {len(woche)} Termine und laufende Angebote.\n\n"
          "Konzerte, Theater, Ausstellungen, Lesungen, Vorträge, Clubabende, Kinderprogramm und Games stehen gleichrangig nebeneinander. "
          "Es gibt keine redaktionelle Auswahl von Highlights und keine Werbung.\n\n"
          "Die Suche lässt sich nach Tag, Sparte, Spielort und freiem Eintritt eingrenzen. Termine können in den eigenen Kalender übernommen werden. "
          "Jeder Eintrag verlinkt auf die Originalseite des Veranstalters mit weiteren Informationen und Tickets.\n\n"
          "Kostenlos und ohne Anmeldung.\n\n"
          "https://kulturzettel-bayreuth.de\n\n"
          "Hinweise auf fehlende Termine oder Quellen sind willkommen.\n\n"
          f"{hinweis}\n\n"
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
