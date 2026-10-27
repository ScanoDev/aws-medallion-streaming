"""Descarga páginas de eafit.edu.co con Firecrawl, repartidas en lotes fijos.

Cada integrante corre su parte (--parte K --partes N) con su propia clave, al
mismo tiempo que los demás. Los lotes se calculan solo con el manifiesto
(ya_hechas.txt), que es igual para todos: no cambian al reanudar ni al traer
datos de otros, así que nunca se cruzan.

Ningún tiempo de espera pasa de 15 segundos:
  * Firecrawl corta cada página a los 13 s y el script deja de esperar a los 15 s
    (por defecto Firecrawl espera hasta 60 s: de ahí venía el minuto perdido).
  * Una página que falla no se reintenta en el momento: pasa a una segunda
    vuelta al final del lote.
  * Si Firecrawl pide bajar el ritmo (HTTP 429), se espera como máximo 15 s.

Uso (desde la raíz del repo):
    python medallion/scraping/scrape_masivo.py --urls medallion/scraping/eafit_urls.json
        --manifiesto medallion/scraping/ya_hechas.txt --out data/raw
        --parte 1 --partes 3 --max-paginas 985
"""
import os, sys, json, time, hashlib, glob, random, argparse
from datetime import datetime, timezone
import requests

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)  # si hay .env, su clave gana sobre la de la terminal
except ImportError:
    pass  # sin python-dotenv, la clave se toma de la variable de entorno

ENDPOINT = "https://api.firecrawl.dev/v2/scrape"
SEMILLA = 42                # misma semilla para todos: mismo orden y lotes sin cruces
ESPERA_MAXIMA = 15          # ninguna espera ni timeout pasa de esto (segundos)
MARGEN_SERVIDOR = 2         # Firecrawl corta 2 s antes que el script, para recibir su respuesta
FALLOS_SEGUIDOS_MAX = 10    # tantos fallos seguidos = caída de la red o de Firecrawl
REINTENTABLES = {408, 429, 500, 502, 503, 504}


def nombre_archivo(url):
    return hashlib.md5(url.encode()).hexdigest() + ".json"


def esta_ok(d):
    md = ((d.get("respuesta") or {}).get("data") or {}).get("markdown")
    return d.get("http_status") == 200 and bool(md)


def hechas_en_disco(out_dir):
    hechas = set()
    for ruta in glob.glob(os.path.join(out_dir, "*.json")):
        try:
            with open(ruta, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        if esta_ok(d) and d.get("url_pedida"):
            hechas.add(d["url_pedida"])
    return hechas


def guardar(ruta, registro):
    """Escribe primero a un temporal: si se corta a mitad, no queda un JSON roto."""
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False)
    os.replace(tmp, ruta)


def anotar_error(url, detalle):
    with open("errores.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {url} | {detalle}\n")


def segundos_retry_after(r):
    try:
        return float(r.headers.get("Retry-After", ""))
    except ValueError:
        return ESPERA_MAXIMA


class Ritmo:
    """Deja al menos `intervalo` segundos entre el INICIO de dos peticiones.

    El plan gratuito permite 10 peticiones por minuto (una cada 6 s). Si una
    página ya tardó 6 s o más, no se espera nada antes de la siguiente.
    """

    def __init__(self, intervalo):
        self.intervalo = intervalo
        self.ultimo = None

    def esperar(self):
        if self.ultimo is not None:
            falta = self.intervalo - (time.monotonic() - self.ultimo)
            if falta > 0:
                time.sleep(min(falta, ESPERA_MAXIMA))
        self.ultimo = time.monotonic()


def pedir(url, api_key, timeout):
    return requests.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={"url": url, "formats": ["markdown"], "onlyMainContent": True,
              "timeout": int((timeout - MARGEN_SERVIDOR) * 1000)},
        timeout=(5, timeout),
    )


