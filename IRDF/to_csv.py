import json
import csv
from collections import Counter, defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
IN_FILE = "shows.json"
OUT_CSV = "shows.csv"
REPORT  = "conversion_report.txt"

# Locked field order — never change without versioning your data
FIELDS = ["link", "showname", "seasons", "episodes", "rating", "poster"]

# Null sentinel for CSV — empty string means "missing", not zero, not "None"
MISSING = ""

# TMDB poster size — document for future reference
TMDB_POSTER_SIZE = "w400"

# ── Load ──────────────────────────────────────────────────────────────────────
with open(IN_FILE, encoding="utf-8") as f:
    data = json.load(f)

print(f"[LOAD] {len(data)} records from {IN_FILE}")
print("=" * 60)

# ── Step 1: Audit raw data ────────────────────────────────────────────────────
print("\n[AUDIT] Raw data inspection:")

null_by_field = defaultdict(list)
for field in FIELDS:
    for d in data:
        if d.get(field) is None or d.get(field) == "":
            null_by_field[field].append(d.get("showname", f"row_{data.index(d)}"))

for field in FIELDS:
    count = len(null_by_field[field])
    print(f"  {field:10} nulls: {count}" + (f" → {null_by_field[field][:3]}..." if count > 3 else (f" → {null_by_field[field]}" if count else "")))

# ── Step 2: Detect duplicates ─────────────────────────────────────────────────
print("\n[AUDIT] Duplicate inspection:")

# True duplicates: same link (same show, scraped twice)
link_seen   = {}
true_dups   = []   # (index, showname, link)
for i, d in enumerate(data):
    link = (d.get("link") or "").strip().rstrip("/")
    if link in link_seen:
        true_dups.append({
            "index":    i,
            "showname": d.get("showname"),
            "link":     link,
            "kept_at":  link_seen[link],
        })
    else:
        link_seen[link] = i

# Same name, different link: different shows with the same title
name_groups = defaultdict(list)
for d in data:
    name = (d.get("showname") or "").strip().lower()
    link = (d.get("link") or "").strip().rstrip("/")
    name_groups[name].append(link)

same_name_diff_link = {
    k: v for k, v in name_groups.items()
    if len(v) > 1 and len(set(v)) == len(v)  # multiple links, all different
}

true_dup_links = {d["link"] for d in true_dups}

print(f"  True duplicates (same link)          : {len(true_dups)} → will be dropped")
for d in true_dups:
    print(f"    DROP  '{d['showname']}' at row {d['index']} (kept row {d['kept_at']})")

print(f"  Same name, different link (diff show): {len(same_name_diff_link)} → will be kept")
for name, links in same_name_diff_link.items():
    print(f"    KEEP  '{name}':")
    for l in links:
        print(f"           {l}")

# ── Step 3: Process rows ──────────────────────────────────────────────────────
print("\n[PROCESS] Cleaning and validating rows...")

cleaned  = []
skipped  = []
dropped  = []
warnings = []

seen_links = set()

