# PROMPT PEPPE — Frontend Barbieri S1 + Piano Gym
**CEO, 2026-06-02**

---

Peppe, ottimo lavoro su barber S1 (12k venue, 89% prezzate — record assoluto).

## Task IMMEDIATO: Frontend Barbieri

Il brief completo è in `barber_s1_REPORT_PEPPE.md` (leggilo tutto — 415 righe).
Qui ti do le istruzioni operative per partire subito.

---

## Step 1: Setup (fai subito)

```bash
git pull
git checkout -b feat/barber-frontend
```

Dati: `data/barber_data.json` — 16MB, già nel repo.
Per non caricare 16MB in una pagina: gzippa prima del deploy.
```bash
gzip -k data/barber_data.json  # → crea barber_data.json.gz (~3MB)
```

---

## Step 2: Struttura file

Crea `barber.html` nella root (o `website/barber.html` se il sito è in `/website`).
Non toccare `index.html` (drink) né i file beach.

---

## Step 3: Marker esagonali (questo è il pezzo nuovo rispetto a beach)

```javascript
// Hexagonal marker con Leaflet DivIcon
function createHexMarker(price, tier) {
  const colors = { green: '#2ecc71', amber: '#f39c12', red: '#e74c3c', grey: '#888' };
  const color = colors[tier] || colors.grey;
  
  const svg = `<svg width="32" height="36" viewBox="0 0 32 36" xmlns="http://www.w3.org/2000/svg">
    <polygon points="16,2 30,10 30,26 16,34 2,26 2,10" 
             fill="${color}" stroke="#3d2b8a" stroke-width="2"/>
    <text x="16" y="21" text-anchor="middle" fill="white" 
          font-size="9" font-weight="bold">${price}</text>
  </svg>`;
  
  return L.divIcon({
    html: svg,
    className: 'barber-marker',
    iconSize: [32, 36],
    iconAnchor: [16, 18],
    popupAnchor: [0, -18]
  });
}

// Calcola tier vs mediana regionale
function getPriceTier(price, regionalMedian) {
  const ratio = price / regionalMedian;
  if (ratio <= 0.85) return 'green';
  if (ratio <= 1.15) return 'amber';
  return 'red';
}
```

---

## Step 4: Filtri a 2 livelli (cascaded)

```javascript
// Struttura categorie per genere
const SERVICE_TREE = {
  uomo: ['haircut_man', 'beard_trim', 'beard_design', 'treatment_man'],
  donna: ['haircut_woman', 'color', 'highlights', 'blowdry', 'treatment_woman'],
  bambino: ['haircut_child']
};

// Labels italiane
const SERVICE_LABELS = {
  haircut_man: 'Taglio', beard_trim: 'Barba (trim)', beard_design: 'Barba (design)',
  treatment_man: 'Trattamento', haircut_woman: 'Taglio', color: 'Colore',
  highlights: 'Meches', blowdry: 'Piega', treatment_woman: 'Trattamento',
  haircut_child: 'Taglio bambino'
};

// Stato filtri
let activeGender = null;   // 'uomo' | 'donna' | 'bambino'
let activeService = null;  // es. 'haircut_man'

function onGenderChange(gender) {
  activeGender = gender;
  activeService = null;
  updateServiceDropdown();
  updateMap();  // grigio se service null
}

function onServiceChange(service) {
  activeService = service;
  updateMap();  // colora in base a prezzo vs mediana
}
```

---

## Step 5: Logica mappa aggiornamento

```javascript
function updateMap() {
  markerLayer.clearLayers();
  
  venues.forEach(venue => {
    if (!activeGender || !activeService) {
      // Nessun filtro: marker grigio
      const m = L.marker([venue.lat, venue.lon], { icon: createHexMarker('?', 'grey') });
      markerLayer.addLayer(m);
      return;
    }
    
    // Trova prezzo per il servizio selezionato
    const serviceData = venue.services_normalized?.find(s => s.code === activeService);
    if (!serviceData) return;  // venue non offre questo servizio
    
    const price = serviceData.price_median_eur;
    const region = venue.region;
    const regionalMedian = barberData.region_stats[region]?.median_by_service?.[activeService];
    
    if (!regionalMedian) return;
    
    const tier = getPriceTier(price, regionalMedian);
    const label = price >= 100 ? `€${(price/100).toFixed(1)}k` : `€${Math.round(price)}`;
    
    const marker = L.marker([venue.lat, venue.lon], { 
      icon: createHexMarker(label, tier) 
    });
    
    marker.bindPopup(buildPopup(venue, serviceData, regionalMedian));
    markerLayer.addLayer(marker);
  });
}
```

---

## Step 6: Sidebar (copia da beach, sostituisci le parti)

La sidebar beach ha:
- Filtri slider prezzo → sostituisci con gender chips + service dropdown
- Layer toggles → tieni uguale
- Statistiche regionali → adatta per mostrare mediana del servizio selezionato

Non reinventare la struttura CSS, riusa tutto quello che puoi da `index.html` / beach.

---

## REGOLE CRITICHE

1. **Mai mostrare prezzi misti** — se filtro è "taglio uomo", mostra SOLO prezzi taglio uomo. Zero eccezioni.
2. **Mediana REGIONALE** — non nazionale. I dati regionali sono in `barber_data.json → region_stats`.
3. **Bambino = genere separato** — non sotto-categoria donna.
4. **Nessun filtro attivo** → marker grigi + tooltip "Seleziona genere e servizio".
5. **Non editare** `data/barber_data.json` — è generato da script, qualsiasi modifica manuale viene sovrascritta.

---

## Deliverable e timeline

| Deliverable | Quando |
|------------|--------|
| PR con mappa base funzionante (marker visibili, colori, popup) | Prima possibile |
| PR con filtri funzionanti (gender + service) | Dopo feedback CEO sulla mappa base |
| PR con sidebar completa | Finale |

**Fai una PR per step** — non aspettare di avere tutto finito.

---

## Cosa fare DOPO barbieri (non adesso)

Quando barbieri frontend è live, il prossimo task sarà gym frontend.
Ma aspetta il via libera CEO — prima dobbiamo raccogliere i prezzi.
Per ora: solo barbieri.

---

Qualsiasi dubbio tecnico → apri issue su GitHub con label `peppe-question`.

— CEO
