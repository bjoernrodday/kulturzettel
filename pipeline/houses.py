import re
RULES=[
 (r'friedrichsforum|stadthalle','Friedrichsforum'),
 (r'zentrum(?!.*evangel)|europasaal','Das Zentrum'),
 (r'glashaus','Glashaus'),
 (r'opernhaus','Markgräfliches Opernhaus'),
 (r'steingraeber','Steingraeber Haus'),
 (r'neuneinhalb','Neuneinhalb'),
 (r'becher','Becher Bräu'),
 (r'liebesbier|maisel','Liebesbier'),
 (r'studiobühne','Studiobühne'),
 (r'kulturstadl','Brandenburger Kulturstadl'),
 (r'reichshof','Kulturbühne Reichshof'),
 (r'rw21|stadtbibliothek|volkshochschule','RW21'),
 (r'kunstmuseum|barockrathaus','Kunstmuseum'),
 (r'kunstverein','Kunstverein'),
 (r'historisches museum','Historisches Museum'),
 (r'wagner museum|wagner-museum|wahnfried','Richard Wagner Museum'),
 (r'urwelt','Urwelt-Museum'),
 (r'iwalewa','Iwalewahaus'),
 (r'eremitage|neues schloss|schloss fantaisie|schloss birken|schloss colmdorf','Schlösser & Eremitage'),
 (r'kirche|kantorei|hochschule für evangelische','Kirchen'),
 (r'tourist|treffpunkt','Stadtführungen'),
 (r'oberfrankenhalle','Oberfrankenhalle'),
 (r'cineplex|kino','Kino'),
 (r'botanischer','Botanischer Garten'),
 (r'fabrik|frisco|tanzbar|schokofabrik|club','Clubs'),
 (r'winterdorf','Winterdorf'),
 (r'universität|uni bayreuth|audimax','Universität'),
]
def house(v):
    s=(v or '').lower()
    for p,h in RULES:
        if re.search(p,s): return h
    return 'Weitere Orte'
