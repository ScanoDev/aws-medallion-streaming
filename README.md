# aws-medallion-streaming
super descripción que aun debo hacer

# A - dmkasñda
## Punto 1
asdasd

## Punto 2
sdsdf

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

# B - saoñdas
