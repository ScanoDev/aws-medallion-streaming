CREATE DATABASE IF NOT EXISTS eafit_medallion;

CREATE EXTERNAL TABLE eafit_medallion.bronce_tokens (
  pagina_id        string,
  url              string,
  idioma           string,
  status_pagina    string,
  fecha_extraccion string,
  posicion         string,
  token            string
)
ROW FORMAT DELIMITED
  FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION 's3://medallion-eafit-2026-orion/bronce/tokens/'
TBLPROPERTIES ('skip.header.line.count' = '1');