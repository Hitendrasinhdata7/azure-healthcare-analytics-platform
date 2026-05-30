# Databricks notebook source
# MAGIC %md
# MAGIC # Silver → Gold Layer
# MAGIC ## Azure Healthcare Analytics Platform
# MAGIC Builds business-ready Fact & Dimension tables and KPI aggregates in the Gold layer.

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from delta.tables import DeltaTable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("silver_to_gold")

spark = SparkSession.builder.appName("SilverToGold").getOrCreate()

STORAGE_ACCOUNT = spark.conf.get("pipeline.storage_account", "adlshealthcaredev")
SILVER_PATH = f"abfss://silver@{STORAGE_ACCOUNT}.dfs.core.windows.net"
GOLD_PATH   = f"abfss://gold@{STORAGE_ACCOUNT}.dfs.core.windows.net"

# COMMAND ----------
# MAGIC %md ## Dim: DimPatient

def build_dim_patient():
    df = spark.read.format("delta").load(f"{SILVER_PATH}/patients") \
        .filter(F.col("dq_patient_id_null") == 0)

    df = df.withColumn("age",
        F.floor(F.datediff(F.current_date(), F.col("date_of_birth")) / 365.25)
    ).withColumn("age_band",
        F.when(F.col("age") < 18,  "0-17")
         .when(F.col("age") < 35,  "18-34")
         .when(F.col("age") < 50,  "35-49")
         .when(F.col("age") < 65,  "50-64")
         .when(F.col("age") < 80,  "65-79")
         .otherwise("80+")
    ).select("patient_id", "gender", "date_of_birth", "postcode", "age", "age_band")

    _write_gold(df, "dim_patient", partition_by="age_band")
    logger.info(f"DimPatient: {df.count()} rows")

# COMMAND ----------
# MAGIC %md ## Dim: DimDepartment

def build_dim_department():
    appts = spark.read.format("delta").load(f"{SILVER_PATH}/appointments")
    df = appts.select("department").distinct() \
        .withColumn("department_key", F.monotonically_increasing_id()) \
        .withColumn("department_group",
            F.when(F.col("department").isin("Cardiology","Neurology","Oncology"), "Specialist")
             .when(F.col("department").isin("Emergency","General Surgery"), "Acute")
             .otherwise("Other")
        )
    _write_gold(df, "dim_department")
    logger.info(f"DimDepartment: {df.count()} rows")

# COMMAND ----------
# MAGIC %md ## Dim: DimDate

def build_dim_date():
    from pyspark.sql.types import StructType, StructField, DateType
    from datetime import date, timedelta

    dates = [date(2020, 1, 1) + timedelta(days=i) for i in range(365 * 6)]
    df = spark.createDataFrame([(d,) for d in dates], ["date_key"])
    df = (df
        .withColumn("year",       F.year("date_key"))
        .withColumn("quarter",    F.quarter("date_key"))
        .withColumn("month",      F.month("date_key"))
        .withColumn("month_name", F.date_format("date_key", "MMMM"))
        .withColumn("week",       F.weekofyear("date_key"))
        .withColumn("day_of_week",F.dayofweek("date_key"))
        .withColumn("day_name",   F.date_format("date_key", "EEEE"))
        .withColumn("is_weekend",
            F.col("day_of_week").isin(1, 7).cast("int"))
        .withColumn("financial_year",
            F.when(F.col("month") >= 4, F.concat(F.col("year"), F.lit("/"), (F.col("year")+1)))
             .otherwise(F.concat((F.col("year")-1), F.lit("/"), F.col("year")))
        )
    )
    _write_gold(df, "dim_date", partition_by="year")
    logger.info(f"DimDate: {df.count()} rows")

# COMMAND ----------
# MAGIC %md ## Fact: FactPatientActivity

