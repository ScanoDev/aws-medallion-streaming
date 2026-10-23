SELECT motivo_rechazo, count(*) AS filas
FROM eafit_medallion.plata_tokens_rechazados
GROUP BY motivo_rechazo
ORDER BY motivo_rechazo;