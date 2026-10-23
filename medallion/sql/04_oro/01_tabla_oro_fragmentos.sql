-- Oro: fragmentos (chunks) de texto limpio, listos para indexar en el RAG de ORION.
-- Agrega los tokens válidos de plata, en orden, en bloques de 200 tokens por página.
-- Pregunta: ¿cuál es el texto limpio de cada página y cuántos fragmentos aporta cada sección?
-- Efecto esperado: 5.446 fragmentos de 1.019 páginas.
-- Para volver a crearla: DROP TABLE IF EXISTS eafit_medallion.oro_fragmentos;
CREATE TABLE eafit_medallion.oro_fragmentos
WITH (
  table_type = 'ICEBERG',
  is_external = false,
  format = 'PARQUET',
  location = 's3://medallion-eafit-2026-orion/oro/fragmentos/'
) AS
WITH numerados AS (
  SELECT
    pagina_id,
    url,
    posicion,
    token_limpio,
    row_number() OVER (PARTITION BY pagina_id ORDER BY posicion) AS n
  FROM eafit_medallion.plata_tokens_validos
)
SELECT
  split_part(url, '/', 4)                                   AS seccion,
  pagina_id,
  url,
  CAST((n - 1) / 200 + 1 AS integer)                        AS numero_fragmento,
  CAST(count(*) AS integer)                                 AS n_tokens,
  array_join(array_agg(token_limpio ORDER BY posicion), ' ') AS texto
FROM numerados
GROUP BY 1, 2, 3, 4;