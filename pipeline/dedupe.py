import json,re,difflib
D=json.load(open('events.json'));ev=D['events']
def n(s): return re.sub(r'\W+',' ',s.lower()).strip()
MAN=[]  # manuelle Dublettenpaare (keep_id, drop_id), je Lauf nach Sichtung ergänzen
drop=set()
def absorb(k,d):
    k['sources']=list(dict.fromkeys(k['sources']+d['sources']))
    k['end_date']=max(k.get('end_date') or k['date'],d.get('end_date') or d['date'])
    for f in ['time','subtitle','price','organizer']:
        if not k.get(f) and d.get(f): k[f]=d[f]
    drop.add(d['id'])
byid={e['id']:e for e in ev}
for a,b in MAN:
    if a in byid and b in byid and a not in drop and b not in drop: absorb(byid[a],byid[b]); byid[a]['end_date']=byid[a]['end_date'] if byid[a]['end_date']>byid[a]['date'] else None
M=[e for e in ev if ismulti(e)]
for i,a in enumerate(M):
    if a['id'] in drop: continue
    for b in M[i+1:]:
        if b['id'] in drop: continue
        if a['date']<=b['end_date'] and b['date']<=a['end_date'] and difflib.SequenceMatcher(None,n(a['title']),n(b['title'])).ratio()>=0.88:
            absorb(a,b)
for a in M:
    if a['id'] in drop: continue
    for b in ev:
        if b['id'] in drop or ismulti(b) or b is a: continue
        if a['date']<=b['date']<=a['end_date'] and difflib.SequenceMatcher(None,n(a['title']),n(b['title'])).ratio()>0.8:
            a['sources']=list(dict.fromkeys(a['sources']+b['sources'])); drop.add(b['id'])
D['events']=[e for e in ev if e['id'] not in drop]
json.dump(D,open('events.json','w'),ensure_ascii=False,indent=0)
print(len(drop),len(D['events']))
