-- R3: limpia cada token (quita sintaxis markdown, URLs y símbolos de formato)
-- y rechaza los que quedan sin letras ni números.
-- Justificación: hallazgos 9, 10 y 11. Limpiar antes de rechazar conserva
-- las palabras dentro de los enlaces: "[Reglamentos" pasa a "Reglamentos".
-- Efecto esperado: 50.653 filas incumplen (de las que no incumplen R1 ni R2).
CREATE OR REPLACE VIEW eafit_medallion.regla_r3_token_sin_contenido AS
WITH limpieza AS (
  SELECT
    pagina_id,
    posicion,
    regexp_replace(
      regexp_replace(
        regexp_replace(token, '\]\([^)]*\)?', ''),
        'https?://\S*|www\.\S*|mailto:\S*', ''),
      '[\[\]!*#|()_`>]', '') AS token_limpio
  FROM eafit_medallion.bronce_tokens
)
SELECT
  pagina_id,
  posicion,
  token_limpio,
  NOT regexp_like(token_limpio, '[\p{L}\p{N}]') AS incumple_r3
FROM limpieza;