# aws-medallion-streaming

Trabajo 1 del curso **Almacenamiento y Procesamiento de Grandes Datos** (Maestría en Ciencias de los Datos y Analítica, Universidad EAFIT, 2026).

| Parte | Qué hace | Servicios |
|---|---|---|
| A | Arquitectura Medallion (bronce, plata y oro) sobre el texto del sitio web de EAFIT | S3, Athena, Glue Data Catalog, Iceberg |
| B | Flujo de streaming de eventos | IoT Core, SQS, Lambda, DynamoDB |

Todos los recursos de AWS se crearon manualmente en la consola, sin infraestructura como código. Región de trabajo: `us-east-1`.

---

# Parte A: capas Medallion

## 1. Descripción del conjunto de datos

**Qué es:** el texto de 1.024 páginas públicas de **eafit.edu.co**, con una fila por token (cada palabra o símbolo separado por espacios). Es la fuente de conocimiento de ORION, el chatbot con RAG de nuestro proyecto integrador.

**De dónde proviene:** se extrajo con la API de **Firecrawl** el 20 y 21 de octubre de 2026, en formato markdown. Las 1.024 páginas son una muestra aleatoria (semilla 42) de las 4.991 URLs del sitio. Los JSON originales están en `data/raw/` y el script que genera el archivo de bronce en `medallion/scripts/bronce.py`.

**Por qué una fila por token:** esta granularidad es un índice invertido posicional, la estructura sobre la que funciona la búsqueda por palabras clave (BM25) de un RAG híbrido. No se usó aumento de datos: el millón de filas sale de los datos reales a esta granularidad.

| Columna | Tipo real | Descripción |
|---|---|---|
| `pagina_id` | texto | Hash MD5 de la URL |
| `url` | texto | Dirección de la página |
| `idioma` | texto | Idioma declarado en los metadatos de la página |
| `status_pagina` | entero | Código HTTP de la página |
| `fecha_extraccion` | fecha y hora | Momento de la extracción (UTC) |
| `posicion` | entero | Posición del token dentro de la página |
| `token` | texto | El token tal como aparece en el markdown |

| Filas | Páginas | Peso | Formato |
|---:|---:|---:|---|
| 1.719.783 | 1.024 | 314,5 MB | TSV (separado por tabulaciones) |

## 2. Bronce

El archivo está en `s3://medallion-eafit-2026-orion/bronce/tokens/` y la tabla externa `eafit_medallion.bronce_tokens` lo lee con **todas las columnas como texto**.

La estructura de la tabla se definió manualmente con `CREATE EXTERNAL TABLE` y quedó registrada en el catálogo de Glue, que Athena usa por defecto. No se usó un Glue Crawler porque habría adivinado tipos numéricos y de fecha, mientras que en bronce todo debe ser texto, y porque conocemos el formato exacto del archivo. Se eligió TSV en lugar de CSV porque 78 tokens terminan en barra invertida, que el lector de CSV interpreta como escape y rompe filas.

Consulta: `medallion/sql/01_bronce/`

## 3. Hallazgos

Defectos cuantificados con SQL sobre bronce. Un mismo token puede tener varios defectos, por lo que los porcentajes no se suman.

| # | Defecto | Filas | % |
|---|---|---:|---:|
| 1 | Filas repetidas por clave (pagina_id, posicion) | 0 | 0,00 |
| 2 | Texto repetido en 50 % o más de las páginas (pie de página, menús) | 666.406 | 38,75 |
| 3 | Fecha de extracción vacía | 41.113 | 2,39 |
| 4 | Fecha de extracción con formato inválido | 0 | 0,00 |
| 5 | Posición no numérica | 0 | 0,00 |
| 6 | Token vacío | 0 | 0,00 |
| 7 | Página con error HTTP (status distinto de 200) | 4.825 | 0,28 |
| 8 | Página en un idioma distinto al español | 506.567 | 29,46 |
| 9 | Token que es una URL | 147.340 | 8,57 |
| 10 | Token con sintaxis de enlace o imagen markdown | 258.809 | 15,05 |
| 11 | Token sin letras ni números (solo símbolos) | 129.297 | 7,52 |
| 12 | Token de una página casi vacía (menos de 50 tokens) | 66 | 0,00 |

