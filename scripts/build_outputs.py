"""
build_outputs.py
================
Reads mycia_milano_menu_items.csv + mycia_milano_venues.csv and produces:

  1. prices_by_product.csv   — product-centric, sorted normalized_product > price asc
  2. demo_map.html            — Leaflet interactive map with product filter

Run:
    python build_outputs.py
"""

import csv
import json
import re
from pathlib import Path
from collections import defaultdict

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

ITEMS_CSV  = Path("mycia_milano_menu_items.csv")
VENUES_CSV = Path("mycia_milano_venues.csv")
OUT_PRODUCT_CSV = Path("prices_by_product.csv")
OUT_MAP_HTML    = Path("demo_map.html")

# Human-readable labels for normalized product codes
PRODUCT_LABELS = {
    "spritz":           "Spritz",
    "negroni":          "Negroni",
    "americano":        "Americano",
    "gin_tonic":        "Gin Tonic",
    "moscow_mule":      "Moscow Mule",
    "margarita":        "Margarita",
    "mojito":           "Mojito",
    "manhattan":        "Manhattan",
    "daiquiri":         "Daiquiri",
    "beer_draft_small": "Birra Spina Piccola",
    "beer_draft_medium":"Birra Spina Media",
    "beer_draft":       "Birra alla Spina",
    "beer_bottle":      "Birra in Bottiglia",
    "wine_glass":       "Vino al Calice",
    "soft_drink":       "Bibita",
    "water":            "Acqua",
    "espresso":         "Caffè",
    "custom_cocktail":  "Cocktail Custom",
    "custom_beer":      "Birra Artigianale",
}

# Section-level fallback normalization
SECTION_TO_PRODUCT = [
    (r"birra.*(spina|tap)",       "beer_draft"),
    (r"birra.*bottiglia",         "beer_bottle"),
    (r"birre",                    "beer_draft"),
    (r"cocktail",                 "custom_cocktail"),
    (r"cocteles",                 "custom_cocktail"),
    (r"vini|calici",              "wine_glass"),
    (r"gin\b",                    "gin_tonic"),
    (r"rum\b",                    "custom_cocktail"),
    (r"whisky|whiskey",           "custom_cocktail"),
    (r"long drink",               "custom_cocktail"),
    (r"mocktail",                 "custom_cocktail"),
    (r"aperitivi|aperitivo",      "custom_cocktail"),
]

# Sections that are actually food (to exclude)
FOOD_SECTION_RE = re.compile(
    r"\b(pizza|tacos?|burger|panino|piatti?|antipasti?|primi|secondi|"
    r"dolci|dessert|insalat|pasta|risotto|entradas?|contorni|grill)\b",
    re.I,
)

PRICE_ORDER = [
    "spritz", "negroni", "americano", "gin_tonic", "mojito",
    "moscow_mule", "margarita", "manhattan", "daiquiri",
    "custom_cocktail",
    "beer_draft_small", "beer_draft_medium", "beer_draft",
    "beer_bottle", "custom_beer",
    "wine_glass",
    "espresso", "soft_drink", "water",
]


def section_normalize(section: str) -> str | None:
    sl = section.lower()
    for pattern, product in SECTION_TO_PRODUCT:
        if re.search(pattern, sl):
            return product
    return None


def is_food_section(section: str) -> bool:
    return bool(FOOD_SECTION_RE.search(section))


def product_sort_key(product: str) -> int:
    try:
        return PRICE_ORDER.index(product)
    except ValueError:
        return len(PRICE_ORDER)


# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────

venues = {}
for row in csv.DictReader(open(VENUES_CSV, encoding="utf-8")):
    venues[row["venue_id"]] = row

raw_items = list(csv.DictReader(open(ITEMS_CSV, encoding="utf-8")))

# ─────────────────────────────────────────────
# ENRICH ITEMS
# ─────────────────────────────────────────────

