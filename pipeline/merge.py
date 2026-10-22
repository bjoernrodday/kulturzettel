import json,re,hashlib,difflib,sys,datetime,glob,zoneinfo
NOW=datetime.datetime.now(zoneinfo.ZoneInfo('Europe/Berlin'))
TODAY=sys.argv[1] if len(sys.argv)>1 else NOW.date().isoformat()
def _plus2m(iso):
    import calendar
    y,m,d=map(int,iso.split('-')); m+=2
    if m>12: y,m=y+1,m-12
    return f"{y:04d}-{m:02d}-{min(d,calendar.monthrange(y,m)[1]):02d}"
HORIZON=_plus2m(TODAY)
files=sorted(glob.glob('events_neu_*.json'))+[f for f in sorted(glob.glob('events_*.json')) if not f.startswith('events_neu_') and f!='events_alt.json']+glob.glob('events_alt.json')
def norm(s):
    s=(s or '').lower()
    s=re.sub(r'[„“"\'’`´:–—\-!?.,()|/&+]',' ',s)
    return re.sub(r'\s+',' ',s).strip()
STOP=set('der die das und mit im in am an den dem des ein eine zu zum zur von für auf lesung ausstellung führung führungen konzert live öffentliche öffentlich vortrag'.split())
def toks(n): return set(w for w in n.split() if w not in STOP and len(w)>2)
out=[]
for f in files:
    data=json.load(open(f)); data=data['events'] if isinstance(data,dict) else data
    for e in data:
        if re.search(r'abgesagt|entfällt|verschoben',(e.get('title','')+' '+(e.get('subtitle') or '')),re.I): continue
        if not e.get('date') or not e.get('title'): continue
        last=e.get('end_date') or e['date']
        if last<TODAY: continue
        if e['date']>HORIZON: continue
        n=norm(e['title']); dup=None
        for o in out:
            if o['date']!=e['date']: continue
            on=norm(o['title'])
            a,b=toks(n),toks(on)
            if on==n or (len(n)>5 and (n in on or on in n)) or difflib.SequenceMatcher(None,n,on).ratio()>0.78 or (a and b and (a<=b or b<=a or len(a&b)/len(a|b)>=0.6)):
                dup=o;break
        if dup:
            # Nur Angaben desselben Termins übernehmen (gleiches Datum ist hier garantiert);
            # Preis nur, wenn beide Einträge keine Serie sind – sonst könnte ein Probe-/Einzelpreis auf die Serie rutschen
            for k in ['time','subtitle','end_date','organizer','url']:
                if not dup.get(k) and e.get(k): dup[k]=e[k]
            if not dup.get('price') and e.get('price') and not (dup.get('end_date') or e.get('end_date')): dup['price']=e['price']
            if e.get('termine'):
                have={t.get('date') for t in dup.get('termine') or []}
                dup['termine']=(dup.get('termine') or [])+[t for t in e['termine'] if t.get('date') not in have]
            dup['tags']=list(dict.fromkeys((dup.get('tags') or [])+(e.get('tags') or [])))[:5]
            dup.setdefault('sources',[]).extend(e.get('sources') or [e.get('source')])
            continue
        e=dict(e); e['sources']=e.get('sources') or [e.get('source')]
        out.append(e)
# Produktionen mit festen Vorstellungen: vergangene Termine streichen, Datum/Ende aus den Terminen ableiten
kept=[]
for e in out:
    if e.get('termine'):
        ts=sorted({t['date']:t for t in e['termine'] if t.get('date') and TODAY<=t['date']<=HORIZON}.values(),key=lambda t:(t['date'],t.get('time') or '99'))
        if not ts: continue
        if len(ts)==1:
            e['date'],e['time']=ts[0]['date'],ts[0].get('time') or e.get('time'); e['end_date']=None
            if ts[0].get('hinweis'): e['hinweis']=ts[0]['hinweis']
            e.pop('termine',None)
        else:
            e['termine']=ts; e['date']=ts[0]['date']; e['end_date']=ts[-1]['date']; e['time']=ts[0].get('time') or e.get('time')
    kept.append(e)
out=kept
from houses import house
for e in out:
    e['house']=house(e['venue']) if house(e['venue'])!='Weitere Orte' else house(e['venue']+' '+(e.get('organizer') or '')+' '+e['title'])
    e['id']=hashlib.md5((e['date']+norm(e['title'])).encode()).hexdigest()[:10]
    e.pop('source',None)
    e['sources']=[s for s in dict.fromkeys(e['sources']) if s]
out.sort(key=lambda e:(e['date'],e.get('time') or '99'))
json.dump({'sources':json.load(open('sources.json')),'updated':NOW.isoformat(timespec='minutes'),'events':out},open('events.json','w'),ensure_ascii=False,indent=0)
print(len(out))
