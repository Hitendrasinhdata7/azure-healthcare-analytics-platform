# Databricks notebook source
# MAGIC %md
# MAGIC # Data Quality Framework
# MAGIC ## Azure Healthcare Analytics Platform

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger("data_quality")
spark = SparkSession.builder.appName("DataQuality").getOrCreate()

STORAGE_ACCOUNT = spark.conf.get("pipeline.storage_account", "adlshealthcaredev")
SILVER_PATH = f"abfss://silver@{STORAGE_ACCOUNT}.dfs.core.windows.net"
GOLD_PATH   = f"abfss://gold@{STORAGE_ACCOUNT}.dfs.core.windows.net"
DQ_LOG_PATH = f"abfss://monitoring@{STORAGE_ACCOUNT}.dfs.core.windows.net/dq_results"

# COMMAND ----------

@dataclass
class DQResult:
    table: str
    rule_name: str
    dimension: str          # completeness / accuracy / uniqueness / validity
    total_rows: int
    failed_rows: int
    passed: bool
    threshold: float
    actual_rate: float
    run_ts: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return self.__dict__

# COMMAND ----------

class DataQualityEngine:
    def __init__(self, df: DataFrame, table_name: str, threshold: float = 0.95):
        self.df = df.cache()
        self.table_name = table_name
        self.threshold = threshold
        self.total = self.df.count()
        self.results: List[DQResult] = []

    def check_not_null(self, column: str) -> "DataQualityEngine":
        nulls = self.df.filter(F.col(column).isNull()).count()
        rate = 1 - (nulls / max(self.total, 1))
        self.results.append(DQResult(
            table=self.table_name,
            rule_name=f"{column}_not_null",
            dimension="completeness",
            total_rows=self.total,
            failed_rows=nulls,
            passed=rate >= self.threshold,
            threshold=self.threshold,
            actual_rate=round(rate, 4),
        ))
        return self

    def check_unique(self, column: str) -> "DataQualityEngine":
        dupes = self.total - self.df.select(column).distinct().count()
        rate = 1 - (dupes / max(self.total, 1))
        self.results.append(DQResult(
            table=self.table_name,
            rule_name=f"{column}_unique",
            dimension="uniqueness",
            total_rows=self.total,
            failed_rows=dupes,
            passed=rate >= self.threshold,
            threshold=self.threshold,
            actual_rate=round(rate, 4),
        ))
        return self

    def check_in_set(self, column: str, valid_values: list) -> "DataQualityEngine":
        invalid = self.df.filter(
            F.col(column).isNotNull() & ~F.col(column).isin(valid_values)
        ).count()
        rate = 1 - (invalid / max(self.total, 1))
        self.results.append(DQResult(
            table=self.table_name,
            rule_name=f"{column}_valid_values",
            dimension="validity",
            total_rows=self.total,
            failed_rows=invalid,
            passed=rate >= self.threshold,
            threshold=self.threshold,
            actual_rate=round(rate, 4),
        ))
        return self

    def check_positive(self, column: str) -> "DataQualityEngine":
        neg = self.df.filter(
            F.col(column).isNotNull() & (F.col(column) <= 0)
        ).count()
        rate = 1 - (neg / max(self.total, 1))
        self.results.append(DQResult(
            table=self.table_name,
            rule_name=f"{column}_positive",
            dimension="accuracy",
            total_rows=self.total,
            failed_rows=neg,
            passed=rate >= self.threshold,
            threshold=self.threshold,
            actual_rate=round(rate, 4),
        ))
        return self

    def check_date_not_future(self, column: str) -> "DataQualityEngine":
        future = self.df.filter(
            F.col(column).isNotNull() & (F.col(column) > F.current_date())
        ).count()
        rate = 1 - (future / max(self.total, 1))
        self.results.append(DQResult(
            table=self.table_name,
            rule_name=f"{column}_not_future",
            dimension="accuracy",
            total_rows=self.total,
            failed_rows=future,
            passed=rate >= self.threshold,
            threshold=self.threshold,
            actual_rate=round(rate, 4),
        ))
        return self

    def check_referential_integrity(self, fk_col: str, parent_df: DataFrame, pk_col: str) -> "DataQualityEngine":
        parent_keys = parent_df.select(pk_col).distinct()
        orphans = self.df.join(parent_keys, self.df[fk_col] == parent_keys[pk_col], "left_anti").count()
        rate = 1 - (orphans / max(self.total, 1))
        self.results.append(DQResult(
            table=self.table_name,
            rule_name=f"{fk_col}_referential_integrity",
            dimension="accuracy",
            total_rows=self.total,
            failed_rows=orphans,
            passed=rate >= self.threshold,
            threshold=self.threshold,
            actual_rate=round(rate, 4),
        ))
        return self

    def summary(self) -> DataFrame:
        rows = [r.to_dict() for r in self.results]
        df_result = spark.createDataFrame(rows)
        return df_result

    def print_summary(self):
        print(f"\n{'='*70}")
        print(f"  DQ REPORT: {self.table_name}  |  {self.total} total rows")
        print(f"{'='*70}")
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        for r in self.results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            print(f"  {status}  {r.rule_name:<45} rate={r.actual_rate:.2%}  failed={r.failed_rows}")
        print(f"{'='*70}")
        print(f"  Summary: {passed} passed, {failed} failed out of {len(self.results)} rules")
        return failed == 0

