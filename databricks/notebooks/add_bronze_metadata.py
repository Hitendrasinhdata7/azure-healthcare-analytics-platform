# Databricks notebook source
# MAGIC %md
# MAGIC # Add Bronze Metadata
# MAGIC Stamps raw Parquet files with audit columns and converts to Delta format.

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from delta.tables import DeltaTable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("add_bronze_metadata")

spark = SparkSession.builder.appName("AddBronzeMetadata").getOrCreate()

STORAGE_ACCOUNT  = spark.conf.get("pipeline.storage_account", "adlshealthcaredev")
DATASET          = spark.conf.get("pipeline.dataset", "patients")
PIPELINE_RUN_ID  = spark.conf.get("pipeline.run_id", "local-run")
INGESTION_TS     = spark.conf.get("pipeline.ingestion_ts", "")

RAW_PATH    = f"abfss://raw@{STORAGE_ACCOUNT}.dfs.core.windows.net/{DATASET}.csv"
BRONZE_PATH = f"abfss://bronze@{STORAGE_ACCOUNT}.dfs.core.windows.net/{DATASET}"

logger.info(f"Processing dataset: {DATASET}")
logger.info(f"Source: {RAW_PATH}")
logger.info(f"Destination: {BRONZE_PATH}")

# Read raw CSV
df = (spark.read
      .option("header", "true")
      .option("inferSchema", "true")
      .option("multiLine", "true")
      .option("escape", '"')
      .csv(RAW_PATH))

logger.info(f"Raw row count: {df.count()}")

# Add audit/metadata columns
df = (df
    .withColumn("_ingestion_timestamp", F.to_timestamp(F.lit(INGESTION_TS)) if INGESTION_TS else F.current_timestamp())
    .withColumn("_source_system",       F.lit("NHS_SYNTHETIC"))
    .withColumn("_source_file",         F.lit(RAW_PATH))
    .withColumn("_pipeline_run_id",     F.lit(PIPELINE_RUN_ID))
    .withColumn("_bronze_load_date",    F.current_date())
    .withColumn("_dataset_name",        F.lit(DATASET))
)

# Write to Bronze as Delta (append — immutable)
if DeltaTable.isDeltaTable(spark, BRONZE_PATH):
    df.write.format("delta").mode("append").save(BRONZE_PATH)
else:
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(BRONZE_PATH)

final_count = spark.read.format("delta").load(BRONZE_PATH).count()
logger.info(f"Bronze table row count after load: {final_count}")

print(f"✅ Bronze metadata added for [{DATASET}] — {final_count} rows total")
