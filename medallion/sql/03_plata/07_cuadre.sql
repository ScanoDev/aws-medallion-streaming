-- Cuadre: bronce = válidas + rechazadas. La diferencia debe ser 0.
SELECT
  (SELECT count(*) FROM eafit_medallion.bronce_tokens)           AS filas_bronce,
  (SELECT count(*) FROM eafit_medallion.plata_tokens_validos)    AS filas_validas,
  (SELECT count(*) FROM eafit_medallion.plata_tokens_rechazados) AS filas_rechazadas,
  (SELECT count(*) FROM eafit_medallion.bronce_tokens)
    - (SELECT count(*) FROM eafit_medallion.plata_tokens_validos)
    - (SELECT count(*) FROM eafit_medallion.plata_tokens_rechazados) AS diferencia;