#!/usr/bin/env python3
"""Riftbound (Vendetta) gyűjtemény + Cardmarket árak összefésülése.

Források (mind ingyenes, kulcs nélkül):
  - Riftcodex API: https://api.riftcodex.com  (kártyaadatok, képek)
  - Cardmarket napi árlista (Price Guide) és termékkatalógus, Riftbound = idGame 22:
      https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_22.json
      https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_22.json

Használat:  python3 scripts/build_data.py collection.json
Kimenet:    data.js a repó gyökerében (kártyák + gyűjtemény + Cardmarket árak).
            A GitHub Action naponta lefuttatja, így az árak naponta frissülnek.
"""
import json, re, sys, unicodedata, urllib.request, collections, datetime, os

SET_ID = "VEN"            # Riftcodex set kód
CM_EXPANSION = 6587       # Cardmarket expansion: Vendetta (6588 = Vendetta promók, nem kell)
CM = "https://downloads.s3.cardmarket.com/productCatalog"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "riftbound-collection-viewer"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

def clean_rich(html):
    """A Riftcodex rich szövegből csak a sortörés marad; minden más HTML-tag kiesik.
    Az entitások (&gt; stb.) escape-elt formában maradnak, így biztonságosan beilleszthető."""
    html = re.sub(r"<br\s*/?>|</p>\s*<p>", "\n", html)
    html = re.sub(r"<[^>]+>", "", html).strip()
    return html

def base_name(n):
    return re.sub(r"\s*\((Alternate Art|Overnumbered|Signature)\)$", "", n)

def main(collection_path):
    collection = json.load(open(collection_path))

    # 1) Riftcodex: összes Vendetta kártya
    cards, page = {}, 1
    while True:
        d = get(f"https://api.riftcodex.com/cards?set_id={SET_ID}&size=100&page={page}")
        for c in d["items"]:
            cards.setdefault(c["riftbound_id"], c)
        if page >= d["pages"]:
            break
        page += 1

    # 2) Cardmarket katalógus + árlista
    products = [p for p in get(f"{CM}/productList/products_singles_22.json")["products"]
                if p["idExpansion"] == CM_EXPANSION]
    pg_raw = get(f"{CM}/priceGuide/price_guide_22.json")
    prices = {g["idProduct"]: g for g in pg_raw["priceGuides"]}
    by_name = collections.defaultdict(list)
    for p in products:
        by_name[norm(p["name"])].append(p)
    for v in by_name.values():
        v.sort(key=lambda p: p["idProduct"])

    # Azonos nevű Cardmarket-termékek (alap / alt art / overnumbered) idProduct szerint
    # emelkedő sorrendben jönnek, az alap verzió a legkisebb. A Riftcodex variánsait
    # ugyanígy rendezzük: alap (001) < alt art (001a) < overnumbered (167+).
    def variant_rank(c):
        rid = c["riftbound_id"]; num = rid.split("-")[1]
        if c["metadata"].get("signature"): return 3
        if num.endswith("a"): return 1
        if num.isdigit() and int(num) > 166: return 2
        return 0

    groups = collections.defaultdict(list)
    for c in cards.values():
        groups[norm(base_name(c["name"]))].append(c)

    def find_product(c):
        keys = [norm(base_name(c["name"]))]
        if c.get("tags"):
            keys.append(norm(f'{c["tags"][0]}, {base_name(c["name"])}'))  # legendák: "Renekton, Butcher of the Sands"
        for k in keys:
            cands = by_name.get(k)
            if not cands:
                continue
            sibs = sorted(groups[norm(base_name(c["name"]))], key=variant_rank)
            ranks = [variant_rank(s) for s in sibs]
            idx = sorted(set(ranks)).index(variant_rank(c))
            return cands[min(idx, len(cands) - 1)]
        return None

    def price_of(g, foil):
        if not g: return None
        sfx = "-foil" if foil else ""
        for k in ("trend", "avg30", "avg7", "low"):
            v = g.get(k + sfx)
            if v: return v
        return None

    out = []
    for rid, c in sorted(cards.items(), key=lambda kv: kv[0]):
        p = find_product(c)
        g = prices.get(p["idProduct"]) if p else None
        own = collection.get(rid, {})
        out.append({
            "id": rid,
            "num": rid.split("-")[1],
            "name": c["name"],
            "type": c["classification"]["type"],
            "rarity": c["classification"]["rarity"],
            "domain": c["classification"]["domain"] or [],
            "tags": c.get("tags") or [],
            "text": c["text"]["plain"] or "",
            "rich": clean_rich(c["text"]["rich"] or ""),
            "flavour": c["text"].get("flavour") or "",
            "energy": c["attributes"].get("energy"), "might": c["attributes"].get("might"),
            "power": c["attributes"].get("power"),
            "artist": c["media"].get("artist") or "",
            "img": c["media"]["image_url"],
            "normal": own.get("normal", 0),
            "foil": own.get("foil", 0),
            "cm": None if not p else {
                "id": p["idProduct"], "name": p["name"],
                "trend": price_of(g, False), "trendFoil": price_of(g, True),
                "low": g and g.get("low"), "lowFoil": g and g.get("low-foil"),
                "avg30": g and g.get("avg30"), "avg30Foil": g and g.get("avg30-foil"),
            },
        })

    unmatched = [k for k in collection if k not in cards]
    meta = {"priceGuideDate": pg_raw.get("createdAt"), "set": "Vendetta (VEN)",
            "unknownIds": unmatched, "collectionName": os.path.basename(collection_path)}
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    with open(os.path.join(outdir, "data.js"), "w") as f:
        f.write("window.META=" + json.dumps(meta) + ";\nwindow.CARDS=" + json.dumps(out, ensure_ascii=False) + ";\n")
    owned = [x for x in out if x["normal"] or x["foil"]]
    print(f"{len(out)} kártya, ebből a gyűjteményben {len(owned)}; Cardmarket-egyezés nélkül:",
          [x["id"] for x in owned if not x["cm"]], "ismeretlen ID-k:", unmatched)

if __name__ == "__main__":
    main(sys.argv[1])