# COMMAND ----------
# MAGIC %md ## Run DQ Checks

def run_all_dq_checks():
    patients   = spark.read.format("delta").load(f"{SILVER_PATH}/patients")
    appts      = spark.read.format("delta").load(f"{SILVER_PATH}/appointments")
    imaging    = spark.read.format("delta").load(f"{SILVER_PATH}/imaging")
    procedures = spark.read.format("delta").load(f"{SILVER_PATH}/procedures")
    referrals  = spark.read.format("delta").load(f"{SILVER_PATH}/referrals")

    all_results = []

    # --- Patients ---
    eng = DataQualityEngine(patients, "silver_patients", threshold=0.95)
    eng.check_not_null("patient_id") \
       .check_unique("patient_id") \
       .check_not_null("gender") \
       .check_in_set("gender", ["Male", "Female", "Other"]) \
       .check_not_null("date_of_birth") \
       .check_date_not_future("date_of_birth")
    all_passed = eng.print_summary()
    all_results.append(eng.summary())

    # --- Appointments ---
    eng = DataQualityEngine(appts, "silver_appointments", threshold=0.95)
    eng.check_not_null("appointment_id") \
       .check_unique("appointment_id") \
       .check_not_null("patient_id") \
       .check_not_null("appointment_date") \
       .check_in_set("status", ["Attended", "Dna", "Cancelled", "Booked"]) \
       .check_referential_integrity("patient_id", patients, "patient_id")
    eng.print_summary()
    all_results.append(eng.summary())

    # --- Imaging ---
    eng = DataQualityEngine(imaging, "silver_imaging", threshold=0.95)
    eng.check_not_null("imaging_id") \
       .check_unique("imaging_id") \
       .check_not_null("patient_id") \
       .check_in_set("modality", ["MRI","CT","X-RAY","ULTRASOUND","PET"]) \
       .check_referential_integrity("patient_id", patients, "patient_id")
    eng.print_summary()
    all_results.append(eng.summary())

    # --- Procedures ---
    eng = DataQualityEngine(procedures, "silver_procedures", threshold=0.95)
    eng.check_not_null("procedure_id") \
       .check_unique("procedure_id") \
       .check_not_null("patient_id") \
       .check_not_null("cost") \
       .check_positive("cost")
    eng.print_summary()
    all_results.append(eng.summary())

    # --- Referrals ---
    eng = DataQualityEngine(referrals, "silver_referrals", threshold=0.95)
    eng.check_not_null("referral_id") \
       .check_unique("referral_id") \
       .check_not_null("patient_id") \
       .check_not_null("referral_date") \
       .check_referential_integrity("patient_id", patients, "patient_id")
    eng.print_summary()
    all_results.append(eng.summary())

    # Write DQ results to monitoring store
    from functools import reduce
    from pyspark.sql import DataFrame as DF
    combined = reduce(DF.union, all_results)
    combined.write.format("delta").mode("append").save(DQ_LOG_PATH)
    print(f"\nDQ results written to {DQ_LOG_PATH}")
    return combined

dq_results = run_all_dq_checks()
display(dq_results)
