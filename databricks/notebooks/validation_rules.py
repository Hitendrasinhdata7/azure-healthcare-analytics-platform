"""
validation_rules.py
Reusable validation rule definitions for the Healthcare Analytics Platform.
Import this module in Databricks notebooks or unit tests.

Designed to work both in Databricks (with PySpark) and locally (pure Python).
"""

try:
    from pyspark.sql import functions as F, Column
    _SPARK_AVAILABLE = True
except ImportError:
    _SPARK_AVAILABLE = False

# ── Pure-Python rule constants (used by unit/DQ tests) ───────

VALID_GENDERS    = {"Male", "Female", "Other"}
VALID_STATUSES   = {"Attended", "Dna", "Cancelled", "Booked"}
VALID_MODALITIES = {"MRI", "CT", "X-RAY", "ULTRASOUND", "PET"}
MIN_COST         = 1.0
MAX_COST         = 500_000.0
VALID_SPECIALITIES = {
    "Cardiology","Neurology","Oncology","Orthopaedics","Gastroenterology",
    "Dermatology","Endocrinology","Haematology","Nephrology","Rheumatology",
}

# ── Column-level Spark rules (only if PySpark available) ──────

if _SPARK_AVAILABLE:
    def rule_not_null(col_name: str) -> "Column":
        return F.col(col_name).isNotNull()

    def rule_positive(col_name: str) -> "Column":
        return F.col(col_name) > 0

    def rule_in_set(col_name: str, valid_values: list) -> "Column":
        return F.col(col_name).isin(valid_values)

    def rule_date_not_future(col_name: str) -> "Column":
        return F.col(col_name) <= F.current_date()

    def rule_string_length(col_name: str, min_len: int = 1, max_len: int = 255) -> "Column":
        return (F.length(F.col(col_name)) >= min_len) & (F.length(F.col(col_name)) <= max_len)

    def rule_regex_match(col_name: str, pattern: str) -> "Column":
        return F.col(col_name).rlike(pattern)

    def rule_date_range(col_name: str, min_date: str, max_date: str) -> "Column":
        return (F.col(col_name) >= F.lit(min_date)) & (F.col(col_name) <= F.lit(max_date))

    def rule_numeric_range(col_name: str, min_val: float, max_val: float) -> "Column":
        return (F.col(col_name) >= min_val) & (F.col(col_name) <= max_val)

    # ── Table-level rule sets ─────────────────────────────────
    PATIENT_RULES = {
        "patient_id_not_null":  rule_not_null("patient_id"),
        "gender_valid":         rule_in_set("gender", list(VALID_GENDERS)),
        "dob_not_null":         rule_not_null("date_of_birth"),
        "dob_not_future":       rule_date_not_future("date_of_birth"),
        "dob_range":            rule_date_range("date_of_birth", "1900-01-01", "2015-12-31"),
        "postcode_not_null":    rule_not_null("postcode"),
        "postcode_format":      rule_regex_match("postcode", r"^[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}$"),
    }

    APPOINTMENT_RULES = {
        "appointment_id_not_null":   rule_not_null("appointment_id"),
        "patient_id_not_null":       rule_not_null("patient_id"),
        "appointment_date_not_null": rule_not_null("appointment_date"),
        "status_valid":              rule_in_set("status", list(VALID_STATUSES)),
        "department_not_null":       rule_not_null("department"),
    }

    IMAGING_RULES = {
        "imaging_id_not_null":  rule_not_null("imaging_id"),
        "patient_id_not_null":  rule_not_null("patient_id"),
        "modality_valid":       rule_in_set("modality", list(VALID_MODALITIES)),
        "scan_date_not_null":   rule_not_null("scan_date"),
        "scan_date_not_future": rule_date_not_future("scan_date"),
    }

    PROCEDURE_RULES = {
        "procedure_id_not_null": rule_not_null("procedure_id"),
        "patient_id_not_null":   rule_not_null("patient_id"),
        "cost_not_null":         rule_not_null("cost"),
        "cost_positive":         rule_positive("cost"),
        "cost_range":            rule_numeric_range("cost", MIN_COST, MAX_COST),
    }

    REFERRAL_RULES = {
        "referral_id_not_null":   rule_not_null("referral_id"),
        "patient_id_not_null":    rule_not_null("patient_id"),
        "referral_date_not_null": rule_not_null("referral_date"),
        "speciality_not_null":    rule_not_null("speciality"),
    }

else:
    # Fallback stubs for local/unit-test usage (no Spark)
    def _stub(*args, **kwargs):
        return None

    rule_not_null = rule_positive = rule_in_set = _stub
    rule_date_not_future = rule_string_length = rule_regex_match = _stub
    rule_date_range = rule_numeric_range = _stub

    PATIENT_RULES = {
        "patient_id_not_null": None,
        "gender_valid":        None,
        "dob_not_null":        None,
        "dob_not_future":      None,
        "dob_range":           None,
        "postcode_not_null":   None,
        "postcode_format":     None,
    }
    APPOINTMENT_RULES = {
        "appointment_id_not_null":   None,
        "patient_id_not_null":       None,
        "appointment_date_not_null": None,
        "status_valid":              None,
        "department_not_null":       None,
    }
    IMAGING_RULES = {
        "imaging_id_not_null":  None,
        "patient_id_not_null":  None,
        "modality_valid":       None,
        "scan_date_not_null":   None,
        "scan_date_not_future": None,
    }
    PROCEDURE_RULES = {
        "procedure_id_not_null": None,
        "patient_id_not_null":   None,
        "cost_not_null":         None,
        "cost_positive":         None,
        "cost_range":            None,
    }
    REFERRAL_RULES = {
        "referral_id_not_null":   None,
        "patient_id_not_null":    None,
        "referral_date_not_null": None,
        "speciality_not_null":    None,
    }

ALL_RULES = {
    "patients":     PATIENT_RULES,
    "appointments": APPOINTMENT_RULES,
    "imaging":      IMAGING_RULES,
    "procedures":   PROCEDURE_RULES,
    "referrals":    REFERRAL_RULES,
}
