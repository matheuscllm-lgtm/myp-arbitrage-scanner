"""Bug A + Bug B investigation:
  A) Find M-Rayquaza Jumbo product in XY 7 (Ancient Origins) — confirm title pattern
  B) Fetch Flareon VMAX 018/203 product page, inspect seller table flag-icons + texts

Outputs: prints all relevant rows + dumps raw HTML excerpts to .debug/ for review.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import re
from pathlib import Path

import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper(
    browser={"browser": "firefox", "platform": "windows", "desktop": True},
)
scraper.headers.update({
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
})

DEBUG = Path(__file__).resolve().parent.parent / ".debug"
DEBUG.mkdir(exist_ok=True)

def fetch(url):
    print(f"\n=== GET {url}")
    r = scraper.get(url, timeout=30)
    print("  status:", r.status_code, "len:", len(r.text))
    return r

# ── Bug B: Flareon VMAX 018/203 ──
url_flareon = "https://mypcards.com/pokemon/produto/229412/flareon-vmax"
r = fetch(url_flareon)
(DEBUG / "flareon_018_raw.html").write_text(r.text, encoding="utf-8")
soup = BeautifulSoup(r.text, "lxml")

print("\n--- Flareon name (h1) ---")
h1 = soup.select_one("h1")
print("  ", h1.get_text(strip=True) if h1 else "(no h1)")

print("\n--- Flareon .estat-tcg ---")
tcg = soup.select_one(".estat-tcg")
if tcg:
    print("  text:", tcg.get_text(strip=True)[:200])

print("\n--- Flareon .estatistica-ultimo ---")
last = soup.select_one(".estatistica-ultimo")
if last:
    print("  text:", last.get_text(strip=True)[:200])

print("\n--- Seller tables (table.table-striped.table-bordered) ---")
tables = soup.select("table.table-striped.table-bordered")
print(f"  found {len(tables)} tables")

for ti, t in enumerate(tables):
    print(f"\n  === Table {ti} ===")
    rows = t.find_all("tr")
    for ri, row in enumerate(rows):
        row_text = row.get_text(" ", strip=True)
        if "R$" not in row_text:
            continue
        # flag-icon detection (same as scanner)
        flag_el = row.select_one("span.flag-icon[title]")
        flag_title = flag_el.get("title", "").strip() if flag_el else None
        # also collect ALL [title] values
        all_titles = [el.get("title", "").strip() for el in row.select("[title]") if el.get("title")]
        # classes on flag-icon
        flag_classes = flag_el.get("class") if flag_el else None
        is_nm = ("NM" in row_text.upper()) or ("QUASE NOVA" in row_text.upper()) or ("NEAR MINT" in row_text.upper())
        print(f"    row {ri}: flag-icon.title={flag_title!r} classes={flag_classes} NM={is_nm}")
        print(f"      text: {row_text[:160]}")
        print(f"      all [title]: {all_titles[:8]}")

# ── Bug A: hunt for Jumbo products in XY 7 ──
print("\n\n========================================")
print("=== Bug A: Jumbo hunt in XY 7 (Ancient Origins) ===")
print("========================================")
# We don't know the XY 7 edition URL but we can search the catalog
# Quick alternative: try mypcards search endpoint or scrape the edition listing
# Use the API endpoint for products by query
api_url = "https://mypcards.com/api/v1/products?q=jumbo+rayquaza"
try:
    r = fetch(api_url)
    print("  api response preview:", r.text[:500])
except Exception as e:
    print("  api err:", e)

# Also try generic search slug
search = "https://mypcards.com/pokemon/produtos?search=jumbo"
r = fetch(search)
(DEBUG / "jumbo_search.html").write_text(r.text, encoding="utf-8")
soup2 = BeautifulSoup(r.text, "lxml")
# Find product cards
links = soup2.select("a[href*='/pokemon/produto/']")
print(f"  found {len(links)} product links on /produtos?search=jumbo")
seen = set()
jumbo_links = []
for a in links:
    href = a.get("href", "")
    if href in seen:
        continue
    seen.add(href)
    text = a.get_text(" ", strip=True)
    if "jumbo" in text.lower():
        jumbo_links.append((text[:80], href))

print(f"  filtered jumbo titles: {len(jumbo_links)}")
for txt, href in jumbo_links[:20]:
    print(f"    - {txt!r}  →  {href}")
