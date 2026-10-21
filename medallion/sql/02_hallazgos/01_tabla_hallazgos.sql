-- Tabla de hallazgos: defectos de calidad de la capa de bronce.
-- Cada fila cuenta cuántas filas de bronce tienen ese defecto.
-- Un mismo token puede tener varios defectos, así que los porcentajes NO se suman.
WITH b AS (
  SELECT * FROM eafit_medallion.bronce_tokens
),
total AS (
  SELECT count(*) AS n, count(DISTINCT pagina_id) AS paginas FROM b
),
-- Secuencias de 8 tokens seguidos dentro de cada página
ngramas AS (
  SELECT
    pagina_id,
    concat_ws(' ',
      token,
      lead(token, 1) OVER (PARTITION BY pagina_id ORDER BY try_cast(posicion AS integer)),
      lead(token, 2) OVER (PARTITION BY pagina_id ORDER BY try_cast(posicion AS integer)),
      lead(token, 3) OVER (PARTITION BY pagina_id ORDER BY try_cast(posicion AS integer)),
      lead(token, 4) OVER (PARTITION BY pagina_id ORDER BY try_cast(posicion AS integer)),
      lead(token, 5) OVER (PARTITION BY pagina_id ORDER BY try_cast(posicion AS integer)),
      lead(token, 6) OVER (PARTITION BY pagina_id ORDER BY try_cast(posicion AS integer)),
      lead(token, 7) OVER (PARTITION BY pagina_id ORDER BY try_cast(posicion AS integer))
    ) AS ngrama
  FROM b
),
-- Secuencias que aparecen en al menos la mitad de las páginas: pie de página y menús
repetidas AS (
  SELECT ngrama
  FROM ngramas
  GROUP BY ngrama
  HAVING count(DISTINCT pagina_id) >= 0.5 * (SELECT paginas FROM total)
),
paginas_cortas AS (
  SELECT pagina_id FROM b GROUP BY pagina_id HAVING count(*) < 50
),
hallazgos AS (
  SELECT 1 AS orden, 'Filas repetidas por clave (pagina_id, posicion)' AS defecto,
         (SELECT count(*) FROM (SELECT pagina_id, posicion FROM b
                                GROUP BY pagina_id, posicion HAVING count(*) > 1)) AS filas
  UNION ALL
  SELECT 2, 'Texto repetido en 50 % o más de las páginas (pie de página, menús)',
         (SELECT count(*) FROM ngramas n JOIN repetidas r ON n.ngrama = r.ngrama)
  UNION ALL
  SELECT 3, 'Fecha de extracción vacía',
         count_if(fecha_extraccion IS NULL OR trim(fecha_extraccion) = '') FROM b
  UNION ALL
  SELECT 4, 'Fecha de extracción con formato inválido',
         count_if(trim(fecha_extraccion) <> ''
                  AND NOT regexp_like(fecha_extraccion, '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')) FROM b
  UNION ALL
  SELECT 5, 'Posición no numérica',
         count_if(try_cast(posicion AS integer) IS NULL) FROM b
  UNION ALL
  SELECT 6, 'Token vacío',
         count_if(token IS NULL OR trim(token) = '') FROM b
  UNION ALL
  SELECT 7, 'Página con error HTTP (status distinto de 200)',
         count_if(status_pagina <> '200') FROM b
  UNION ALL
  SELECT 8, 'Página en un idioma distinto al español',
         count_if(idioma <> 'es') FROM b
  UNION ALL
  SELECT 9, 'Token que es una URL',
         count_if(regexp_like(lower(token), 'https?://|www\.')) FROM b
  UNION ALL
  SELECT 10, 'Token con sintaxis de enlace o imagen markdown',
         count_if(regexp_like(token, '\]\(|!\[|^\[')) FROM b
  UNION ALL
  SELECT 11, 'Token sin letras ni números (solo símbolos)',
         count_if(NOT regexp_like(token, '[\p{L}\p{N}]')) FROM b
  UNION ALL
  SELECT 12, 'Token de una página casi vacía (menos de 50 tokens)',
         count_if(pagina_id IN (SELECT pagina_id FROM paginas_cortas)) FROM b
)
SELECT
  orden,
  defecto,
  filas,
  round(100.0 * filas / (SELECT n FROM total), 2) AS porcentaje
FROM hallazgos
ORDER BY orden;