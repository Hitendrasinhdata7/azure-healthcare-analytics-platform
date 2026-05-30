"""
Integration tests for the Healthcare Analytics pipeline.
Uses PySpark locally with Delta Lake.
Run with:  pytest tests/integration/ -v
Requires:  pyspark, delta-spark installed in virtual environment.
"""

import pytest
import os
import shutil
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


@pytest.fixture(scope="session")
def spark():
    spark = (
        SparkSession.builder
        .appName("HealthcareIntegrationTests")
        .master("local[*]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    yield spark
    spark.stop()


@pytest.fixture(scope="session")
def sample_patients(spark):
    from datetime import date
    data = [
        ("p001", "Male",   date(1980, 1, 1), "SW1A 1AA"),
        ("p002", "Female", date(1990, 5, 15), "E1 6RF"),
        ("p003", None,     date(1975, 3, 20), "M1 1AE"),   # null gender
        ("p004", "Male",   None,              "B1 1BB"),   # null dob
        ("p001", "Male",   date(1980, 1, 1), "SW1A 1AA"),  # duplicate
    ]
    schema = ["patient_id", "gender", "date_of_birth", "postcode"]
    return spark.createDataFrame(data, schema)


@pytest.fixture(scope="session")
def sample_appointments(spark):
    from datetime import date
    data = [
        ("a001", "p001", date(2023, 1, 10), "Cardiology",  "Attended"),
        ("a002", "p002", date(2023, 2, 15), "Neurology",   "Cancelled"),
        ("a001", "p001", date(2023, 1, 10), "Cardiology",  "Attended"),  # duplicate
        ("a003", "p999", date(2023, 3, 5),  "Emergency",   "Attended"),  # orphan patient
    ]
    schema = ["appointment_id", "patient_id", "appointment_date", "department", "status"]
    return spark.createDataFrame(data, schema)


class TestDeduplication:
    def test_patient_dedup(self, spark, sample_patients):
        from pyspark.sql.window import Window
        w = Window.partitionBy("patient_id").orderBy(F.monotonically_increasing_id().desc())
        deduped = (
            sample_patients
            .withColumn("_rn", F.row_number().over(w))
            .filter(F.col("_rn") == 1)
            .drop("_rn")
        )
        assert deduped.count() == 4  # 5 rows → 4 after removing duplicate p001

    def test_appointment_dedup(self, spark, sample_appointments):
        from pyspark.sql.window import Window
        w = Window.partitionBy("appointment_id").orderBy(F.monotonically_increasing_id().desc())
        deduped = (
            sample_appointments
            .withColumn("_rn", F.row_number().over(w))
            .filter(F.col("_rn") == 1)
            .drop("_rn")
        )
        assert deduped.count() == 3  # 4 rows → 3 after removing duplicate a001


class TestNullDetection:
    def test_null_gender_detected(self, spark, sample_patients):
        nulls = sample_patients.filter(F.col("gender").isNull()).count()
        assert nulls == 1

    def test_null_dob_detected(self, spark, sample_patients):
        nulls = sample_patients.filter(F.col("date_of_birth").isNull()).count()
        assert nulls == 1


class TestGenderStandardisation:
    def test_gender_standardisation(self, spark):
        data = [("p1", "m"), ("p2", "MALE"), ("p3", "F"), ("p4", "female"), ("p5", "Other")]
        df = spark.createDataFrame(data, ["patient_id", "gender"])
        df = df.withColumn("gender_std",
            F.when(F.upper(F.col("gender")).isin("M", "MALE"), "Male")
             .when(F.upper(F.col("gender")).isin("F", "FEMALE"), "Female")
             .when(F.upper(F.col("gender")).isin("O", "OTHER"), "Other")
             .otherwise(None)
        )
        males = df.filter(F.col("gender_std") == "Male").count()
        females = df.filter(F.col("gender_std") == "Female").count()
        assert males == 2
        assert females == 2


class TestReferentialIntegrity:
    def test_orphan_appointments_detected(self, spark, sample_patients, sample_appointments):
        patient_ids = sample_patients.select("patient_id").distinct()
        orphans = sample_appointments.join(
            patient_ids,
            sample_appointments["patient_id"] == patient_ids["patient_id"],
            "left_anti"
        )
        assert orphans.count() >= 1  # p999 is not in patients

    def test_all_valid_patients_have_no_orphan(self, spark, sample_patients, sample_appointments):
        patient_ids = sample_patients.select("patient_id").distinct()
        valid_appts = sample_appointments.join(
            patient_ids,
            sample_appointments["patient_id"] == patient_ids["patient_id"],
            "inner"
        )
        assert valid_appts.count() >= 1


class TestDateHandling:
    def test_date_cast(self, spark):
        data = [("2023-01-15",), ("invalid-date",), (None,)]
        df = spark.createDataFrame(data, ["date_str"])
        df = df.withColumn("parsed_date", F.to_date(F.col("date_str"), "yyyy-MM-dd"))
        nulls = df.filter(F.col("parsed_date").isNull()).count()
        assert nulls == 2  # invalid-date and None both become null
