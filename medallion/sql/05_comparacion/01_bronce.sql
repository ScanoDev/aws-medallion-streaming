-- Comparación: ¿cuántas páginas tiene cada sección del sitio? (capa bronce)
SELECT split_part(url, '/', 4) AS seccion, count(DISTINCT pagina_id) AS paginas
FROM eafit_medallion.bronce_tokens
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;