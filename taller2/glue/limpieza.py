"""
Reglas de limpieza del taller 2 (vienen del taller 1, pasadas a PySpark).

Entrada: DataFrame de tokens con las columnas
    pagina_id, url, idioma, status_pagina, fecha_extraccion, posicion, token

Uso:
    validos, rechazados = limpiar(df_tokens)

validos:    columnas de entrada + token_limpio
rechazados: columnas de entrada + motivo_rechazo

Cada fila se rechaza con el motivo de la primera regla que incumple (R1, R2, R3).
"""
from pyspark.sql import functions as F
from pyspark.sql import Window

MOTIVO_R1 = "R1: página con error HTTP"
MOTIVO_R2 = "R2: texto repetido (pie de página o menú)"
MOTIVO_R3 = "R3: token sin contenido después de limpiar"

TAM_SECUENCIA = 8      # tokens seguidos que forman una secuencia
UMBRAL_PAGINAS = 0.5   # fracción mínima de páginas para considerarla repetida


def marcar_r1(df):
    """R1: la página respondió con un código distinto de 200."""
    return df.withColumn(
        "incumple_r1",
        F.coalesce(F.col("status_pagina").cast("string") != F.lit("200"), F.lit(True)),
    )


def marcar_r2(df):
    """
    R2: el token hace parte de una secuencia de 8 tokens que aparece
    en al menos la mitad de las páginas (pie de página, menús).
    """
    orden = Window.partitionBy("pagina_id").orderBy("posicion")
    siguientes = [F.lead("token", k).over(orden) for k in range(1, TAM_SECUENCIA)]
    con_secuencia = df.withColumn("secuencia", F.concat_ws(" ", F.col("token"), *siguientes))

    total_paginas = df.select("pagina_id").distinct().count()
    repetidas = (
        con_secuencia.groupBy("secuencia")
        .agg(F.countDistinct("pagina_id").alias("paginas"))
        .filter(F.col("paginas") >= UMBRAL_PAGINAS * total_paginas)
        .select("secuencia", F.lit(True).alias("inicia_repetida"))
    )

    marcado = con_secuencia.join(F.broadcast(repetidas), "secuencia", "left").fillna(
        False, subset=["inicia_repetida"]
    )

    # Una secuencia que empieza en la posición p cubre p, p+1, ..., p+7.
    # Entonces un token está cubierto si alguna secuencia repetida empieza
    # entre su posición menos 7 y su posición.
    ventana = orden.rangeBetween(-(TAM_SECUENCIA - 1), 0)
    return marcado.withColumn(
        "incumple_r2", F.max("inicia_repetida").over(ventana)
    ).drop("secuencia", "inicia_repetida")


def limpiar_token(col):
    """Limpia un token en este orden: enlace markdown, URLs, símbolos de formato."""
    sin_enlace = F.regexp_replace(col, r"\]\([^)]*\)?", "")
    sin_urls = F.regexp_replace(sin_enlace, r"https?://\S*|www\.\S*|mailto:\S*", "")
    return F.regexp_replace(sin_urls, r"[\[\]!*#|()_`>]", "")


def marcar_r3(df):
    """R3: después de limpiar, el token no tiene ninguna letra ni número."""
    return df.withColumn("token_limpio", limpiar_token(F.col("token"))).withColumn(
        "incumple_r3", ~F.col("token_limpio").rlike(r"[\p{L}\p{N}]")
    )


def clasificar(df):
    """Aplica R1, R2 y R3 y deja en motivo_rechazo el de la primera que incumple (nulo si es válida)."""
    columnas = df.columns
    marcado = marcar_r3(marcar_r2(marcar_r1(df)))
    motivo = (
        F.when(F.col("incumple_r1"), F.lit(MOTIVO_R1))
        .when(F.col("incumple_r2"), F.lit(MOTIVO_R2))
        .when(F.col("incumple_r3"), F.lit(MOTIVO_R3))
    )
    return marcado.withColumn("motivo_rechazo", motivo).select(
        *columnas, "token_limpio", "motivo_rechazo"
    )


def limpiar(df):
    """Devuelve (validos, rechazados)."""
    clasificado = clasificar(df).cache()
    validos = clasificado.filter(F.col("motivo_rechazo").isNull()).drop("motivo_rechazo")
    rechazados = clasificado.filter(F.col("motivo_rechazo").isNotNull()).drop("token_limpio")
    return validos, rechazados