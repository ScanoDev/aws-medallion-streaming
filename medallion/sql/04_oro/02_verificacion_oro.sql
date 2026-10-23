-- La suma de tokens en oro debe ser igual a las filas válidas de plata: 987.442
SELECT count(*) AS fragmentos, count(DISTINCT pagina_id) AS paginas, sum(n_tokens) AS tokens
FROM eafit_medallion.oro_fragmentos;

-- Respuesta a la pregunta: fragmentos que aporta cada sección del sitio
SELECT seccion, count(DISTINCT pagina_id) AS paginas, count(*) AS fragmentos
FROM eafit_medallion.oro_fragmentos
GROUP BY seccion
ORDER BY fragmentos DESC
LIMIT 10;