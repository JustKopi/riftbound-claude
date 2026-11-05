# Riftbound gyűjtemény – Vendetta

Kereshető Riftbound (Vendetta) gyűjtemény-oldal Cardmarket árakkal, GitHub Pages-en.

- Kártyaadatok és képek: [Riftcodex API](https://riftcodex.com) (ingyenes, kulcs nélkül)
- Árak: a Cardmarket ingyenes napi Price Guide fájlja (Riftbound = `idGame 22`, Vendetta = expansion `6587`)

## Fájlok

- `index.html`: az oldal (lista és képes nézet, kattintásra részletek, RiftBuddy export betöltése)
- `data.js`: generált adat (kártyák, gyűjtemény, árak)
- `collection.json`: a RiftBuddy export, ebből készül a gyűjtemény
- `scripts/build_data.py`: újragenerálja a `data.js`-t
- `.github/workflows/pages.yml`: naponta frissíti az árakat és telepíti az oldalt

## Gyűjtemény frissítése

Cseréld le a `collection.json`-t az új RiftBuddy exportra, aztán:

```bash
python3 scripts/build_data.py collection.json
git commit -am "Gyűjtemény frissítése" && git push
```

Ha csak a `collection.json`-t cseréled, a következő napi futás akkor is újragenerálja az oldalt. Azonnal az Actions fülön a „Run workflow” gombbal indítható.
