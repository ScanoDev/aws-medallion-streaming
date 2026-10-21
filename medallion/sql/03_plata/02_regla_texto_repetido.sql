-- R2: rechaza los tokens que forman parte de texto repetido en la mitad
-- o más de las páginas (pie de página y menús).
-- Justificación: hallazgo 2. Para un RAG, ese texto hace que todas las páginas se parezcan.
-- Efecto esperado: 676.863 filas incumplen (de las que no incumplen R1).
CREATE OR REPLACE VIEW eafit_medallion.regla_r2_texto_repetido AS
WITH b AS (
  SELECT pagina_id, posicion, try_cast(posicion AS integer) AS pos, token
  FROM eafit_medallion.bronce_tokens
),
ngramas AS (
  SELECT
    pagina_id,
    pos,
    concat_ws(' ',
      token,
      lead(token, 1) OVER (PARTITION BY pagina_id ORDER BY pos),
      lead(token, 2) OVER (PARTITION BY pagina_id ORDER BY pos),
      lead(token, 3) OVER (PARTITION BY pagina_id ORDER BY pos),
      lead(token, 4) OVER (PARTITION BY pagina_id ORDER BY pos),
      lead(token, 5) OVER (PARTITION BY pagina_id ORDER BY pos),
      lead(token, 6) OVER (PARTITION BY pagina_id ORDER BY pos),
      lead(token, 7) OVER (PARTITION BY pagina_id ORDER BY pos)
    ) AS ngrama
  FROM b
),
repetidas AS (
  SELECT ngrama
  FROM ngramas
  GROUP BY ngrama
  HAVING count(DISTINCT pagina_id) >= 0.5 * (SELECT count(DISTINCT pagina_id) FROM b)
),
-- Cada secuencia repetida cubre 8 posiciones: la inicial y las 7 siguientes
cubiertas AS (
  SELECT DISTINCT n.pagina_id, n.pos + k AS pos
  FROM ngramas n
  JOIN repetidas r ON n.ngrama = r.ngrama
  CROSS JOIN UNNEST(sequence(0, 7)) AS t(k)
)
SELECT
  b.pagina_id,
  b.posicion,
  c.pagina_id IS NOT NULL AS incumple_r2
FROM b
LEFT JOIN cubiertas c
  ON b.pagina_id = c.pagina_id AND b.pos = c.pos;