enriched = []
for item in raw_items:
    # Skip items without price
    try:
        price = float(item["normalized_price_eur"])
        if price <= 0:
            continue
    except (ValueError, TypeError):
        continue

    # Skip food items
    if is_food_section(item["menu_section"]):
        continue
    if item["item_type"] == "non_drink" and not item["normalized_product"]:
        continue

    # Resolve normalized_product
    prod = item["normalized_product"]
    if not prod:
        # Try section-level fallback
        prod = section_normalize(item["menu_section"])
    if not prod:
        # If item is flagged as drink → generic custom_cocktail
        if item["item_type"] == "drink":
            prod = "custom_cocktail"
        else:
            continue  # skip non-drink without category

    venue = venues.get(item["venue_id"], {})
    lat  = venue.get("latitude", "")
    lng  = venue.get("longitude", "")

    # Skip if no geo
    if not lat or not lng:
        continue

    # Sanity check price range
    if price < 0.80 or price > 60:
        continue

    enriched.append({
        "normalized_product":   prod,
        "product_label":        PRODUCT_LABELS.get(prod, prod.replace("_", " ").title()),
        "item_name":            item["item_name"],
        "menu_section":         item["menu_section"],
        "price_eur":            price,
        "venue_id":             item["venue_id"],
        "venue_name":           item["venue_name"],
        "address":              venue.get("address", ""),
        "city":                 "Milano",
        "latitude":             lat,
        "longitude":            lng,
        "price_tier":           venue.get("price_tier", ""),
        "categories":           venue.get("categories", ""),
        "opening_hours":        venue.get("opening_hours", ""),
        "source_url":           item["source_url"],
        "retrieved_at":         item["retrieved_at"],
    })

print(f"Items arricchiti: {len(enriched)}")

# ─────────────────────────────────────────────
# SORT: by product order, then price asc
# ─────────────────────────────────────────────

enriched.sort(key=lambda x: (product_sort_key(x["normalized_product"]), x["price_eur"]))

# ─────────────────────────────────────────────
# 1. prices_by_product.csv
# ─────────────────────────────────────────────

FIELDS = [
    "normalized_product", "product_label",
    "item_name", "menu_section",
    "price_eur",
    "venue_name", "address", "city",
    "latitude", "longitude",
    "price_tier", "categories", "opening_hours",
    "source_url", "retrieved_at",
]

