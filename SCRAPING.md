# Obtención de los datos

Las páginas se extrajeron del sitio público de la Universidad EAFIT (eafit.edu.co) con la API de Firecrawl (endpoint `/v2/scrape`, formato markdown, solo contenido principal).

## Muestra
- Universo: 4.991 URLs del sitio (`parte_a_medallion/scraping/eafit_urls.json`).
- Muestra: 1.024 páginas, elegidas al azar barajando las URLs con semilla 42.
- Resultado: un JSON por página en `data/raw/`, con la URL, la fecha de extracción y la respuesta completa de Firecrawl.

## Cómo reproducirlo
Desde la raíz del repo:
```bash
pip install requests
export FIRECRAWL_API_KEY="su-clave"
python medallion/scraping/scrape_masivo.py \
  --urls medallion/scraping/eafit_urls.json \
  --manifiesto medallion/scraping/ya_hechas.txt \
  --out data/raw \
  --max-paginas 1024
```