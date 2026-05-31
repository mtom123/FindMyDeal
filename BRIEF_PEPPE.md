# Brief per Peppe — Aggiornamento dati 31/05

## Cosa è cambiato

Ho mergiato la seconda sessione di scraping di Pietro. **+109 nuovi prezzi**, ora abbiamo:

| Metrica | Valore |
|---|---|
| **Price points totali** | **738** |
| **Venues uniche sulla mappa** | **126** |
| Venue-product pairs | 487 |
| Prodotti disponibili | **22** |
| Venues totali nel DB | 1.059 |

Il file `prices_data.json` è già aggiornato e pushato. Il sito già si vede aggiornato.

---

## Cosa puoi fare oggi sul sito

### 1. Highlight prodotti "ricchi" (PRIORITÀ ALTA)
I 3 prodotti con copertura migliore sono perfetti per testare l'UX:
- **Spritz**: 80 venues, 114 prezzi → range €3-20
- **Negroni**: 60 venues, 78 prezzi → range €5-15
- **Americano**: 53 venues, 64 prezzi → range €1-15

Per gli altri prodotti i numeri scendono. Se vuoi puoi mettere un badge/contatore tipo "80 locali" accanto al nome del prodotto nella sidebar — già lo fai? Se sì, ottimo.

### 2. Birra Moretti finalmente disponibile! 🍺
Il prodotto sample originale del progetto. **11 venues, 16 prezzi**.
- Min: €3.00 (Sui Generis, Garden Caffè)
- Max: €8.00 (Osteria dal Cornuto - Moretti Rossa)
- Mediana: €4.00

### 3. Nuovi prodotti aggiunti
- **Peroni/Nastro Azzurro** (11 venues)
- **Heineken** (7 venues)
- **Cappuccino** (13 venues)
- **Prosecco Calice** (10 venues)
- **Manhattan** (5 venues)

### 4. Attenzione ai venues "Milano centro"
~40 venues di leggimenu hanno coordinate approssimative (Piazza Duomo) perché non geocodate precisamente. Sulla mappa li vedrai stacked. Se hai un cluster funzionante, già li mostra raggruppati. Quando avremo Nominatim disponibile li sposterò alle posizioni reali.

---

## Suggerimenti UX (se hai tempo)

### Filtro multi-prodotto
Ora se l'utente cerca "drink economici" vuole vedere bibite a basso prezzo. Magari un toggle "Mostra solo prezzi < €X" applicato al prodotto selezionato.

### Mostra range/median nel chip prodotto
Esempio: invece di solo "Spritz (80)", scrivere "Spritz · €3-20 · med €7". Aiuta a capire dove un locale si posiziona.

### Popup migliorato
Quando clicchi un pin, mostra tutti i prodotti di quel locale, non solo quello filtrato. Aiuta a capire il pricing complessivo del bar.

### Sezione "Top deals"
Lista dei 10 prezzi più bassi per il prodotto selezionato. Tipo:
```
SPRITZ più economico a Milano:
1. Bar Picchio — €3.50
2. Garden Caffè — €3.50
3. ...
```

---

## Cosa NON fare ora
- ❌ Non toccare `prices_data.json` a mano — viene rigenerato dal merge pipeline
- ❌ Non geocodare manualmente — lo faccio io centralizzato

## Domande?
Apri issue su GitHub o chiedimi su WhatsApp.

— CEO
