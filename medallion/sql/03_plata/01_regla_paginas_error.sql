-- R1: rechaza los tokens de páginas que respondieron con error HTTP.
-- Justificación: hallazgo 7 (páginas 404 sin contenido real).
-- Efecto esperado: 4.825 filas incumplen.
CREATE OR REPLACE VIEW eafit_medallion.regla_r1_paginas_error AS
SELECT
  pagina_id,
  posicion,
  status_pagina <> '200' AS incumple_r1
FROM eafit_medallion.bronce_tokens;