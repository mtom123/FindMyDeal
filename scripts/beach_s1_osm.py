#!/usr/bin/env python3
"""Beach S1 — OSM Overpass query for Italian beach venues."""

import requests
import json
import csv
import time
from datetime import datetime, timezone

OVERPASS = "https://overpass-api.de/api/interpreter"

QUERY = """
[out:json][timeout:300];
area["ISO3166-1"="IT"]->.italy;
(
  node["tourism"="beach_resort"](area.italy);
  way["tourism"="beach_resort"](area.italy);
  node["leisure"="beach_resort"](area.italy);
  way["leisure"="beach_resort"](area.italy);
  node["amenity"="beach_club"](area.italy);
  way["amenity"="beach_club"](area.italy);
  node["name"~"stabilimento|lido|bagni|bagno",i]["natural"!="beach"](area.italy);
  way["name"~"stabilimento|lido|bagni|bagno",i]["natural"!="beach"](area.italy);
);
out center tags;
"""

COASTAL_REGIONS = {
    "Liguria", "Toscana", "Lazio", "Campania", "Calabria", "Sicilia",
    "Puglia", "Marche", "Abruzzo", "Molise", "Emilia-Romagna",
    "Veneto", "Friuli-Venezia Giulia", "Sardegna", "Basilicata",
    "Lombardia",  # lago di garda treated as coastal-adjacent
}

# Province costiere note per filtrare se regione manca
COASTAL_PROVINCES = {
    "Genova", "La Spezia", "Savona", "Imperia",
    "Livorno", "Grosseto", "Massa", "Lucca", "Pisa",
    "Roma", "Latina", "Viterbo",
    "Napoli", "Salerno", "Caserta",
    "Reggio di Calabria", "Cosenza", "Catanzaro", "Crotone", "Vibo Valentia",
    "Palermo", "Catania", "Messina", "Siracusa", "Ragusa", "Agrigento", "Trapani",
    "Bari", "Lecce", "Brindisi", "Taranto", "Foggia",
    "Ancona", "Pesaro", "Ascoli Piceno", "Fermo",
    "Pescara", "Chieti", "Teramo",
    "Campobasso",
    "Rimini", "Ravenna", "Ferrara", "Forlì-Cesena",
    "Venezia", "Rovigo",
    "Trieste", "Gorizia", "Udine",
    "Sassari", "Cagliari", "Nuoro", "Oristano", "Sud Sardegna",
    "Matera", "Potenza",
    # Keep these broad — OSM tags are irregular
}

RETRIEVED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

VENUES_FILE = "raw_sources/beach_s1_venues.csv"

VENUES_FIELDS = [
    "source_platform", "source_venue_id", "venue_name", "venue_url",
    "address", "city", "province", "region", "postal_code",
    "latitude", "longitude", "categories", "price_tier", "rating",
    "rating_count", "phone", "website", "opening_hours",
    "has_menu", "menu_url", "extraction_status", "retrieved_at",
    "google_maps_url", "instagram", "facebook", "booking_provider", "vertical",
]


HEADERS = {
    "User-Agent": "SurPrice-BeachResearch/1.0 (research; contact@surprice.it)",
    "Accept": "application/json",
}

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def fetch_osm():
    print("Querying Overpass API... (may take 1-3 min)")
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            print(f"  Trying {endpoint}")
            r = requests.post(endpoint, data={"data": QUERY}, headers=HEADERS, timeout=600)
            if r.status_code == 200:
                return r.json()
            print(f"  Status {r.status_code}, trying next...")
        except Exception as e:
            print(f"  Error: {e}, trying next...")
        time.sleep(3)
    raise RuntimeError("All Overpass endpoints failed")


def extract_coord(el):
    if el["type"] == "node":
        return el.get("lat"), el.get("lon")
    # way/relation with center
    center = el.get("center", {})
    return center.get("lat"), center.get("lon")


def build_venue(el):
    tags = el.get("tags", {})
    lat, lon = extract_coord(el)
    name = tags.get("name", "").strip()
    if not name:
        return None

    # Skip if name looks like a generic beach without facilities
    skip_names = {"spiaggia", "beach", "marina", "porto"}
    if name.lower() in skip_names:
        return None

    city = (
        tags.get("addr:city")
        or tags.get("addr:municipality")
        or tags.get("is_in:city")
        or ""
    ).strip()
    province = (
        tags.get("addr:province")
        or tags.get("addr:district")
        or ""
    ).strip()
    region = tags.get("addr:region", "").strip()
    postcode = tags.get("addr:postcode", "").strip()
    street = tags.get("addr:street", "").strip()
    housenumber = tags.get("addr:housenumber", "").strip()

    address_parts = []
    if street:
        address_parts.append(street + (" " + housenumber if housenumber else ""))
    if city:
        address_parts.append(city)
    address = ", ".join(address_parts) if address_parts else ""

    website = (
        tags.get("website")
        or tags.get("contact:website")
        or tags.get("url")
        or ""
    ).strip()

    phone = (
        tags.get("phone")
        or tags.get("contact:phone")
        or tags.get("contact:mobile")
        or ""
    ).strip()

    category_parts = []
    if tags.get("tourism"):
        category_parts.append(tags["tourism"])
    if tags.get("leisure"):
        category_parts.append(tags["leisure"])
    if tags.get("amenity"):
        category_parts.append(tags["amenity"])
    categories = "; ".join(category_parts)

    osm_id = f"{el['type']}/{el['id']}"
    google_maps_url = ""
    if lat and lon:
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

    venue_url = f"https://www.openstreetmap.org/{el['type']}/{el['id']}"

    return {
        "source_platform": "osm",
        "source_venue_id": osm_id,
        "venue_name": name,
        "venue_url": venue_url,
        "address": address,
        "city": city,
        "province": province,
        "region": region,
        "postal_code": postcode,
        "latitude": lat if lat else "",
        "longitude": lon if lon else "",
        "categories": categories,
        "price_tier": "",
        "rating": "",
        "rating_count": "",
        "phone": phone,
        "website": website,
        "opening_hours": tags.get("opening_hours", ""),
        "has_menu": "False",
        "menu_url": "",
        "extraction_status": "ok" if (lat or address) else "no_geo",
        "retrieved_at": RETRIEVED_AT,
        "google_maps_url": google_maps_url,
        "instagram": tags.get("contact:instagram", ""),
        "facebook": tags.get("contact:facebook", ""),
        "booking_provider": "",
        "vertical": "beach",
    }


def main():
    data = fetch_osm()
    elements = data.get("elements", [])
    print(f"Raw OSM elements: {len(elements)}")

    venues = []
    seen_ids = set()

    for el in elements:
        v = build_venue(el)
        if v is None:
            continue
        vid = v["source_venue_id"]
        if vid in seen_ids:
            continue
        seen_ids.add(vid)
        venues.append(v)

    print(f"Valid venues after filter: {len(venues)}")

    # Stats by region
    from collections import Counter
    region_count = Counter(v["region"] or "unknown" for v in venues)
    print("\nTop regions:")
    for reg, cnt in region_count.most_common(15):
        print(f"  {reg}: {cnt}")

    # Write CSV
    with open(VENUES_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VENUES_FIELDS)
        writer.writeheader()
        writer.writerows(venues)

    print(f"\nWritten: {VENUES_FILE} ({len(venues)} rows)")
    return venues


if __name__ == "__main__":
    main()