with open(OUT_PRODUCT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(enriched)

# Stats
from collections import Counter
prod_count = Counter(r["normalized_product"] for r in enriched)
print(f"\nProdotti in prices_by_product.csv:")
for prod, n in sorted(prod_count.items(), key=lambda x: (-x[1], x[0])):
    prices = [r["price_eur"] for r in enriched if r["normalized_product"] == prod]
    prices.sort()
    label = PRODUCT_LABELS.get(prod, prod)
    print(f"  {label:25s} {n:3d} prezzi | EUR {min(prices):.2f}–{max(prices):.2f} | median {prices[len(prices)//2]:.2f}")

print(f"\n-> {OUT_PRODUCT_CSV} scritto ({len(enriched)} righe)")

# ─────────────────────────────────────────────
# 2. Build venue → products map for Leaflet
# ─────────────────────────────────────────────

venue_map: dict[str, dict] = {}
for row in enriched:
    vid = row["venue_id"]
    if vid not in venue_map:
        venue_map[vid] = {
            "id":       vid,
            "name":     row["venue_name"],
            "address":  row["address"],
            "lat":      float(row["latitude"]),
            "lng":      float(row["longitude"]),
            "tier":     row["price_tier"],
            "cats":     row["categories"],
            "products": {},   # prod_code -> list of {item, price}
        }
    prod = row["normalized_product"]
    label = row["product_label"]
    if prod not in venue_map[vid]["products"]:
        venue_map[vid]["products"][prod] = {"label": label, "items": []}
    venue_map[vid]["products"][prod]["items"].append({
        "name":  row["item_name"],
        "price": row["price_eur"],
    })

# Compute min price per product per venue
for v in venue_map.values():
    for prod_data in v["products"].values():
        prod_data["min_price"] = min(i["price"] for i in prod_data["items"])

all_products_ordered = sorted(
    {r["normalized_product"] for r in enriched},
    key=product_sort_key
)

venues_json = json.dumps(list(venue_map.values()), ensure_ascii=False, indent=2)
products_json = json.dumps(
    [{"code": p, "label": PRODUCT_LABELS.get(p, p.replace("_"," ").title())}
     for p in all_products_ordered],
    ensure_ascii=False
)

print(f"\nVenues sulla mappa: {len(venue_map)}"  )

# ─────────────────────────────────────────────
# 3. demo_map.html
# ─────────────────────────────────────────────

HTML = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>FoodPrice Demo — Milano Drink Prices</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; display: flex; height: 100vh; overflow: hidden; background: #1a1a2e; }}

    /* ── Sidebar ── */
    #sidebar {{
      width: 280px; min-width: 240px;
      background: #16213e;
      color: #e8e8f0;
      display: flex; flex-direction: column;
      border-right: 1px solid #0f3460;
      z-index: 999;
    }}
    #sidebar h1 {{
      font-size: 1.1rem; font-weight: 700;
      padding: 18px 16px 4px;
      color: #e94560;
      letter-spacing: .5px;
    }}
    #sidebar .subtitle {{
      font-size: .72rem; color: #9090b0; padding: 0 16px 14px;
    }}

    /* Product filter list */
    #filter-title {{
      font-size: .65rem; font-weight: 600; letter-spacing: 1px;
      text-transform: uppercase; color: #5555aa;
      padding: 10px 16px 6px;
    }}
    #product-list {{
      overflow-y: auto; flex: 1; padding: 0 10px 10px;
    }}
    .prod-btn {{
      display: flex; align-items: center; justify-content: space-between;
      width: 100%; padding: 8px 10px; margin-bottom: 4px;
      border-radius: 8px; border: 1.5px solid transparent;
      background: #1e2a4a; color: #c8c8e8;
      cursor: pointer; font-size: .82rem;
      transition: all .15s;
      text-align: left;
    }}
    .prod-btn:hover {{ background: #263555; color: #fff; }}
    .prod-btn.active {{ background: #e94560; color: #fff; border-color: #ff6b88; }}
    .prod-btn .count {{
      font-size: .7rem; background: rgba(255,255,255,.12);
      padding: 1px 7px; border-radius: 10px; white-space: nowrap;
    }}
    .prod-btn.active .count {{ background: rgba(255,255,255,.25); }}

    /* Stats box */
    #stats {{
      padding: 12px 16px;
      background: #0f1e3a;
      border-top: 1px solid #0f3460;
      font-size: .78rem; color: #9090b0;
    }}
    #stats strong {{ color: #e8e8f0; }}

    /* ── Map ── */
    #map {{ flex: 1; }}

    /* ── Popup ── */
    .leaflet-popup-content-wrapper {{
      background: #16213e; color: #e8e8f0;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,.5);
      border: 1px solid #0f3460;
    }}
    .leaflet-popup-tip {{ background: #16213e; }}
    .popup-name {{ font-weight: 700; font-size: 1rem; margin-bottom: 2px; }}
    .popup-addr {{ font-size: .72rem; color: #7878a8; margin-bottom: 10px; }}
    .popup-products {{ font-size: .8rem; }}
    .popup-product-row {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 5px 0; border-bottom: 1px solid #1e2a4a;
    }}
    .popup-product-row:last-child {{ border-bottom: none; }}
    .popup-prod-label {{ color: #b8b8d8; }}
    .popup-prod-label .item-name {{ font-size: .7rem; color: #6868a0; }}
    .popup-price {{
      font-weight: 700; font-size: .95rem;
      color: #e94560; white-space: nowrap; margin-left: 12px;
    }}
    .popup-tier {{ font-size: .7rem; color: #5555aa; margin-top: 6px; }}
    .highlighted-product {{ background: rgba(233,69,96,.08); border-radius: 4px; }}

    /* ── Custom markers ── */
    .price-marker {{
      background: #e94560; color: white;
      border-radius: 20px; padding: 3px 8px;
      font-weight: 700; font-size: .78rem;
      white-space: nowrap;
      border: 2px solid white;
      box-shadow: 0 2px 8px rgba(0,0,0,.4);
    }}
    .price-marker.cheap  {{ background: #27ae60; }}
    .price-marker.mid    {{ background: #e67e22; }}
    .price-marker.pricey {{ background: #e94560; }}
  </style>
</head>
<body>

<div id="sidebar">
  <h1>🍹 FoodPrice Demo</h1>
  <p class="subtitle">Milano · prezzi drinks · fonte: MyCIA</p>
  <p id="filter-title">Filtra per prodotto</p>
  <div id="product-list"></div>
  <div id="stats">
    <div id="stat-venues">Seleziona un prodotto</div>
    <div id="stat-price" style="margin-top:4px"></div>
  </div>
</div>

<div id="map"></div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script>
// ── Data ──────────────────────────────────────────
const VENUES   = {venues_json};
const PRODUCTS = {products_json};

// ── Map init ──────────────────────────────────────
const map = L.map('map', {{
  center: [45.4654, 9.1859],
  zoom: 13,
  zoomControl: true,
}});

L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
  maxZoom: 19,
}}).addTo(map);

// ── State ─────────────────────────────────────────
let selectedProduct = null;
let markerCluster   = null;

// ── Build sidebar buttons ─────────────────────────
const listEl = document.getElementById('product-list');

PRODUCTS.forEach(p => {{
  const count = VENUES.filter(v => v.products[p.code]).length;
  if (count === 0) return;

  const btn = document.createElement('button');
  btn.className  = 'prod-btn';
  btn.dataset.code = p.code;
  btn.innerHTML  = `<span>${{p.label}}</span><span class="count">${{count}}</span>`;
  btn.addEventListener('click', () => selectProduct(p.code));
  listEl.appendChild(btn);
}});

// ── Select product ────────────────────────────────
function selectProduct(code) {{
  selectedProduct = code;

  // Update button states
  document.querySelectorAll('.prod-btn').forEach(b => {{
    b.classList.toggle('active', b.dataset.code === code);
  }});

  renderMarkers();
}}

// ── Price color ───────────────────────────────────
function priceClass(price, min, max) {{
  const mid = (min + max) / 2;
  if (price <= min + (mid - min) * 0.5) return 'cheap';
  if (price >= max - (max - mid) * 0.5) return 'pricey';
  return 'mid';
}}

// ── Render markers ───────────────────────────────
function renderMarkers() {{
  if (markerCluster) map.removeLayer(markerCluster);
  markerCluster = L.markerClusterGroup({{
    maxClusterRadius: 40,
    iconCreateFunction: function(cluster) {{
      const n = cluster.getChildCount();
      return L.divIcon({{
        html: `<div style="background:#e94560;color:white;border-radius:50%;
                width:36px;height:36px;display:flex;align-items:center;
                justify-content:center;font-weight:700;font-size:.85rem;
                border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,.5)">${{n}}</div>`,
        className: '',
        iconSize: [36, 36],
        iconAnchor: [18, 18],
      }});
    }}
  }});

  const code = selectedProduct;
  const venues_with = VENUES.filter(v => v.products[code]);

  if (venues_with.length === 0) {{
    updateStats(0, [], code);
    return;
  }}

  const prices = venues_with.flatMap(v =>
    v.products[code].items.map(i => i.price)
  ).sort((a,b) => a-b);

  const minP = prices[0];
  const maxP = prices[prices.length - 1];

  venues_with.forEach(venue => {{
    const prodData = venue.products[code];
    const minPrice = prodData.min_price;
    const cls = priceClass(minPrice, minP, maxP);

    const icon = L.divIcon({{
      html: `<div class="price-marker ${{cls}}">€${{minPrice.toFixed(2)}}</div>`,
      className: '',
      iconSize: null,
      iconAnchor: [20, 12],
    }});

    const marker = L.marker([venue.lat, venue.lng], {{icon}});

    // Build popup
    let prodRows = '';
    Object.entries(venue.products).forEach(([pcode, pdata]) => {{
      const isHighlighted = pcode === code;
      const itemsList = pdata.items
        .sort((a,b) => a.price - b.price)
        .map(i => `<div class="popup-product-row ${{isHighlighted ? 'highlighted-product' : ''}}">
          <div class="popup-prod-label">
            <div>${{pdata.label}}</div>
            <div class="item-name">${{i.name}}</div>
          </div>
          <div class="popup-price">€${{i.price.toFixed(2)}}</div>
        </div>`)
        .join('');
      prodRows += itemsList;
    }});

    const tierStr = venue.tier ? ` · ${{venue.tier}}` : '';
    const popup = `
      <div style="min-width:220px;max-width:300px">
        <div class="popup-name">${{venue.name}}</div>
        <div class="popup-addr">${{venue.address}}${{tierStr}}</div>
        <div class="popup-products">${{prodRows}}</div>
      </div>`;

    marker.bindPopup(popup, {{maxWidth: 320}});
    markerCluster.addLayer(marker);
  }});

  map.addLayer(markerCluster);
  updateStats(venues_with.length, prices, code);
}}

// ── Stats bar ─────────────────────────────────────
function updateStats(count, prices, code) {{
  const label = PRODUCTS.find(p => p.code === code)?.label || code;
  document.getElementById('stat-venues').innerHTML =
    `<strong>${{label}}</strong> · <strong>${{count}}</strong> locali`;
  if (prices.length > 0) {{
    const med = prices[Math.floor(prices.length/2)];
    document.getElementById('stat-price').innerHTML =
      `Range <strong>€${{prices[0].toFixed(2)}}–€${{prices[prices.length-1].toFixed(2)}}</strong>`+
      ` · median <strong>€${{med.toFixed(2)}}</strong>`;
  }} else {{
    document.getElementById('stat-price').innerHTML = '';
  }}
}}

// ── Init: select first product ────────────────────
if (PRODUCTS.length > 0) {{
  const firstWithData = PRODUCTS.find(p => VENUES.some(v => v.products[p.code]));
  if (firstWithData) selectProduct(firstWithData.code);
}}
</script>
</body>
</html>
"""

OUT_MAP_HTML.write_text(HTML, encoding="utf-8")
print(f"-> {OUT_MAP_HTML} scritto ({len(venue_map)} venues, {len(all_products_ordered)} prodotti)")
