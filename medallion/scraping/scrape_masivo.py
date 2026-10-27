import os, sys, json, time, hashlib, glob, random, argparse
from datetime import datetime, timezone
import requests

ENDPOINT = "https://api.firecrawl.dev/v2/scrape"
SEMILLA = 42  # misma semilla para todos: garantiza el mismo orden y tramos sin solaparse
ERRORES_SERVIDOR = (500, 502, 503, 504)


def nombre_archivo(url):
    return hashlib.md5(url.encode()).hexdigest() + ".json"


def esta_ok(d):
    md = ((d.get("respuesta") or {}).get("data") or {}).get("markdown")
    return d.get("http_status") == 200 and bool(md)


def hechas_en_disco(out_dir):
    hechas = set()
    for ruta in glob.glob(os.path.join(out_dir, "*.json")):
        try:
            d = json.load(open(ruta, encoding="utf-8"))
        except Exception:
            continue
        if esta_ok(d) and d.get("url_pedida"):
            hechas.add(d["url_pedida"])
    return hechas


def pedir(url, api_key):
    return requests.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
        timeout=90,
    )


def a_json(r):
    """Devuelve el cuerpo como dict; si no es JSON válido, devuelve None."""
    try:
        return r.json()
    except ValueError:
        return None


def anotar_error(url, detalle):
    with open("errores.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {url} | {detalle}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", default="eafit_urls.json")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--manifiesto", default="ya_hechas.txt")
    ap.add_argument("--parte", type=int, default=1)
    ap.add_argument("--partes", type=int, default=1)
    ap.add_argument("--max-paginas", type=int, default=985,
                    help="tope de páginas a descargar en esta corrida (menos que tus créditos)")
    ap.add_argument("--pausa", type=float, default=6.0)
    ap.add_argument("--generar-manifiesto", action="store_true",
                    help="escribe ya_hechas.txt a partir de la carpeta de salida y termina")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)

    if a.generar_manifiesto:
        hechas = sorted(hechas_en_disco(a.out))
        with open(a.manifiesto, "w", encoding="utf-8") as f:
            f.write("\n".join(hechas) + "\n")
        print(f"{len(hechas)} URL escritas en {a.manifiesto}")
        return

    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        sys.exit("Falta la variable de entorno FIRECRAWL_API_KEY")
    if not (1 <= a.parte <= a.partes):
        sys.exit("--parte debe estar entre 1 y --partes")

    urls = sorted({x["url"] for x in json.load(open(a.urls, encoding="utf-8"))})
    random.Random(SEMILLA).shuffle(urls)

    hechas = hechas_en_disco(a.out)
    if os.path.exists(a.manifiesto):
        hechas |= {l.strip() for l in open(a.manifiesto, encoding="utf-8") if l.strip()}

    pendientes = [u for u in urls if u not in hechas]
    mi_lote = pendientes[a.parte - 1::a.partes]
    print(f"Total URL: {len(urls)} | ya hechas: {len(hechas)} | pendientes: {len(pendientes)}")
    print(f"Mi lote (parte {a.parte} de {a.partes}): {len(mi_lote)} | tope esta corrida: {a.max_paginas}")

    descargadas = 0
    sin_credito = False
    for i, url in enumerate(mi_lote, 1):
        if descargadas >= a.max_paginas:
            print("Tope de páginas alcanzado. Me detengo.")
            break

        r = None
        for intento in range(4):
            try:
                r = pedir(url, api_key)
            except requests.RequestException as e:
                print(f"[{i}] error de red (intento {intento + 1}): {e}")
                r = None
                time.sleep(10)
                continue
            if r.status_code == 429:
                espera = int(r.headers.get("Retry-After", 30))
                print(f"[{i}] 429 límite de velocidad, espero {espera}s")
                time.sleep(espera)
                continue
            if r.status_code in ERRORES_SERVIDOR:
                espera = 15 * (intento + 1)
                print(f"[{i}] HTTP {r.status_code} del servidor, espero {espera}s y reintento")
                time.sleep(espera)
                continue
            break

        if r is None:
            anotar_error(url, "sin respuesta (error de red)")
            print(f"[{i}] no pude descargar {url}; sigo con la siguiente")
            continue
        if r.status_code == 402:
            print("HTTP 402: sin créditos. Me detengo.")
            sin_credito = True
            break

        cuerpo = a_json(r)
        if cuerpo is None:
            detalle = f"HTTP {r.status_code}, respuesta no JSON: {r.text[:200]!r}"
            anotar_error(url, detalle)
            print(f"[{i}] {detalle}")
            time.sleep(a.pausa)
            continue

        registro = {
            "url_pedida": url,
            "fecha_extraccion": datetime.now(timezone.utc).isoformat(),
            "http_status": r.status_code,
            "respuesta": cuerpo,
        }

        if esta_ok(registro):
            with open(os.path.join(a.out, nombre_archivo(url)), "w", encoding="utf-8") as f:
                json.dump(registro, f, ensure_ascii=False)
            descargadas += 1
            n = len(cuerpo["data"]["markdown"])
            print(f"[{i}/{len(mi_lote)}] ok ({descargadas}) {n} car. | {url}")
        else:
            detalle = f"HTTP {r.status_code}, sin markdown: {str(cuerpo)[:200]!r}"
            anotar_error(url, detalle)
            print(f"[{i}/{len(mi_lote)}] fallo | {detalle}")
        time.sleep(a.pausa)

    hechas_ahora = hechas_en_disco(a.out) | hechas
    sin_hacer = [u for u in mi_lote if u not in hechas_ahora]
    ruta_p = f"pendientes_parte{a.parte}.txt"
    with open(ruta_p, "w", encoding="utf-8") as f:
        f.write("\n".join(sin_hacer) + "\n")
    print(f"Listo. Descargadas ahora: {descargadas} | sin hacer de mi lote: {len(sin_hacer)} (en {ruta_p})")
    if sin_credito:
        print("Nota: me detuve por falta de créditos.")


if __name__ == "__main__":
    main()