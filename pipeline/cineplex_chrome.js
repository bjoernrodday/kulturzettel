// Liest das Programm des Cineplex Bayreuth aus der geöffneten Seite
// https://www.cineplex.de/bayreuth/programm (im normalen Chrome, nach dem Laden).
// Ausführen mit dem javascript_tool von Claude in Chrome. Ergebnis: window.__kp (kompaktes JSON),
// Rückgabe: Anzahl Zeichen und Teile. Danach Teile mit window.__kp.slice(i*900,(i+1)*900) (höchstens 900 Zeichen je Abruf, sonst kürzt das Werkzeug die Ausgabe) abholen.
// Weiterverarbeitung: python3 pipeline/kinopuffer.py <datei mit dem zusammengesetzten JSON>
(() => {
  const raw = (self.__next_f || []).filter(x => x[0] === 1).map(x => x[1]).join('');
  const M = {};
  raw.split('\n').forEach(l => { const m = l.match(/^([0-9a-f]+):(.*)$/); if (m) M[m[1]] = m[2]; });
  const cache = {};
  const R = (x, d) => {
    if (d > 40) return null;
    if (typeof x === 'string' && /^\$[0-9a-f]+$/.test(x)) {
      const k = x.slice(1); if (!(k in M)) return x;
      if (cache[k] !== undefined) return cache[k];
      let o; try { o = JSON.parse(M[k]); } catch (e) { return x; }
      cache[k] = null; const r = R(o, d + 1); cache[k] = r; return r;
    }
    if (Array.isArray(x)) return x.map(y => R(y, d + 1));
    if (x && typeof x === 'object') { const r = {}; for (const k in x) r[k] = R(x[k], d + 1); return r; }
    return x;
  };
  // Seit 11/2026 steht der Schlüssel programUIData nicht mehr wörtlich in der Zeile, die ihn
  // enthält (er wird erst über Verweise erreicht). Daher alle JSON-Zeilen auflösen, statt per Text vorzufiltern.
  const P = {};
  const parsed = k => { if (!(k in P)) { const c = M[k][0]; let o = null; if (c === '{' || c === '[') { try { o = R(JSON.parse(M[k]), 0); } catch (e) {} } P[k] = o; } return P[k]; };
  let list = null;
  for (const k in M) {
    const o = parsed(k); if (!o) continue;
    (function walk(x) { if (list || !x || typeof x !== 'object') return; if (Array.isArray(x.programUIData)) { list = x.programUIData; return; } for (const kk in x) walk(x[kk]); })(o);
    if (list) break;
  }
  // Rückfall: alle Filmobjekte (movieTitle + performances) einsammeln und je Film zusammenführen.
  if (!list) {
    const byId = new Map();
    for (const k in M) {
      if (!M[k].includes('movieTitle')) continue;
      const o = parsed(k); if (!o) continue;
      (function walk(x) {
        if (!x || typeof x !== 'object') return;
        if (Array.isArray(x)) { x.forEach(walk); return; }
        if (typeof x.movieTitle === 'string' && Array.isArray(x.performances)) {
          const id = x.movieWinTicketFilmId || x.movieTitle;
          if (!byId.has(id)) byId.set(id, { m: x, p: new Map() });
          const e = byId.get(id);
          x.performances.forEach(p => p && p.performanceDateAndTime && e.p.set(p.performanceId || (p.performanceDateAndTime + '|' + (p.auditoriumName || '')), p));
          return;
        }
        for (const kk in x) walk(x[kk]);
      })(o);
    }
    if (byId.size) list = [...byId.values()].map(e => Object.assign({}, e.m, { performances: [...e.p.values()] }));
  }
  if (!list) { window.__kp = ''; return 'FEHLER: programUIData nicht gefunden'; }
  const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Berlin' });
  const last = new Date(today + 'T12:00:00Z'); last.setUTCDate(last.getUTCDate() + 4);
  const lastDay = last.toISOString().slice(0, 10);
  const films = [], shows = [];
  list.forEach(m => {
    const ps = (m.performances || []).filter(p => p && p.performanceDateAndTime && !p.performanceIsPaused);
    const sel = ps.filter(p => { const d = p.performanceDateAndTime.slice(0, 10); return d >= today && d <= lastDay; });
    if (!sel.length) return;
    const fi = films.length;
    films.push([m.movieTitle, m.movieDuration || null, (m.movieAgeRating ?? null), m.movieGenres || '', !!m.movieIsNew,
      (m.movieLaunchDateGermany || '').slice(0, 10), m.movieDetailsUrl || '', m.movieOriginalLanguage || '']);
    sel.forEach(p => {
      const rc = p.releaseCapabilities || {}, ac = p.auditoriumCapabilities || {};
      const fl = [];
      if (rc.twoDthreeDCapability === '3D') fl.push('3D');
      (rc.showboxMiddleInfo || []).forEach(x => x && fl.push(/^(OV|OmU|OmeU|OmdU)$/.test(x) && m.movieOriginalLanguage ? x + ' ' + m.movieOriginalLanguage : String(x)));
      (rc.technicalCapabilities || []).forEach(x => x && !/atmos/i.test(x) && fl.push(String(x)));
      if (p.isAtmos) fl.push('Dolby Atmos');
      if (p.associatedCategory) fl.push(String(p.associatedCategory));
      if (ac.auditoriumHasBarrierefrei) fl.push('Barrierefrei');
      shows.push([fi, p.performanceDateAndTime.slice(0, 10), p.performanceDateAndTime.slice(11, 16), p.auditoriumName || '',
        /franz|gloria/i.test(p.centerName || '') ? 1 : 0, [...new Set(fl)].join('|')]);
    });
  });
  window.__kp = JSON.stringify({ a: new Date().toISOString(), t: today, f: films, s: shows });
  return window.__kp.length + ' Zeichen, ' + Math.ceil(window.__kp.length / 900) + ' Teile, ' + films.length + ' Filme, ' + shows.length + ' Vorstellungen';
})()
