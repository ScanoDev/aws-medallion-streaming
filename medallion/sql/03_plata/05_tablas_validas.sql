-- Tabla Iceberg de plata con las filas válidas, ya con tipos de datos.
-- La fecha vacía (hallazgo 3) se conserva como NULL: el contenido es bueno.
-- Efecto esperado: 987.442 filas.
CREATE TABLE eafit_medallion.plata_tokens_validos
WITH (
  table_type = 'ICEBERG',
  is_external = false,
  format = 'PARQUET',
  location = 's3://medallion-eafit-2026-orion/plata/tokens_validos/'
) AS
SELECT
  pagina_id,
  url,
  idioma,
  CAST(status_pagina AS integer) AS status_pagina,
  try(CAST(date_parse(substr(fecha_extraccion, 1, 19), '%Y-%m-%dT%H:%i:%s') AS timestamp(6))) AS fecha_extraccion_utc,
  CAST(posicion AS integer) AS posicion,
  token AS token_original,
  token_limpio
FROM eafit_medallion.plata_clasificada
WHERE motivo_rechazo IS NULL;