-- Tabla Iceberg de plata con las filas rechazadas y su motivo.
-- Se guardan tal cual venían de bronce, para poder auditarlas.
-- Efecto esperado: 732.341 filas.
CREATE TABLE eafit_medallion.plata_tokens_rechazados
WITH (
  table_type = 'ICEBERG',
  is_external = false,
  format = 'PARQUET',
  location = 's3://medallion-eafit-2026-orion/plata/tokens_rechazados/'
) AS
SELECT
  pagina_id,
  url,
  idioma,
  status_pagina,
  fecha_extraccion,
  posicion,
  token,
  motivo_rechazo
FROM eafit_medallion.plata_clasificada
WHERE motivo_rechazo IS NOT NULL;