Lo más relevante:
1. **El pie de página de EAFIT** (teléfonos, WhatsApp, direcciones de las sedes) aparece en 1.014 de las 1.024 páginas. Para un RAG es dañino, porque hace que todas las páginas se parezcan.
2. **El metadato de idioma no es confiable:** 176 de las 263 páginas marcadas como inglés tienen el texto en español.
3. **La fecha vacía** viene de 25 páginas descargadas con una versión anterior del script que no la guardaba.

Consulta: `medallion/sql/02_hallazgos/` · Resultado: `medallion/resultados/hallazgos.csv`

## 4. Plata

### Reglas de calidad

Antes de aplicar las reglas, cada token se **limpia**: se quita la sintaxis markdown, las URLs y los símbolos de formato. Así se conservan las palabras que vienen dentro de los enlaces (por ejemplo, `[Reglamentos` pasa a `Reglamentos`): de los 258.856 tokens con enlaces o URLs, 254.079 contienen una palabra real.

Cada fila se rechaza con el motivo de la primera regla que incumple, en este orden:

| Regla | Qué rechaza | Hallazgo |
|---|---|---|
| R1 | Tokens de páginas que respondieron con error HTTP | #7 |
| R2 | Tokens que forman parte de texto repetido en la mitad o más de las páginas | #2 |
| R3 | Tokens que quedan sin letras ni números después de limpiarlos | #9, #10 y #11 |

