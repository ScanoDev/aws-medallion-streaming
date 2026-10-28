import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from limpieza import limpiar

args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext()
glue = GlueContext(sc)
spark = glue.spark_session
job = Job(glue)
job.init(args["JOB_NAME"], args)

BUCKET = "orion-eafit-taller2-2026"

# 1. Leer los 11 archivos de tokens (JSON Lines comprimido)
tokens = spark.read.json(f"s3://{BUCKET}/entrada/tokens/")

# 2. Aplicar las reglas R1, R2 y R3
validos, rechazados = limpiar(tokens)

# 3. Contar
total = tokens.count()
n_validos = validos.count()
por_motivo = {
    fila["motivo_rechazo"]: fila["filas"]
    for fila in rechazados.groupBy("motivo_rechazo").agg({"*": "count"})
    .withColumnRenamed("count(1)", "filas").collect()
}
n_rechazados = sum(por_motivo.values())

resultado = (
    [("total_entrada", total), ("validas", n_validos)]
    + sorted(por_motivo.items())
    + [("diferencia_debe_ser_0", total - n_validos - n_rechazados)]
)

for concepto, filas in resultado:
    print(f"{concepto}: {filas:,}")

# 4. Guardar los conteos en S3 para verlos sin buscar en los logs
(
    spark.createDataFrame(resultado, ["concepto", "filas"])
    .coalesce(1)
    .write.mode("overwrite")
    .option("header", True)
    .csv(f"s3://{BUCKET}/pruebas/limpieza_conteos/")
)

job.commit()