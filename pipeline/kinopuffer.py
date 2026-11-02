#!/usr/bin/env python3
"""Schreibt kinopuffer.json aus dem Chrome-Abruf des Cineplex-Programms.

Aufruf aus dem Repository-Hauptordner:
    python3 pipeline/kinopuffer.py <kompaktes-json> [--soll-filme N --soll-vorstellungen M]

<kompaktes-json> ist die Ausgabe von pipeline/cineplex_chrome.js (window.__kp), in Teilen
abgeholt und unverändert zusammengesetzt. Mit --soll-filme/--soll-vorstellungen werden die
Zahlen geprüft, die das Skript im Browser gemeldet hat (Schutz gegen Übertragungsfehler).

kinopuffer.json: {"abgerufen": ISO-Zeit, "quelle": ..., "tage": {"JJJJ-MM-TT": {"vollstaendig": bool,
"films": [Film wie in filme.json]}}}. Die Kinoseite zeigt immer nur den heutigen Tag; die übrigen
Tage sind Vorrat, falls der Mac ein paar Tage aus ist. Vergangene Tage werden entfernt.
"""
import argparse, datetime as dt, json, os, sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "kinopuffer.json")
TZ = ZoneInfo("Europe/Berlin")
BASE = "https://www.cineplex.de"
G = {"Horrorfilm": "Horror", "Horror": "Horror", "Action": "Action & Abenteuer", "Abenteuer": "Action & Abenteuer",
     "Drama": "Drama", "Komödie": "Komödie", "Familienfilm": "Kinder & Familie", "Kinderfilm": "Kinder & Familie",
     "Animation": "Animation", "Thriller": "Thriller & Krimi", "Krimi": "Thriller & Krimi", "Musik": "Musik",
     "Dokumentation": "Dokumentarfilm", "Dokumentarfilm": "Dokumentarfilm", "Liebesfilm": "Liebesfilm",
     "Romantik": "Liebesfilm", "Science-Fiction": "Science-Fiction & Fantasy", "Fantasy": "Science-Fiction & Fantasy",
     "Sci-Fi": "Science-Fiction & Fantasy"}
EVENT_FLAGS = {"Concerts in Cinema", "Klassik & Co.", "EVENT"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("datei")
    ap.add_argument("--soll-filme", type=int)
    ap.add_argument("--soll-vorstellungen", type=int)
    a = ap.parse_args()
    k = json.load(open(a.datei, encoding="utf-8"))
    if a.soll_filme is not None and len(k["f"]) != a.soll_filme:
        sys.exit(f"Filmzahl passt nicht: {len(k['f'])} statt {a.soll_filme} – Teile neu abholen")
    if a.soll_vorstellungen is not None and len(k["s"]) != a.soll_vorstellungen:
        sys.exit(f"Vorstellungszahl passt nicht: {len(k['s'])} statt {a.soll_vorstellungen} – Teile neu abholen")

    today = dt.datetime.now(TZ).date().isoformat()
    days = {}
    for fi, day, time, room, fg, flags in k["s"]:
        fl = [f for f in flags.split("|") if f]
        # Dolby Atmos zeigt der Cineplex nur bei Franz & Gloria und ULTIMATE an; sonst ist es nur eine Fähigkeit der Kopie
        if not (room.startswith("F&G") or room.startswith("ULTIMATE")):
            fl = [f for f in fl if f != "Dolby Atmos"]
        if room == "4DX" and "4DX" not in fl:
            fl.insert(0, "4DX")
        days.setdefault(day, {}).setdefault(fi, []).append(
            {"time": time, "room": room, "site": "Franz & Gloria" if fg else "Haupthaus", "flags": fl})

    def film(fi, shows, day):
        title, runtime, fsk, genres, is_new, launch, url, lang = k["f"][fi]
        raw = [g.strip() for g in genres.replace("/", ",").split(",") if g.strip()]
        gen = []
        for g in raw:
            m = G.get(g)
            if m and m not in gen:
                gen.append(m)
        badges = []
        if is_new:
            badges.append("NEU")
        cats = {f for s in shows for f in s["flags"]}
        for b in ("Preview", "CineArt", "Sneaks", "Best of Cinema", "Specials", "Concerts in Cinema", "Klassik & Co."):
            if b in cats and b not in badges:
                badges.append("Sneak" if b == "Sneaks" else b)
        if cats & EVENT_FLAGS and "Events & Live" not in gen:
            gen.append("Events & Live")
        week = None
        if launch:
            d0 = dt.date.fromisoformat(launch)
            dd = (dt.date.fromisoformat(day) - d0).days
            if 0 <= dd < 7 * 30:
                week = dd // 7 + 1
        return {"title": title, "venue": "Cineplex Bayreuth", "runtime": runtime,
                "fsk": fsk if isinstance(fsk, int) else None, "genres": gen, "genres_raw": raw, "badges": badges,
                "week": week, "shows": sorted(shows, key=lambda s: s["time"]), "more": False, "note": None,
                "url": BASE + url if url.startswith("/") else (url or BASE + "/bayreuth/programm"),
                "source": "Cineplex Bayreuth"}

    new = {}
    for day, per in days.items():
        if day < today:
            continue
        films = [film(fi, sh, day) for fi, sh in per.items()]
        films.sort(key=lambda f: f["shows"][0]["time"])
        new[day] = films
    # Ein Tag gilt als vollständig, wenn er mindestens 8 Filme oder 60 % der Filmzahl des ersten Tages hat.
    # (Der Cineplex veröffentlicht die neue Woche erst montags/dienstags; vorher stehen ab Donnerstag nur Sonderveranstaltungen.)
    ref = len(new.get(min(new), [])) if new else 0
    tage = {d: {"vollstaendig": len(f) >= 8 or (ref and len(f) >= 0.6 * ref), "films": f} for d, f in sorted(new.items())}

    try:
        old = json.load(open(OUT, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        old = {"tage": {}}
    for d, v in (old.get("tage") or {}).items():
        if d >= today and d not in tage:
            tage[d] = v  # Vorrat aus einem früheren Abruf behalten (der neue Abruf gilt für alle Tage, die er enthält)
    out = {"abgerufen": dt.datetime.now(TZ).isoformat(timespec="minutes"),
           "quelle": "Cineplex Bayreuth, https://www.cineplex.de/bayreuth/programm (Abruf über Chrome)",
           "tage": dict(sorted(tage.items()))}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for d, v in out["tage"].items():
        print(d, len(v["films"]), "Filme", sum(len(f["shows"]) for f in v["films"]), "Vorstellungen",
              "vollständig" if v["vollstaendig"] else "unvollständig")


if __name__ == "__main__":
    main()
