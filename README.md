# aws-medallion-streaming
super descripción que aun debo hacer

# A - dmkasñda
## Punto 1
asdasd

## Punto 2
Sabemos que glue se encarga de encontrar la estructura de las tablas o de los datos que le demos, y también que Athena utiliza Glue por defecto, sin embargo, en este caso glue no detecta la estructura de manera automática, para eso tendríamos que usar glue crawler, el cual se cobra a parte.

## Punto 3
Se encontraron los siguientes hallazgos por medio de las consultas sql.

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



## Punto 4
Vemos que hay palabras en inglés y en español. Sin embargo, también vemos que hay metadata de la página que declara ser en inglés 
pero realmente la info está en español, por eso tomaremos tanto las palabras en inglés como en español. El algoritmo BM25 no puede 
cruzar idiomas, entonces para este caso en particular se tiene como solución la búsqueda vectorial, la cual no se abarca en este 
proyecto. Los markdown también pueden contener información útil para el modelo.

Cada fila se rechaza con el motivo de la primera regla que incumple, en este orden.

| Regla | Qué rechaza | Hallazgo que la justifica |
|---|---|---|
| R1 | Tokens de páginas que respondieron con error HTTP | #7 |
| R2 | Tokens que forman parte de texto repetido en la mitad o más de las páginas (pie de página y menús) | #2 |
| R3 | Tokens que quedan sin letras ni números después de quitar sintaxis markdown, URLs y símbolos de formato | #9, #10 y #11 |

## Parte B: Streaming (IoT Core → SQS → Lambda → DynamoDB)

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
