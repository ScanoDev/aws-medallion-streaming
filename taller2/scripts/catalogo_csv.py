import argparse, csv, glob, json, os

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogo", default="medallion/scraping/eafit_urls.json")
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--salida", default="data/catalogo/catalogo_paginas.csv")
    a = ap.parse_args()

    titulos_raw = {}
    for ruta in glob.glob(os.path.join(a.raw, "*.json")):
        with open(ruta, encoding="utf-8") as fj:
            d = json.load(fj)
        meta = ((d.get("respuesta") or {}).get("data") or {}).get("metadata") or {}
        titulo = meta.get("title")
        if isinstance(titulo, list):
            titulo = titulo[0] if titulo else None
        titulos_raw[d.get("url_pedida")] = " ".join(str(titulo).split()) if titulo else ""

    with open(a.catalogo, encoding="utf-8") as fc:
        catalogo = json.load(fc)

    os.makedirs(os.path.dirname(a.salida) or ".", exist_ok=True)
    filas = con_titulo = descargadas = 0
    with open(a.salida, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["url", "titulo", "descargada"])
        for item in catalogo:
            url = item["url"]
            descargada = url in titulos_raw
            titulo = titulos_raw.get(url) or " ".join((item.get("title") or "").split())
            w.writerow([url, titulo, "true" if descargada else "false"])
            filas += 1
            con_titulo += bool(titulo)
            descargadas += descargada

    print(f"Filas: {filas} | Descargadas: {descargadas} | Con título: {con_titulo} | Archivo: {a.salida}")

if __name__ == "__main__":
    main()