def build_fact_patient_activity():
    appts     = spark.read.format("delta").load(f"{SILVER_PATH}/appointments")
    imaging   = spark.read.format("delta").load(f"{SILVER_PATH}/imaging")
    procedures= spark.read.format("delta").load(f"{SILVER_PATH}/procedures")
    referrals = spark.read.format("delta").load(f"{SILVER_PATH}/referrals")
    patients  = spark.read.format("delta").load(f"{SILVER_PATH}/patients")

    # Appointments as the base fact
    fact = appts.select(
        F.col("appointment_id").alias("activity_id"),
        F.lit("APPOINTMENT").alias("activity_type"),
        F.col("patient_id"),
        F.col("appointment_date").alias("activity_date"),
        F.col("department"),
        F.col("status"),
        F.lit(None).cast("double").alias("cost"),
        F.lit(None).cast("string").alias("modality"),
        F.lit(None).cast("string").alias("speciality"),
        F.col("appointment_year").alias("activity_year"),
        F.col("appointment_month").alias("activity_month"),
    )

    # Imaging
    img_fact = imaging.select(
        F.col("imaging_id").alias("activity_id"),
        F.lit("IMAGING").alias("activity_type"),
        F.col("patient_id"),
        F.col("scan_date").alias("activity_date"),
        F.lit(None).cast("string").alias("department"),
        F.lit(None).cast("string").alias("status"),
        F.lit(None).cast("double").alias("cost"),
        F.col("modality"),
        F.lit(None).cast("string").alias("speciality"),
        F.year(F.col("scan_date")).alias("activity_year"),
        F.month(F.col("scan_date")).alias("activity_month"),
    )

    # Procedures
    proc_fact = procedures.select(
        F.col("procedure_id").alias("activity_id"),
        F.lit("PROCEDURE").alias("activity_type"),
        F.col("patient_id"),
        F.lit(None).cast("date").alias("activity_date"),
        F.lit(None).cast("string").alias("department"),
        F.lit(None).cast("string").alias("status"),
        F.col("cost"),
        F.lit(None).cast("string").alias("modality"),
        F.lit(None).cast("string").alias("speciality"),
        F.lit(None).cast("int").alias("activity_year"),
        F.lit(None).cast("int").alias("activity_month"),
    )

    # Referrals
    ref_fact = referrals.select(
        F.col("referral_id").alias("activity_id"),
        F.lit("REFERRAL").alias("activity_type"),
        F.col("patient_id"),
        F.col("referral_date").alias("activity_date"),
        F.lit(None).cast("string").alias("department"),
        F.lit(None).cast("string").alias("status"),
        F.lit(None).cast("double").alias("cost"),
        F.lit(None).cast("string").alias("modality"),
        F.col("speciality"),
        F.col("referral_year").alias("activity_year"),
        F.month(F.col("referral_date")).alias("activity_month"),
    )

    union_fact = fact.union(img_fact).union(proc_fact).union(ref_fact)

    # Enrich with patient age_band
    dim_patient = spark.read.format("delta").load(f"{GOLD_PATH}/dim_patient") \
        .select("patient_id", "age_band", "gender")

    final_fact = union_fact.join(dim_patient, on="patient_id", how="left")

    # Row count per patient (window function)
    w = Window.partitionBy("patient_id")
    final_fact = final_fact.withColumn("total_activities_per_patient", F.count("activity_id").over(w))

    _write_gold(final_fact, "fact_patient_activity",
                partition_by=["activity_year", "activity_type"])
    logger.info(f"FactPatientActivity: {final_fact.count()} rows")

# COMMAND ----------
# MAGIC %md ## Gold KPI Views

def build_kpi_appointment_by_dept():
    df = spark.read.format("delta").load(f"{GOLD_PATH}/fact_patient_activity") \
        .filter(F.col("activity_type") == "APPOINTMENT") \
        .groupBy("department", "activity_year", "activity_month", "status") \
        .agg(
            F.count("activity_id").alias("appointment_count"),
            F.countDistinct("patient_id").alias("unique_patients")
        )
    _write_gold(df, "kpi_appointments_by_department")
    logger.info("KPI: appointments by department complete")

def build_kpi_procedure_costs():
    df = spark.read.format("delta").load(f"{GOLD_PATH}/fact_patient_activity") \
        .filter((F.col("activity_type") == "PROCEDURE") & F.col("cost").isNotNull()) \
        .groupBy("activity_year", "activity_month") \
        .agg(
            F.count("activity_id").alias("procedure_count"),
            F.sum("cost").alias("total_cost"),
            F.avg("cost").alias("avg_cost"),
            F.max("cost").alias("max_cost"),
        )
    _write_gold(df, "kpi_procedure_costs")
    logger.info("KPI: procedure costs complete")

def build_kpi_referral_trends():
    df = spark.read.format("delta").load(f"{GOLD_PATH}/fact_patient_activity") \
        .filter(F.col("activity_type") == "REFERRAL") \
        .groupBy("speciality", "activity_year", "activity_month") \
        .agg(
            F.count("activity_id").alias("referral_count"),
            F.countDistinct("patient_id").alias("unique_patients")
        )
    _write_gold(df, "kpi_referral_trends")
    logger.info("KPI: referral trends complete")

def build_kpi_imaging_utilisation():
    df = spark.read.format("delta").load(f"{GOLD_PATH}/fact_patient_activity") \
        .filter(F.col("activity_type") == "IMAGING") \
        .groupBy("modality", "activity_year", "activity_month") \
        .agg(
            F.count("activity_id").alias("scan_count"),
            F.countDistinct("patient_id").alias("unique_patients")
        )
    _write_gold(df, "kpi_imaging_utilisation")
    logger.info("KPI: imaging utilisation complete")

# COMMAND ----------

def _write_gold(df, table_name, partition_by=None):
    path = f"{GOLD_PATH}/{table_name}"
    writer = df.write.format("delta").mode("overwrite").option("overwriteSchema", "true")
    if partition_by:
        if isinstance(partition_by, list):
            writer = writer.partitionBy(*partition_by)
        else:
            writer = writer.partitionBy(partition_by)
    writer.save(path)

# COMMAND ----------
# MAGIC %md ## Execute All

build_dim_patient()
build_dim_department()
build_dim_date()
build_fact_patient_activity()
build_kpi_appointment_by_dept()
build_kpi_procedure_costs()
build_kpi_referral_trends()
build_kpi_imaging_utilisation()

print("\n=== Silver → Gold Complete ===")
for t in ["dim_patient","dim_department","dim_date",
          "fact_patient_activity",
          "kpi_appointments_by_department","kpi_procedure_costs",
          "kpi_referral_trends","kpi_imaging_utilisation"]:
    c = spark.read.format("delta").load(f"{GOLD_PATH}/{t}").count()
    print(f"  {t:<45} {c:>8} rows")

# COMMAND ----------
# MAGIC %md ## OPTIMIZE Gold Tables

for t in ["dim_patient","fact_patient_activity"]:
    spark.sql(f"OPTIMIZE delta.`{GOLD_PATH}/{t}` ZORDER BY (patient_id)")
print("Gold OPTIMIZE complete.")