for i, row in enumerate(data):

    # ── Required fields: skip if missing ─────────────────────────────────────
    raw_link = (row.get("link") or "").strip().rstrip("/")
    raw_name = " ".join((row.get("showname") or "").split())

    if not raw_link:
        msg = f"Row {i} '{raw_name}' → missing link, skipped"
        print(f"  [SKIP] {msg}")
        skipped.append({"row": i, "showname": raw_name, "reason": "missing link"})
        continue

    if not raw_name:
        msg = f"Row {i} '{raw_link}' → missing showname, skipped"
        print(f"  [SKIP] {msg}")
        skipped.append({"row": i, "link": raw_link, "reason": "missing showname"})
        continue

    # ── True duplicate: same link seen before → drop ──────────────────────────
    if raw_link in seen_links:
        msg = f"Row {i} '{raw_name}' → duplicate link, dropped"
        print(f"  [DROP] {msg}")
        dropped.append({"row": i, "showname": raw_name, "link": raw_link, "reason": "duplicate link"})
        continue

    seen_links.add(raw_link)

    # ── seasons: int or None ──────────────────────────────────────────────────
    seasons = row.get("seasons")
    if seasons is not None:
        try:
            seasons = int(seasons)
            if seasons < 0:
                warnings.append(f"'{raw_name}' seasons={seasons} negative → null")
                print(f"  [WARN] '{raw_name}' seasons={seasons} is negative → setting null")
                seasons = None
        except (ValueError, TypeError):
            warnings.append(f"'{raw_name}' seasons={seasons} bad type → null")
            print(f"  [WARN] '{raw_name}' seasons={seasons} invalid → setting null")
            seasons = None

    # ── episodes: int or None ─────────────────────────────────────────────────
    episodes = row.get("episodes")
    if episodes is not None:
        try:
            episodes = int(episodes)
            if episodes < 0:
                warnings.append(f"'{raw_name}' episodes={episodes} negative → null")
                print(f"  [WARN] '{raw_name}' episodes={episodes} is negative → setting null")
                episodes = None
        except (ValueError, TypeError):
            warnings.append(f"'{raw_name}' episodes={episodes} bad type → null")
            print(f"  [WARN] '{raw_name}' episodes={episodes} invalid → setting null")
            episodes = None

    # ── rating: float, clamped 0.0–10.0, 1 decimal or None ───────────────────
    rating = row.get("rating")
    if rating is not None:
        try:
            rating = float(rating)
            if not (0.0 <= rating <= 10.0):
                warnings.append(f"'{raw_name}' rating={rating} out of range → clamped")
                print(f"  [WARN] '{raw_name}' rating={rating} out of range → clamping")
                rating = max(0.0, min(10.0, rating))
            rating = round(rating, 1)
        except (ValueError, TypeError):
            warnings.append(f"'{raw_name}' rating={rating} bad type → null")
            print(f"  [WARN] '{raw_name}' rating={rating} invalid → setting null")
            rating = None

    # ── poster: string or None ────────────────────────────────────────────────
    poster = (row.get("poster") or "").strip()
    if not poster:
        poster = None

    # ── Build clean row: None → "" for all nullable fields ───────────────────
    cleaned.append({
        "link":     raw_link,
        "showname": raw_name,
        "seasons":  MISSING if seasons  is None else seasons,
        "episodes": MISSING if episodes is None else episodes,
        "rating":   MISSING if rating   is None else rating,
        "poster":   MISSING if poster   is None else poster,
    })

print(f"\n[RESULT] {len(cleaned)} rows clean | {len(skipped)} skipped | {len(dropped)} dropped | {len(warnings)} warnings")

# ── Step 4: Write CSV ─────────────────────────────────────────────────────────
# utf-8-sig → BOM so Excel reads accented chars correctly
# QUOTE_ALL  → every field quoted, safe for commas in shownames
with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=FIELDS,
        quoting=csv.QUOTE_ALL,
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(cleaned)

print(f"[OUT]  {OUT_CSV}  ({len(cleaned)} rows)")

# ── Step 5: Conversion report ─────────────────────────────────────────────────
ratings = [r["rating"] for r in cleaned if r["rating"] != MISSING]

report = [
    "=== CONVERSION REPORT ===",
    f"Input file    : {IN_FILE}",
    f"Output file   : {OUT_CSV}",
    f"Input records : {len(data)}",
    f"Output rows   : {len(cleaned)}",
    f"Skipped rows  : {len(skipped)}",
    f"Dropped rows  : {len(dropped)}",
    f"Warnings      : {len(warnings)}",
    f"Field order   : {FIELDS}",
    "",
    "=== NULL HANDLING ===",
    "Strategy: None and empty string both saved as '' in CSV",
    "  '' means MISSING — not zero, not unknown, not 'None'",
]
for field in FIELDS:
    count = len(null_by_field[field])
    if count:
        report.append(f"  {field} ({count} nulls): {null_by_field[field]}")
    else:
        report.append(f"  {field}: no nulls")

report += [
    "",
    "=== DUPLICATE HANDLING ===",
    f"True duplicates (same link) dropped : {len(dropped)}",
]
for d in dropped:
    report.append(f"  row {d['row']} '{d['showname']}' → {d['reason']}")

report.append(f"Same name, different link (kept)    : {len(same_name_diff_link)}")
for name, links in same_name_diff_link.items():
    report.append(f"  '{name}': {links}")

report += [
    "",
    "=== WARNINGS ===",
]
for w in warnings:
    report.append(f"  {w}")
if not warnings:
    report.append("  none")

report += [
    "",
    "=== ENCODING ===",
    "  ensure_ascii=False : accented chars preserved (é, à, ö...)",
    "  utf-8-sig          : BOM added for Excel compatibility",
    "",
    "=== RATING STATS ===",
]
if ratings:
    report += [
        f"  min : {min(ratings)}",
        f"  max : {max(ratings)}",
        f"  avg : {sum(ratings)/len(ratings):.2f}",
        f"  count with rating : {len(ratings)} / {len(cleaned)}",
    ]

report += [
    "",
    "=== POSTER ===",
    f"  TMDB size used : {TMDB_POSTER_SIZE}",
    f"  base URL       : https://image.tmdb.org/t/p/{TMDB_POSTER_SIZE}/",
]

with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print(f"[LOG]  {REPORT}")
