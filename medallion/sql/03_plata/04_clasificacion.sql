-- Junta las tres reglas. Cada fila queda con su motivo de rechazo
-- (el de la primera regla que incumple) o NULL si es válida.
CREATE OR REPLACE VIEW eafit_medallion.plata_clasificada AS
SELECT
  b.*,
  r3.token_limpio,
  CASE
    WHEN r1.incumple_r1 THEN 'R1: página con error HTTP'
    WHEN r2.incumple_r2 THEN 'R2: texto repetido (pie de página o menú)'
    WHEN r3.incumple_r3 THEN 'R3: token sin contenido después de limpiar'
  END AS motivo_rechazo
FROM eafit_medallion.bronce_tokens b
JOIN eafit_medallion.regla_r1_paginas_error r1
  ON b.pagina_id = r1.pagina_id AND b.posicion = r1.posicion
JOIN eafit_medallion.regla_r2_texto_repetido r2
  ON b.pagina_id = r2.pagina_id AND b.posicion = r2.posicion
JOIN eafit_medallion.regla_r3_token_sin_contenido r3
  ON b.pagina_id = r3.pagina_id AND b.posicion = r3.posicion;