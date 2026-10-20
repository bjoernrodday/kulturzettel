"""Probe: holt die Programmseite des Cineplex Bayreuth (Originalquelle) und speichert
die Rohseite sowie Hinweise auf eingebettete Daten/API-Adressen, damit ein Parser
für die Kinoseite des Kulturzettels geschrieben werden kann. Läuft als GitHub Action."""
import os, re, json, urllib.request, datetime
URL = "https://www.cineplex.de/bayreuth/programm"
UA = {"User-Agent": "Mozilla/5.0 (kulturzettel-bayreuth.de; privater Kulturkalender, Kontakt: siehe Impressum)",
      "Accept": "text/html,application/json"}
OUT = os.path.join(os.path.dirname(__file__), "kino")
os.makedirs(OUT, exist_ok=True)
html = urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=60).read().decode("utf-8", "replace")
open(os.path.join(OUT, "cineplex_raw.html"), "w").write(html)
probe = {"fetched": datetime.datetime.utcnow().isoformat(timespec="minutes") + "Z", "bytes": len(html)}
probe["script_json_ids"] = re.findall(r'<script[^>]*id="([^"]+)"[^>]*type="application/(?:json|ld\+json)"', html)
probe["script_types"] = sorted(set(re.findall(r'<script[^>]*type="([^"]+)"', html)))
probe["api_like_urls"] = sorted(set(re.findall(r'https?://[^"\'\s<>]*(?:api|graphql|json|showtime|performance|vorstellung)[^"\'\s<>]*', html, re.I)))[:200]
probe["relative_api_paths"] = sorted(set(re.findall(r'["\'](/[^"\'\s<>]*(?:api|graphql|showtime|performance)[^"\'\s<>]*)["\']', html, re.I)))[:200]
probe["weitere_count"] = len(re.findall(r'weitere', html))
probe["hhmm_count"] = len(re.findall(r'\b[012]\d:[0-5]\d\b', html))
json.dump(probe, open(os.path.join(OUT, "cineplex_probe.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(probe, indent=1)[:3000])
