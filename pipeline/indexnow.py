#!/usr/bin/env python3
"""Meldet die von build_seo.py geänderten Adressen an IndexNow (Bing, Yandex, Seznam u. a.).
Google nimmt nicht an IndexNow teil und liest die Sitemap."""
import json, os, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
key = open(os.path.join(ROOT, "pipeline/indexnow_key.txt")).read().strip()
import re
if "--alle" in sys.argv:
    urls = re.findall(r"<loc>(.*?)</loc>", open(os.path.join(ROOT, "sitemap.xml")).read())
else:
    urls = [u.strip() for u in open(os.path.join(ROOT, "pipeline/geaendert.txt")) if u.strip()]
if not urls:
    print("nichts zu melden"); sys.exit(0)
body = json.dumps({"host": "kulturzettel-bayreuth.de", "key": key,
                   "keyLocation": f"https://kulturzettel-bayreuth.de/{key}.txt", "urlList": urls[:10000]}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("IndexNow:", r.status, len(urls), "Adressen")
except urllib.error.HTTPError as e:
    print("IndexNow-Fehler:", e.code, e.read()[:300]); sys.exit(0)
