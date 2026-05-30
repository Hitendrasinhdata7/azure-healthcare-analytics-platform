# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze → Silver Layer
# MAGIC ## Azure Healthcare Analytics Platform
# MAGIC Cleanses, standardises, deduplicates, and validates raw Bronze data into Silver Delta tables.

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from delta.tables import DeltaTable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bronze_to_silver")

spark = SparkSession.builder.appName("BronzeToSilver").getOrCreate()
spark.conf.set("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
spark.conf.set("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")

# COMMAND ----------
# MAGIC %md ## Configuration

STORAGE_ACCOUNT = spark.conf.get("pipeline.storage_account", "adlshealthcaredev")
BRONZE_PATH     = f"abfss://bronze@{STORAGE_ACCOUNT}.dfs.core.windows.net"
SILVER_PATH     = f"abfss://silver@{STORAGE_ACCOUNT}.dfs.core.windows.net"
CHECKPOINT_PATH = f"abfss://checkpoints@{STORAGE_ACCOUNT}.dfs.core.windows.net/silver"

INGESTION_TS = F.current_timestamp()

# COMMAND ----------
# MAGIC %md ## Helper: audit columns

def add_audit_columns(df, layer="silver"):
    return (df
        .withColumn("_ingestion_timestamp", INGESTION_TS)
        .withColumn("_source_layer", F.lit(layer))
        .withColumn("_pipeline_run_id", F.lit(
            spark.conf.get("pipeline.run_id", "local-run")))
    )

# COMMAND ----------
# MAGIC %md ## 1. Patients

def process_patients():
    logger.info("Processing patients: Bronze → Silver")

    df = spark.read.format("delta").load(f"{BRONZE_PATH}/patients")

    # Deduplicate: keep latest record per patient_id
    window_spec = Window.partitionBy("patient_id").orderBy(F.col("_ingestion_timestamp").desc())
    df = (df
        .withColumn("_row_num", F.row_number().over(window_spec))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    # Standardise gender
    df = df.withColumn("gender",
        F.when(F.upper(F.col("gender")).isin("M", "MALE"), "Male")
         .when(F.upper(F.col("gender")).isin("F", "FEMALE"), "Female")
         .when(F.upper(F.col("gender")).isin("O", "OTHER"), "Other")
         .otherwise(F.lit(None).cast("string"))
    )

    # Cast & validate date_of_birth
    df = df.withColumn("date_of_birth", F.to_date(F.col("date_of_birth"), "yyyy-MM-dd"))

    # Standardise postcode: uppercase, trim
    df = df.withColumn("postcode", F.upper(F.trim(F.col("postcode"))))

    # Data quality flags
    df = (df
        .withColumn("dq_patient_id_null",    F.col("patient_id").isNull().cast("int"))
        .withColumn("dq_gender_null",        F.col("gender").isNull().cast("int"))
        .withColumn("dq_dob_null",           F.col("date_of_birth").isNull().cast("int"))
        .withColumn("dq_postcode_null",      F.col("postcode").isNull().cast("int"))
        .withColumn("dq_dob_future",
            (F.col("date_of_birth") > F.current_date()).cast("int"))
    )

    df = add_audit_columns(df)

    # MERGE into Silver Delta table
    silver_table_path = f"{SILVER_PATH}/patients"
    if DeltaTable.isDeltaTable(spark, silver_table_path):
        silver_tbl = DeltaTable.forPath(spark, silver_table_path)
        silver_tbl.alias("target").merge(
            df.alias("source"),
            "target.patient_id = source.patient_id"
        ).whenMatchedUpdateAll() \
         .whenNotMatchedInsertAll() \
         .execute()
    else:
        df.write.format("delta") \
            .partitionBy("gender") \
            .mode("overwrite") \
            .option("overwriteSchema", "true") \
            .save(silver_table_path)

    count = spark.read.format("delta").load(silver_table_path).count()
    logger.info(f"Patients Silver count: {count}")
    return count

# COMMAND ----------
# MAGIC %md ## 2. Appointments

def process_appointments():
    logger.info("Processing appointments: Bronze → Silver")

    df = spark.read.format("delta").load(f"{BRONZE_PATH}/appointments")

    # Deduplicate by appointment_id + appointment_date (keep latest)
    window_spec = Window.partitionBy("appointment_id").orderBy(F.col("_ingestion_timestamp").desc())
    df = (df
        .withColumn("_row_num", F.row_number().over(window_spec))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    # Standardise status
    df = df.withColumn("status",
        F.initcap(F.trim(F.col("status")))
    )

    # Standardise department
    df = df.withColumn("department", F.initcap(F.trim(F.col("department"))))

    # Cast date
    df = df.withColumn("appointment_date", F.to_date(F.col("appointment_date"), "yyyy-MM-dd"))

    # Derived: appointment year/month for partitioning
    df = (df
        .withColumn("appointment_year",  F.year(F.col("appointment_date")))
        .withColumn("appointment_month", F.month(F.col("appointment_date")))
    )

    # DQ flags
    df = (df
        .withColumn("dq_appointment_id_null", F.col("appointment_id").isNull().cast("int"))
        .withColumn("dq_patient_id_null",     F.col("patient_id").isNull().cast("int"))
        .withColumn("dq_date_null",           F.col("appointment_date").isNull().cast("int"))
        .withColumn("dq_future_appointment",
            (F.col("appointment_date") > F.current_date()).cast("int"))
    )

    df = add_audit_columns(df)

    silver_table_path = f"{SILVER_PATH}/appointments"
    if DeltaTable.isDeltaTable(spark, silver_table_path):
        silver_tbl = DeltaTable.forPath(spark, silver_table_path)
        silver_tbl.alias("target").merge(
            df.alias("source"),
            "target.appointment_id = source.appointment_id"
        ).whenMatchedUpdateAll() \
         .whenNotMatchedInsertAll() \
         .execute()
    else:
        df.write.format("delta") \
            .partitionBy("appointment_year", "appointment_month") \
            .mode("overwrite") \
            .option("overwriteSchema", "true") \
            .save(silver_table_path)

    count = spark.read.format("delta").load(silver_table_path).count()
    logger.info(f"Appointments Silver count: {count}")
    return count

# COMMAND ----------
# MAGIC %md ## 3. Imaging

def process_imaging():
    logger.info("Processing imaging: Bronze → Silver")

    df = spark.read.format("delta").load(f"{BRONZE_PATH}/imaging")

    # Deduplicate
    window_spec = Window.partitionBy("imaging_id").orderBy(F.col("_ingestion_timestamp").desc())
    df = (df
        .withColumn("_row_num", F.row_number().over(window_spec))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    df = df.withColumn("modality",  F.upper(F.trim(F.col("modality"))))
    df = df.withColumn("scan_date", F.to_date(F.col("scan_date"), "yyyy-MM-dd"))
    df = df.withColumn("scan_year", F.year(F.col("scan_date")))

    df = (df
        .withColumn("dq_imaging_id_null",   F.col("imaging_id").isNull().cast("int"))
        .withColumn("dq_patient_id_null",   F.col("patient_id").isNull().cast("int"))
        .withColumn("dq_scan_date_null",    F.col("scan_date").isNull().cast("int"))
        .withColumn("dq_invalid_modality",
            (~F.col("modality").isin("MRI","CT","X-RAY","ULTRASOUND","PET")).cast("int"))
    )

    df = add_audit_columns(df)

    silver_table_path = f"{SILVER_PATH}/imaging"
    if DeltaTable.isDeltaTable(spark, silver_table_path):
        silver_tbl = DeltaTable.forPath(spark, silver_table_path)
        silver_tbl.alias("target").merge(
            df.alias("source"),
            "target.imaging_id = source.imaging_id"
        ).whenMatchedUpdateAll() \
         .whenNotMatchedInsertAll() \
         .execute()
    else:
        df.write.format("delta") \
            .partitionBy("modality") \
            .mode("overwrite") \
            .option("overwriteSchema", "true") \
            .save(silver_table_path)

    count = spark.read.format("delta").load(silver_table_path).count()
    logger.info(f"Imaging Silver count: {count}")
    return count

# COMMAND ----------
# MAGIC %md ## 4. Procedures

def process_procedures():
    logger.info("Processing procedures: Bronze → Silver")

    df = spark.read.format("delta").load(f"{BRONZE_PATH}/procedures")

    window_spec = Window.partitionBy("procedure_id").orderBy(F.col("_ingestion_timestamp").desc())
    df = (df
        .withColumn("_row_num", F.row_number().over(window_spec))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    df = df.withColumn("procedure_type", F.initcap(F.trim(F.col("procedure_type"))))
    df = df.withColumn("cost", F.col("cost").cast("double"))

    # Business rule: cost must be positive
    df = (df
        .withColumn("dq_null_cost",     F.col("cost").isNull().cast("int"))
        .withColumn("dq_negative_cost", (F.col("cost") < 0).cast("int"))
    )

    df = add_audit_columns(df)

    silver_table_path = f"{SILVER_PATH}/procedures"
    if DeltaTable.isDeltaTable(spark, silver_table_path):
        silver_tbl = DeltaTable.forPath(spark, silver_table_path)
        silver_tbl.alias("target").merge(
            df.alias("source"),
            "target.procedure_id = source.procedure_id"
        ).whenMatchedUpdateAll() \
         .whenNotMatchedInsertAll() \
         .execute()
    else:
        df.write.format("delta") \
            .mode("overwrite") \
            .option("overwriteSchema", "true") \
            .save(silver_table_path)

    count = spark.read.format("delta").load(silver_table_path).count()
    logger.info(f"Procedures Silver count: {count}")
    return count

# COMMAND ----------
# MAGIC %md ## 5. Referrals

def process_referrals():
    logger.info("Processing referrals: Bronze → Silver")

    df = spark.read.format("delta").load(f"{BRONZE_PATH}/referrals")

    window_spec = Window.partitionBy("referral_id").orderBy(F.col("_ingestion_timestamp").desc())
    df = (df
        .withColumn("_row_num", F.row_number().over(window_spec))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    df = df.withColumn("speciality",    F.initcap(F.trim(F.col("speciality"))))
    df = df.withColumn("referral_date", F.to_date(F.col("referral_date"), "yyyy-MM-dd"))
    df = df.withColumn("referral_year", F.year(F.col("referral_date")))

    df = (df
        .withColumn("dq_referral_id_null",  F.col("referral_id").isNull().cast("int"))
        .withColumn("dq_patient_id_null",   F.col("patient_id").isNull().cast("int"))
        .withColumn("dq_date_null",         F.col("referral_date").isNull().cast("int"))
    )

    df = add_audit_columns(df)

    silver_table_path = f"{SILVER_PATH}/referrals"
    if DeltaTable.isDeltaTable(spark, silver_table_path):
        silver_tbl = DeltaTable.forPath(spark, silver_table_path)
        silver_tbl.alias("target").merge(
            df.alias("source"),
            "target.referral_id = source.referral_id"
        ).whenMatchedUpdateAll() \
         .whenNotMatchedInsertAll() \
         .execute()
    else:
        df.write.format("delta") \
            .partitionBy("referral_year") \
            .mode("overwrite") \
            .option("overwriteSchema", "true") \
            .save(silver_table_path)

    count = spark.read.format("delta").load(silver_table_path).count()
    logger.info(f"Referrals Silver count: {count}")
    return count

# COMMAND ----------
# MAGIC %md ## Run All

results = {
    "patients":     process_patients(),
    "appointments": process_appointments(),
    "imaging":      process_imaging(),
    "procedures":   process_procedures(),
    "referrals":    process_referrals(),
}

print("\n=== Bronze → Silver Complete ===")
for k, v in results.items():
    print(f"  {k:<20} {v:>8} rows in Silver")

# COMMAND ----------
# MAGIC %md ## Delta Optimise Silver Tables

for table in ["patients", "appointments", "imaging", "procedures", "referrals"]:
    spark.sql(f"OPTIMIZE delta.`{SILVER_PATH}/{table}` ZORDER BY (patient_id)")
    logger.info(f"Optimised: {table}")

print("Delta OPTIMIZE complete.")