Decisiones sobre los hallazgos que no generan regla:
1. **Idioma (#8):** no se filtra, porque el metadato es incorrecto en la mayoría de los casos y el contenido en inglés también es útil: los LLM y los embeddings multilingües lo entienden. La búsqueda BM25 no cruza idiomas; eso lo resuelve la búsqueda vectorial, que está fuera del alcance de este trabajo.
2. **Fecha vacía (#3):** la fila se conserva con fecha nula, porque el defecto es de metadatos y el contenido es válido.

### Tablas Iceberg y cuadre

| Tabla | Filas |
|---|---:|
| `bronce_tokens` | 1.719.783 |
| `plata_tokens_validos` | 987.442 |
| `plata_tokens_rechazados` | 732.341 |
| R1: página con error HTTP | 4.825 |
| R2: texto repetido | 676.863 |
| R3: token sin contenido después de limpiar | 50.653 |

**Cuadre:** 987.442 válidas + 732.341 rechazadas = 1.719.783 filas de bronce. Diferencia: 0.

En plata los datos ya tienen sus tipos reales (entero, fecha y hora) y se guardan en Parquet.

Consultas: `medallion/sql/03_plata/`

## 5. Oro

**Pregunta:** ¿cuál es el texto limpio, listo para indexar en el RAG de ORION, de cada página, y cuántos fragmentos aporta cada sección del sitio?

La tabla Iceberg `oro_fragmentos` agrega los tokens válidos de plata, en orden, en fragmentos de 200 tokens por página.

| Fragmentos | Páginas | Tokens |
|---:|---:|---:|
| 5.446 | 1.019 | 987.442 |

La suma de tokens coincide con las filas válidas de plata, así que no se perdió ni se duplicó contenido.

| Sección | Páginas | Fragmentos |
|---|---:|---:|
| noticias | 291 | 1.803 |
| sistema de ciencia, tecnología e innovación | 134 | 706 |
| en (versión en inglés) | 26 | 389 |
| posgrados | 17 | 379 |
| informes de gestión y sostenibilidad | 36 | 360 |

**Respuesta:** noticias es la sección que más contenido aporta al RAG. La versión en inglés aporta 389 fragmentos, lo que confirma la decisión de no filtrar por idioma.

Consultas: `medallion/sql/04_oro/`

## 6. Comparación

Misma consulta en las tres capas: ¿cuántas páginas tiene cada sección del sitio?

| Capa | Tabla | Formato | Datos escaneados | Tiempo |
|---|---|---|---:|---:|
| Bronce | `bronce_tokens` | TSV | POR MEDIR | POR MEDIR |
| Plata | `plata_tokens_validos` | Parquet (Iceberg) | POR MEDIR | POR MEDIR |
| Oro | `oro_fragmentos` | Parquet (Iceberg) | POR MEDIR | POR MEDIR |

**Interpretación:** en bronce, Athena debe leer el archivo de texto completo aunque la consulta solo use dos columnas. Plata está en Parquet, un formato por columnas y comprimido: Athena lee solo `url` y `pagina_id`, que además se comprimen muy bien porque se repiten en cada token de la misma página. Oro tiene apenas 5.446 filas porque ya está agregado. Menos bytes escaneados significa consultas más rápidas y más baratas, porque Athena cobra por datos escaneados.

Consultas: `medallion/sql/05_comparacion/`

## Pregunta final: si los datos fueran mil veces mayores, ¿qué cambiaríamos?

Serían unas 1.700 millones de filas y unos 314 GB en bronce (alrededor de un millón de páginas). Cambiaríamos:

1. **La extracción:** el plan gratuito de Firecrawl no alcanza. Usaríamos un crawler propio distribuido o un plan pagado, con extracción incremental (solo páginas nuevas o modificadas).
2. **El archivo de bronce:** no un solo TSV de 314 GB, sino muchos archivos de 128 MB a 1 GB, comprimidos y particionados por fecha de extracción, para que Athena los lea en paralelo y solo lea las particiones necesarias.
3. **El costo:** con Athena cobrando por datos escaneados, cada consulta a bronce leería 314 GB. Nadie consultaría bronce directamente, y configuraríamos un límite de datos escaneados por consulta en el workgroup.
4. **Plata incremental:** en lugar de recrear las tablas con `CREATE TABLE AS`, cargaríamos solo lo nuevo con `MERGE` de Iceberg, particionaríamos las tablas (por ejemplo, por sección) y correríamos `OPTIMIZE` y `VACUUM` para compactar archivos pequeños y borrar versiones viejas.
5. **La regla R2:** agrupar 1.700 millones de secuencias de 8 tokens es muy costoso. Detectaríamos el texto repetido con una muestra de páginas o con técnicas de hashing como MinHash, y moveríamos las transformaciones pesadas a Spark (AWS Glue o EMR) en lugar de Athena.
6. **Oro y el RAG:** serían unos 5,4 millones de fragmentos. Sus embeddings irían a una base vectorial (por ejemplo, OpenSearch), no a Athena.

---

# Parte B: Streaming (IoT Core → SQS → Lambda → DynamoDB)

### Responsable de esta sección
Puntos 1 y 3 del enunciado: regla de IoT Core hacia SQS y tabla de DynamoDB con llave justificada. También incluye la elección del dataset y la configuración de acceso del equipo.

Todos los recursos se crearon manualmente desde la consola de AWS (sin infraestructura como código), en la región `us-east-1`.

### Dataset
**Household Electric Power Consumption** (UCI Machine Learning Repository, disponible también en Kaggle). Autores originales: Georges Hebrail y Alice Bérard (EDF R&D).

- Archivo `.txt` con separador `;`, ~2,07 millones de mediciones (una por minuto, diciembre de 2006 a noviembre de 2010).
- Columnas: `Date` (dd/mm/aaaa), `Time` (hh:mm:ss), `Global_active_power`, `Global_reactive_power`, `Voltage`, `Global_intensity`, `Sub_metering_1`, `Sub_metering_2`, `Sub_metering_3`.
- Los valores faltantes vienen marcados con `?`. No se eliminan antes de publicar, de modo que los descartes (con su motivo) salen de datos reales y no de datos inyectados.

**Por qué este dataset:** supera el millón de filas, tiene timestamp propio (necesario para medir el retraso), tipos numéricos con un esquema claro y faltantes naturales que sirven para demostrar el descarte de eventos.

### Esquema del evento
```json
{
  "event_id": "0000000",
  "date": "16/12/2006",
  "time": "17:24:00",
  "global_active_power": 4.216,
  "global_reactive_power": 0.418,
  "voltage": 234.84,
  "global_intensity": 18.4,
  "sub_metering_1": 0.0,
  "sub_metering_2": 1.0,
  "sub_metering_3": 17.0,
  "sent_at": 1761072000123
}
```
- `event_id`: número de fila del archivo (7 dígitos). Permite el cuadre de eventos y detectar duplicados.
- `sent_at`: epoch en milisegundos, asignado por el publicador justo antes de enviar. Con él se mide el retraso.

### Punto 3: Tablas de DynamoDB (modo On-demand)

| Tabla | Partición | Orden | Uso |
|---|---|---|---|
| `eventos_energia` | `date` (String, aaaa-mm-dd) | `time` (String, hh:mm:ss) | Eventos válidos |
| `eventos_descartados` | `event_id` (String) | n/a | Eventos rechazados, con el campo `motivo` |

**Justificación de la llave de `eventos_energia`:**
- Hay ~1.440 lecturas por día repartidas en ~1.442 días, así que la carga se distribuye en muchas particiones y ninguna se vuelve "caliente".
- La combinación `date` + `time` es única, porque hay una lectura por minuto.
- Permite consultas eficientes: todos los eventos de un día, o un rango de horas dentro de un día.
- Se usa el modo On-demand para evitar límites de escritura durante la ráfaga de eventos.

### Punto 1: Regla de IoT Core → SQS

**Colas SQS (tipo Standard):**
- `cola_eventos_energia`: cola principal, visibility timeout de 60 s, con DLQ y máximo de 3 recepciones.
- `cola_eventos_energia_dlq`: cola de mensajes fallidos.

Se eligió Standard (no FIFO) por rendimiento y porque la regla de IoT Core no necesita configuración adicional.

**Regla de IoT Core `regla_energia_sqs`:**
```sql
SELECT * FROM 'energia/lecturas'
```
Acción: enviar el mensaje completo a `cola_eventos_energia`.

**Verificación:** se publicó un mensaje de prueba en el tema `energia/lecturas` desde el cliente de prueba MQTT de la consola de IoT Core, y se comprobó que apareció en la cola mediante *Poll for messages*.


<img width="1919" height="875" alt="image" src="https://github.com/user-attachments/assets/7ac63200-19a5-4761-a684-9dd46b69f5dd" />

<img width="1920" height="700" alt="image" src="https://github.com/user-attachments/assets/457f03db-21cc-413e-9b06-be8eafe430d9" />

<img width="1920" height="656" alt="image" src="https://github.com/user-attachments/assets/b6439487-cfe1-4950-8871-9e74a86322fd" />




### Acceso del equipo (IAM)
El flujo completo vive en una sola cuenta de AWS, por lo que se crearon usuarios de IAM para los demás integrantes:
- Grupo `equipo_streaming` con permisos de Lambda, lectura de SQS, lectura de DynamoDB, publicación en IoT Core, lectura de logs de CloudWatch y CloudShell.
- Rol `rol_lambda_energia` (confianza: `lambda.amazonaws.com`) con `AWSLambdaSQSQueueExecutionRole` y una política en línea que solo permite `dynamodb:PutItem` sobre las dos tablas.
- Se aplicó el principio de mínimo privilegio: los usuarios no pueden purgar la cola ni borrar ítems de las tablas.
- Al entregar el trabajo, los usuarios y sus claves se desactivan.
