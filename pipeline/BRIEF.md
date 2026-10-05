# Kulturzettel Bayreuth – Sammelauftrag 
Zeitfenster: Termine, die zwischen HEUTE und HEUTE+2 MONATE beginnen (laufende Ausstellungen/Reihen, die schon begonnen haben und noch laufen, ebenfalls aufnehmen).
Nur WebFetch/WebSearch verwenden (Shell-Downloads blockt der Proxy). Lokale Shell/Python nur zum Schreiben/Prüfen der JSON-Datei.

Schema je Termin (Datei = JSON-Array, UTF-8):
{"title":..., "subtitle":str|null, "date":"YYYY-MM-DD", "end_date":str|null, "time":"HH:MM"|null, "venue":..., "organizer":str|null,
 "category": genau eine aus [Klassik, Oper & Musiktheater, Theater, Pop, Rock & Jazz, Tanz, Kabarett & Comedy, Literatur, Ausstellung, Vortrag & Diskurs, Film, Kinder & Familie, Club & Party, Führung, Festival, Games],
 "tags":[2–4 kurze Schlagworte], "description":"1–2 Sätze, eigene Worte, deutsch, sachlich, ohne Werbeton", "price":str|null, "url":..., "source":"Name des Veranstalters"}

Regeln:
- Nur Kultur, nur Stadt Bayreuth (keine Umlandorte). Nichts erfinden. Abgesagte Termine weglassen.
- Kultur weit gefasst, auch Games/LAN/E-Sport. Keine Wertungen, keine Highlights.
- URL IMMER ZUR ORIGINALQUELLE: Detailseite des Veranstalters/der Spielstätte, sonst deren Programmseite, sonst deren eigener Ticketshop (okticket, reservix, eventim-light, motion, tickets4arts …). region-bayreuth.de als Link nur, wenn der Veranstalter ausschließlich dort veröffentlicht; dann source "<Veranstalter> (nur Stadt, Land, Leben)".
- Private Aggregatoren (eventfinder, bayreuth4U, Kurier-Kalender, regioactive, concerti, concerticket, erlebe.bayern) NUR zum Entdecken/Gegenprüfen; keine Texte/Listen übernehmen. Nur wenn ein Termin nirgends sonst zu finden ist: reine Fakten + eigene Kurzbeschreibung, source "Hinweis: <Aggregator>", url = Aggregator-Detailseite.
- Beschreibungen immer eigene Worte.
- Serien und regelmäßige Führungen als EIN Eintrag mit end_date (Termine in description nennen).
- Friedrichsforum: venue Format "Friedrichsforum – <Fläche>" mit Flächenbezeichnung genau wie auf friedrichsforum.de (Großer Saal, Kleiner Saal, Balkonsaal, Hofgartensaal, Lounge, Wandelhalle …). Nie "Stadthalle".
- Altbestand von gestern liegt in events_alt.json im Arbeitsordner (Feld events) – nur zum Abgleich, was schon bekannt ist. Deine Datei soll aber alle Termine deiner Quellen im Zeitfenster enthalten (frisch bestätigt), nicht nur neue. Wenn eine Quelle nicht erreichbar ist: notieren und weitermachen.
- Fang nicht an, das Ergebnis lange zu polieren: lieber vollständig und korrekt. Speichere Zwischenstände regelmäßig in deine Datei (gültiges JSON).
- Am Ende antworte kurz: Anzahl Einträge, nicht erreichbare Quellen, Liste der Termine, die NICHT im Altbestand waren (Titel + Datum), und ggf. neue ergiebige Quellen (Name + URL).
