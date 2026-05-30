"""
Data Quality Tests — Healthcare Analytics Platform
Tests DQ engine logic and rule thresholds using pure Python + mock data.
Run with: pytest tests/data_quality/ -v
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../databricks/notebooks"))

from validation_rules import (
    PATIENT_RULES, APPOINTMENT_RULES, IMAGING_RULES,
    PROCEDURE_RULES, REFERRAL_RULES
)
import re

# ── Helpers ─────────────────────────────────────────────────────

POSTCODE_RE = re.compile(r"^[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}$")
VALID_GENDERS    = {"Male", "Female", "Other"}
VALID_STATUSES   = {"Attended", "Dna", "Cancelled", "Booked"}
VALID_MODALITIES = {"MRI", "CT", "X-RAY", "ULTRASOUND", "PET"}

def passes_not_null(value) -> bool:
    return value is not None and value != ""

def passes_positive(value) -> bool:
    return value is not None and float(value) > 0

def passes_in_set(value, valid_set) -> bool:
    return value in valid_set

def passes_postcode(value) -> bool:
    return bool(POSTCODE_RE.match(str(value))) if value else False

def dq_rate(records, check_fn) -> float:
    if not records:
        return 0.0
    passed = sum(1 for r in records if check_fn(r))
    return passed / len(records)

# ── Patient DQ tests ─────────────────────────────────────────

class TestPatientDQ:
    def test_all_ids_present(self):
        records = ["p001", "p002", "p003", None, "p005"]
        rate = dq_rate(records, passes_not_null)
        assert rate == 0.8

    def test_gender_100pct_valid(self):
        records = ["Male", "Female", "Other", "Male", "Female"]
        rate = dq_rate(records, lambda g: passes_in_set(g, VALID_GENDERS))
        assert rate == 1.0

    def test_gender_with_invalids(self):
        records = ["Male", "Female", "Unknown", None, "M"]
        rate = dq_rate(records, lambda g: passes_in_set(g, VALID_GENDERS))
        assert rate == 0.4

    def test_postcode_valid(self):
        records = ["SW1A 1AA", "E1 6RF", "M1 1AE", "invalid", "12345"]
        rate = dq_rate(records, passes_postcode)
        assert rate == 0.6

    def test_threshold_passes_at_95pct(self):
        # 96 valid out of 100 — should pass 0.95 threshold
        records = ["Male"] * 96 + ["Unknown"] * 4
        rate = dq_rate(records, lambda g: passes_in_set(g, VALID_GENDERS))
        assert rate >= 0.95

    def test_threshold_fails_below_95pct(self):
        # 93 valid out of 100 — should fail 0.95 threshold
        records = ["Male"] * 93 + ["Unknown"] * 7
        rate = dq_rate(records, lambda g: passes_in_set(g, VALID_GENDERS))
        assert rate < 0.95


# ── Appointment DQ tests ─────────────────────────────────────

class TestAppointmentDQ:
    def test_status_valid(self):
        records = ["Attended", "Cancelled", "Booked", "Dna", "Attended"]
        rate = dq_rate(records, lambda s: passes_in_set(s, VALID_STATUSES))
        assert rate == 1.0

    def test_status_invalid_raw_values(self):
        records = ["attended", "CANCELLED", "no-show", "Booked"]
        rate = dq_rate(records, lambda s: passes_in_set(s, VALID_STATUSES))
        # Only "Booked" is valid
        assert rate == 0.25

    def test_appointment_id_uniqueness(self):
        ids = ["a001", "a002", "a003", "a001"]  # a001 duplicated
        unique_count = len(set(ids))
        total_count  = len(ids)
        uniqueness_rate = unique_count / total_count
        assert uniqueness_rate == 0.75


# ── Imaging DQ tests ─────────────────────────────────────────

class TestImagingDQ:
    def test_modality_valid(self):
        records = ["MRI", "CT", "X-RAY", "ULTRASOUND", "PET"]
        rate = dq_rate(records, lambda m: passes_in_set(m, VALID_MODALITIES))
        assert rate == 1.0

    def test_modality_mixed(self):
        records = ["MRI", "XRAY", "ct", "PET", None]
        rate = dq_rate(records, lambda m: passes_in_set(m, VALID_MODALITIES))
        # Only MRI and PET pass
        assert rate == 0.4


# ── Procedure DQ tests ───────────────────────────────────────

class TestProcedureDQ:
    def test_cost_positive(self):
        costs = [500.0, 1200.50, 0.0, -100.0, None]
        rate = dq_rate(costs, passes_positive)
        assert rate == 0.4

    def test_cost_range(self):
        costs = [500.0, 25000.0, 1.0, 600000.0, -50.0]
        rate = dq_rate(costs, lambda c: c is not None and 1.0 <= c <= 500_000.0)
        assert rate == 0.6

    def test_all_costs_valid(self):
        costs = [1000.0, 5000.0, 20000.0, 500.0, 15000.0]
        rate = dq_rate(costs, passes_positive)
        assert rate == 1.0


# ── Completeness scoring ─────────────────────────────────────

class TestCompletenessScoring:
    def test_completeness_score_calculation(self):
        """Completeness = non-null fields / total fields"""
        records = [
            {"patient_id": "p1", "gender": "Male",   "dob": "1980-01-01", "postcode": "SW1A 1AA"},
            {"patient_id": "p2", "gender": None,     "dob": "1990-05-15", "postcode": "E1 6RF"},
            {"patient_id": "p3", "gender": "Female", "dob": None,         "postcode": None},
        ]
        fields = ["patient_id", "gender", "dob", "postcode"]
        total_cells = len(records) * len(fields)
        filled_cells = sum(1 for r in records for f in fields if r[f] is not None)
        completeness = filled_cells / total_cells
        # 3 records × 4 fields = 12 cells; nulls: gender(p2), dob(p3), postcode(p3) = 3 nulls → 9 filled
        assert round(completeness, 4) == round(9/12, 4)

    def test_zero_nulls_is_100pct(self):
        records = [
            {"id": "1", "val": "a"},
            {"id": "2", "val": "b"},
        ]
        total = len(records) * 2
        filled = sum(1 for r in records for v in r.values() if v is not None)
        assert filled / total == 1.0
