"""Convierte los JSON de Firecrawl (data/raw) en el archivo de bronce: una fila por token.

Bronce = crudo: el token se guarda tal cual aparece en el markdown (separado por
espacios), sin limpiar. La limpieza se hace en plata, con SQL en Athena.

Formato: TSV (separado por tabulaciones), sin comillas. Como los tokens salen de
partir el texto por espacios, nunca contienen tabulaciones ni saltos de línea,
así que el archivo se puede leer en Athena sin escapar nada.

Uso (desde la raíz del repo):
    python medallion/scripts/bronce.py
"""
import argparse, glob, json, os

COLUMNAS = ["pagina_id", "url", "idioma", "status_pagina",
            "fecha_extraccion", "posicion", "token"]


def limpio(valor):
    """Convierte a texto y garantiza que no rompa el formato TSV."""
    texto = str(valor)
    if "\t" in texto or "\n" in texto or "\r" in texto:
        raise ValueError(f"Valor con tabulación o salto de línea: {texto!r}")
    return texto


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", default="data/raw")
    ap.add_argument("--salida", default="data/bronce/bronce_tokens.tsv")
    a = ap.parse_args()

    archivos = sorted(glob.glob(os.path.join(a.entrada, "*.json")))
    paginas = filas = 0
    os.makedirs(os.path.dirname(a.salida) or ".", exist_ok=True)

    with open(a.salida, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(COLUMNAS) + "\n")
        for ruta in archivos:
            with open(ruta, encoding="utf-8") as fj:
                d = json.load(fj)
            data = (d.get("respuesta") or {}).get("data") or {}
            meta = data.get("metadata") or {}
            md = data.get("markdown") or ""

            pagina_id = os.path.splitext(os.path.basename(ruta))[0]
            fijos = [limpio(v) for v in (
                pagina_id,
                d.get("url_pedida", ""),
                meta.get("language", ""),
                meta.get("statusCode", ""),
                d.get("fecha_extraccion", ""),
            )]
            for pos, token in enumerate(md.split(), start=1):
                f.write("\t".join(fijos + [str(pos), limpio(token)]) + "\n")
                filas += 1
            paginas += 1

    mb = os.path.getsize(a.salida) / 1024 / 1024
    print(f"Páginas: {paginas} | Filas (tokens): {filas:,} | Tamaño: {mb:.1f} MB")


if __name__ == "__main__":
    main()