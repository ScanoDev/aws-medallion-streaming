# Scraping EAFIT con Firecrawl

Cada integrante raspa su tramo con SU PROPIA cuenta de Firecrawl.

## Reglas
- NO modificar `ya_hechas.txt` ni correr `--generar-manifiesto`: de ese archivo depende que los tramos no se solapen.
- NUNCA escribir la API key en archivos ni subirla al repo. Va solo como variable de entorno.
- Antes de correr, revisar el saldo en el dashboard de Firecrawl y ajustar `--max-paginas` (dejar ~15 créditos de colchón).

## Pasos
```bash
git clone <URL-DEL-REPO>
cd <carpeta-del-repo>
pip install requests
export FIRECRAWL_API_KEY="su-clave"
python scrape_masivo.py --parte K --partes 4 --max-paginas 985
```
K = 1, 2, 3 o 4 (Depende del orden, jose es 1 y ya los demas se reparten).

La primera línea de salida debe decir `ya hechas: 1024`, no 0.
Se puede parar con Ctrl+C y retomar con el mismo comando sin repetir ni pagar dos veces.

## Entregar lo raspado
```bash
git checkout -b datos-parte-K
git add data/raw
git commit -m "Datos parte K"
git push -u origin datos-parte-K
```
Al terminar, enviar también el archivo `pendientes_parteK.txt` por el grupo.
## Parte 4
La parte 4 (`--parte 4`) queda sin asignar por ahora; la toma quien tenga créditos extra.