def intentar(url, api_key, timeout, ritmo):
    """Pide una página. Devuelve (estado, dato).

    estado: 'ok' (dato = registro), 'reintentable' o 'fallo' (dato = detalle),
    'sin_credito' o 'clave_invalida'.
    Solo un 429 se reintenta en el momento, porque el límite es de la cuenta y
    saltar a otra página no ayudaría.
    """
    for intento in (1, 2):
        ritmo.esperar()
        try:
            r = pedir(url, api_key, timeout)
        except requests.Timeout:
            return "reintentable", f"sin respuesta en {timeout:g} s"
        except requests.RequestException as e:
            return "reintentable", f"error de red: {e.__class__.__name__}"
        if r.status_code == 429 and intento == 1:
            espera = min(segundos_retry_after(r), ESPERA_MAXIMA)
            print(f"    429: Firecrawl pide bajar el ritmo, espero {espera:g} s")
            time.sleep(espera)
            continue
        break

    if r.status_code == 402:
        return "sin_credito", "HTTP 402"
    if r.status_code == 401:
        return "clave_invalida", f"HTTP 401: {r.text[:150]}"

    try:
        cuerpo = r.json()
    except ValueError:
        cuerpo = None

    if r.status_code == 200 and cuerpo is not None:
        registro = {
            "url_pedida": url,
            "fecha_extraccion": datetime.now(timezone.utc).isoformat(),
            "http_status": r.status_code,
            "respuesta": cuerpo,
        }
        if esta_ok(registro):
            return "ok", registro
        return "fallo", f"HTTP 200 sin markdown: {str(cuerpo)[:200]!r}"

    texto = str(cuerpo) if cuerpo is not None else r.text
    detalle = f"HTTP {r.status_code}: {texto[:200]!r}"
    return ("reintentable" if r.status_code in REINTENTABLES else "fallo"), detalle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", default="eafit_urls.json")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--manifiesto", default="ya_hechas.txt")
    ap.add_argument("--parte", type=int, help="tu número de parte (1 a --partes)")
    ap.add_argument("--partes", type=int, help="cuántas partes hay en total (igual para todos)")
    ap.add_argument("--max-paginas", type=int, default=985,
                    help="tope de páginas a descargar en esta corrida (menos que tus créditos)")
    ap.add_argument("--pausa", type=float, default=6.0,
                    help="segundos mínimos entre el inicio de dos peticiones "
                         "(plan gratuito: 10 por minuto = 6 s)")
    ap.add_argument("--timeout", type=float, default=15.0,
                    help="segundos máximos por página (mínimo 3)")
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

    if a.parte is None or a.partes is None:
        sys.exit("Faltan --parte y --partes (por ejemplo: --parte 1 --partes 3)")
    if not (1 <= a.parte <= a.partes):
        sys.exit("--parte debe estar entre 1 y --partes")
    if a.timeout < MARGEN_SERVIDOR + 1:
        sys.exit(f"--timeout debe ser al menos {MARGEN_SERVIDOR + 1} segundos")
    if not os.path.exists(a.manifiesto):
        sys.exit(f"No encuentro el manifiesto {a.manifiesto}: sin él los lotes no son estables")
    api_key = (os.environ.get("FIRECRAWL_API_KEY") or "").strip()
    if not api_key:
        sys.exit("Falta la variable de entorno FIRECRAWL_API_KEY")
    if not api_key.startswith("fc-"):
        print("Ojo: la clave no empieza por 'fc-'; si sale HTTP 401, revisa FIRECRAWL_API_KEY")

    # Restos de una corrida cortada a mitad de escritura
    for tmp in glob.glob(os.path.join(a.out, "*.json.tmp")):
        os.remove(tmp)

    urls = sorted({x["url"] for x in json.load(open(a.urls, encoding="utf-8"))})
    random.Random(SEMILLA).shuffle(urls)

    # El reparto se calcula SOLO con el manifiesto, que es igual para todos.
    base = {l.strip() for l in open(a.manifiesto, encoding="utf-8") if l.strip()}
    pendientes_base = [u for u in urls if u not in base]
    lote_completo = pendientes_base[a.parte - 1::a.partes]
    huella = hashlib.md5(("\n".join(pendientes_base) + f"\n{a.partes}").encode()).hexdigest()[:8]

    # Dentro del lote, se saltan las páginas que ya están descargadas en disco.
    en_disco = hechas_en_disco(a.out)
    mi_lote = [u for u in lote_completo if u not in en_disco]

    print(f"Total URL: {len(urls)} | ya hechas: {len(base)} | pendientes: {len(pendientes_base)}")
    print(f"Huella del reparto: {huella} (debe ser igual para todos los compañeros)")
    print(f"Mi lote (parte {a.parte} de {a.partes}): {len(lote_completo)} | "
          f"ya descargadas de mi lote: {len(lote_completo) - len(mi_lote)} | "
          f"por hacer: {len(mi_lote)} | tope esta corrida: {a.max_paginas}")

    # Páginas en disco que pertenecen al lote de otro (por ejemplo, tras un git pull)
    indice = {u: i for i, u in enumerate(pendientes_base)}
    lote_set = set(lote_completo)
    ajenas = {}
    for u in en_disco:
        if u not in base and u not in lote_set and u in indice:
            k = indice[u] % a.partes + 1
            ajenas[k] = ajenas.get(k, 0) + 1
    if ajenas:
        detalle = ", ".join(f"parte {k}: {n}" for k, n in sorted(ajenas.items()))
        print(f"Aviso: en disco hay páginas de otros lotes ({detalle}). "
              f"No se vuelven a pedir, pero avísale a ese compañero.")

    a_bajar = min(len(mi_lote), a.max_paginas)
    print(f"Tiempo estimado: unos {a_bajar * a.pausa / 60:.0f} minutos "
          f"(Firecrawl gratis permite 10 páginas por minuto)")

    ritmo = Ritmo(a.pausa)
    descargadas = 0
    motivo_fin = None
    vueltas = [("primera vuelta", mi_lote)]
    try:
        while vueltas and motivo_fin is None:
            nombre, lista = vueltas.pop(0)
            fallidas = []
            seguidos = 0
            if nombre != "primera vuelta":
                print(f"--- {nombre}: {len(lista)} páginas ---")
            for i, url in enumerate(lista, 1):
                if descargadas >= a.max_paginas:
                    motivo_fin = f"tope de {a.max_paginas} páginas alcanzado"
                    break
                estado, dato = intentar(url, api_key, a.timeout, ritmo)
                if estado == "ok":
                    guardar(os.path.join(a.out, nombre_archivo(url)), dato)
                    descargadas += 1
                    seguidos = 0
                    n = len(dato["respuesta"]["data"]["markdown"])
                    print(f"[{i}/{len(lista)}] ok ({descargadas}) {n} car. | {url}")
                    continue
                if estado == "sin_credito":
                    motivo_fin = "sin créditos (HTTP 402)"
                    break
                if estado == "clave_invalida":
                    motivo_fin = f"clave inválida ({dato}). Revisa FIRECRAWL_API_KEY"
                    break
                anotar_error(url, dato)
                print(f"[{i}/{len(lista)}] fallo | {dato}")
                if estado == "reintentable":
                    fallidas.append(url)
                    seguidos += 1
                    if seguidos >= FALLOS_SEGUIDOS_MAX:
                        motivo_fin = (f"{seguidos} fallos seguidos: parece una caída de la red "
                                      f"o de Firecrawl. Reanuda más tarde con el mismo comando")
                        break
                else:
                    seguidos = 0
            if nombre == "primera vuelta" and fallidas and motivo_fin is None:
                vueltas.append(("segunda vuelta (páginas que fallaron)", fallidas))
    except KeyboardInterrupt:
        motivo_fin = "detenido con Ctrl + C"

    en_disco_ahora = hechas_en_disco(a.out)
    sin_hacer = [u for u in lote_completo if u not in en_disco_ahora]
    ruta_p = f"pendientes_parte{a.parte}.txt"
    with open(ruta_p, "w", encoding="utf-8") as f:
        f.write("\n".join(sin_hacer) + ("\n" if sin_hacer else ""))
    print(f"Listo. Descargadas ahora: {descargadas} | de mi lote tengo "
          f"{len(lote_completo) - len(sin_hacer)} de {len(lote_completo)} | "
          f"faltan {len(sin_hacer)} (en {ruta_p})")
    if motivo_fin:
        print(f"Motivo de parada: {motivo_fin}")


if __name__ == "__main__":
    main()