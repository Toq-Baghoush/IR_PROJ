import re
import json

LOG_FILE = "/mnt/user-data/uploads/New_Text_Document__2_.txt"
JSON_FILE = "/mnt/user-data/uploads/test3__1_.json"
OUT_JSON  = "/mnt/user-data/outputs/common_shows.json"

# ── 1. Parse log file ─────────────────────────────────────────────────────────
RE_SHOW = re.compile(r'\[shows\] INFO: Show: (.+?), seasons=(\S+), episodes=(\d+|None)')
RE_URL  = re.compile(r'\[TvshowCrawlerPipeline\] INFO: Processing item: (https://seriesgraph\.com/show/\S+)')

def safe_int(val):
    v = val.strip().strip(",")
    return None if v == "None" else int(v)

txt_shows = {}
with open(LOG_FILE, encoding="utf-8") as f:
    lines = f.readlines()

i = 0
while i < len(lines):
    m = RE_SHOW.search(lines[i])
    if m:
        name     = m.group(1).strip()
        seasons  = safe_int(m.group(2))
        episodes = safe_int(m.group(3))
        url = None
        for j in range(i + 1, min(i + 5, len(lines))):
            mu = RE_URL.search(lines[j])
            if mu:
                url = mu.group(1).strip().rstrip("/")
                break
        if url:
            txt_shows[url] = {"showname": name, "seasons": seasons, "episodes": episodes}
    i += 1

print(f"[TXT]  {len(txt_shows)} shows parsed")

# ── 2. Load JSON ──────────────────────────────────────────────────────────────
with open(JSON_FILE, encoding="utf-8") as f:
    json_data = json.load(f)

json_by_url = {}
for item in json_data:
    url = (item.get("link") or "").strip().rstrip("/")
    if url:
        json_by_url[url] = item

print(f"[JSON] {len(json_by_url)} shows loaded")

# ── 3. Intersection only ──────────────────────────────────────────────────────
common_urls = set(txt_shows.keys()) & set(json_by_url.keys())
print(f"[COMMON] {len(common_urls)} shows found in both files")

result = []
for url in common_urls:
    txt = txt_shows[url]
    jsn = json_by_url[url]
    result.append({
        "link":     url,
        "showname": txt["showname"],
        "seasons":  txt["seasons"],
        "episodes": txt["episodes"],
        "rating":   jsn["rating"],
        "poster":   jsn["poster"],
    })

result.sort(key=lambda x: (x["showname"] or "").lower())

# ── 4. Save ───────────────────────────────────────────────────────────────────
import os
os.makedirs("/mnt/user-data/outputs", exist_ok=True)

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"[OUT]  {OUT_JSON}")
print(f"\nSample:")
print(json.dumps(result[:2], ensure_ascii=False, indent=2))
