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
            for k in ['time','subtitle','price','end_date','organizer','url']:
                if not dup.get(k) and e.get(k): dup[k]=e[k]
            dup['tags']=list(dict.fromkeys((dup.get('tags') or [])+(e.get('tags') or [])))[:5]
            dup.setdefault('sources',[]).extend(e.get('sources') or [e.get('source')])
            continue
        e=dict(e); e['sources']=e.get('sources') or [e.get('source')]
        out.append(e)
from houses import house
for e in out:
    e['house']=house(e['venue']) if house(e['venue'])!='Weitere Orte' else house(e['venue']+' '+(e.get('organizer') or '')+' '+e['title'])
    e['id']=hashlib.md5((e['date']+norm(e['title'])).encode()).hexdigest()[:10]
    e.pop('source',None)
    e['sources']=[s for s in dict.fromkeys(e['sources']) if s]
out.sort(key=lambda e:(e['date'],e.get('time') or '99'))
json.dump({'sources':json.load(open('sources.json')),'updated':NOW.isoformat(timespec='minutes'),'events':out},open('events.json','w'),ensure_ascii=False,indent=0)
print(len(out))
