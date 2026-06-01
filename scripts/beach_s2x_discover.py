#!/usr/bin/env python3
"""
S2X Phase A — Discovery URL venue da sitemap spiagge.it.
"""
import re
import csv
import time
import requests
from datetime import datetime, timezone

HEADERS = {"User-Agent": "SurPrice-Research/1.0 (research@surprice.it)"}
SITEMAPS = [
    "https://www.spiagge.it/stabilimenti_01/sitemap.xml",
    "https://www.spiagge.it/stabilimenti_02/sitemap.xml",
    "https://www.spiagge.it/stabilimenti_03/sitemap.xml",
]
OUT_CSV = "raw_sources/beach_s2x_spiagge_url_list.csv"

# Match URL pattern: /stabilimenti-balneari/{id}-{slug}/
VENUE_RE = re.compile(r"https://www\.spiagge\.it/stabilimenti-balneari/(\d+)-([^/]+)/")
URL_RE = re.compile(r"<loc>(https://www\.spiagge\.it/stabilimenti-balneari/\d+-[^<]+)</loc>")


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.text


def main():
    discovered = {}
    for sm in SITEMAPS:
        print(f"Fetching {sm}...")
        try:
            xml = fetch(sm)
        except Exception as e:
            print(f"  Error: {e}")
            continue
        urls = URL_RE.findall(xml)
        print(f"  URLs found: {len(urls)}")
        for u in urls:
            m = VENUE_RE.match(u)
            if not m:
                continue
            vid = m.group(1)
            slug = m.group(2)
            discovered[vid] = (u, slug, sm.split("/")[-2])
        time.sleep(2)

    print(f"\nTotal unique venues: {len(discovered)}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["spiagge_venue_id", "spiagge_url", "slug", "sitemap_source", "discovered_at"])
        for vid, (url, slug, src) in sorted(discovered.items(), key=lambda x: int(x[0])):
            w.writerow([vid, url, slug, src, now])
    print(f"Written: {OUT_CSV}")


if __name__ == "__main__":
    main()
