import argparse, glob, gzip, json, os

def abrir(carpeta, n, comprimir):
    ext = "jsonl.gz" if comprimir else "jsonl"
    ruta = os.path.join(carpeta, f"tokens_{n:03d}.{ext}")
    if comprimir:
        return ruta, gzip.open(ruta, "wt", encoding="utf-8", newline="\n")
    return ruta, open(ruta, "w", encoding="utf-8", newline="\n")

def texto_o_nulo(valor):
    if valor is None or valor == "":
        return None
    return str(valor)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", default="data/raw")
    ap.add_argument("--salida", default="data/bronce/tokens_jsonl")
    ap.add_argument("--filas-por-archivo", type=int, default=500000)
    ap.add_argument("--gzip", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.salida, exist_ok=True)
    for viejo in glob.glob(os.path.join(a.salida, "tokens_*.jsonl*")):
        os.remove(viejo)

    archivos = sorted(glob.glob(os.path.join(a.entrada, "*.json")))
    paginas = filas = filas_archivo = 0
    n = 1
    rutas = []
    ruta, f = abrir(a.salida, n, a.gzip)
    rutas.append(ruta)

    for ruta_json in archivos:
        if filas_archivo >= a.filas_por_archivo:
            f.close()
            n += 1
            ruta, f = abrir(a.salida, n, a.gzip)
            rutas.append(ruta)
            filas_archivo = 0
        with open(ruta_json, encoding="utf-8") as fj:
            d = json.load(fj)
        data = (d.get("respuesta") or {}).get("data") or {}
        meta = data.get("metadata") or {}
        md = data.get("markdown") or ""
        fijos = {
            "pagina_id": os.path.splitext(os.path.basename(ruta_json))[0],
            "url": d.get("url_pedida"),
            "idioma": texto_o_nulo(meta.get("language")),
            "status_pagina": texto_o_nulo(meta.get("statusCode")),
            "fecha_extraccion": texto_o_nulo(d.get("fecha_extraccion")),
        }
        for pos, token in enumerate(md.split(), start=1):
            fila = dict(fijos, posicion=pos, token=token)
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
            filas += 1
            filas_archivo += 1
        paginas += 1
    f.close()

    mb = sum(os.path.getsize(r) for r in rutas) / 1024 / 1024
    print(f"Páginas: {paginas} | Filas (tokens): {filas:,} | Archivos: {len(rutas)} | Tamaño: {mb:.1f} MB")

if __name__ == "__main__":
    main()