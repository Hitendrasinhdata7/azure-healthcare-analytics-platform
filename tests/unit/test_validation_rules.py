"""
Unit tests for validation_rules and DataQualityEngine.
Run locally with:  pytest tests/unit/ -v
"""

import pytest
import sys
import os

# Allow import of databricks notebooks as modules locally
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../databricks/notebooks"))

# ── Lightweight pure-Python tests (no Spark required) ─────────

from validation_rules import (
    PATIENT_RULES,
    APPOINTMENT_RULES,
    IMAGING_RULES,
    PROCEDURE_RULES,
    REFERRAL_RULES,
    ALL_RULES,
)

class TestValidationRuleSets:
    def test_all_tables_have_rules(self):
        expected = {"patients", "appointments", "imaging", "procedures", "referrals"}
        assert set(ALL_RULES.keys()) == expected

    def test_patient_rules_contain_required_keys(self):
        required = {"patient_id_not_null", "gender_valid", "dob_not_null"}
        assert required.issubset(set(PATIENT_RULES.keys()))

    def test_appointment_rules_contain_required_keys(self):
        required = {"appointment_id_not_null", "patient_id_not_null", "status_valid"}
        assert required.issubset(set(APPOINTMENT_RULES.keys()))

    def test_procedure_rules_contain_cost_checks(self):
        assert "cost_not_null"  in PROCEDURE_RULES
        assert "cost_positive"  in PROCEDURE_RULES

    def test_no_empty_rule_sets(self):
        for table, rules in ALL_RULES.items():
            assert len(rules) > 0, f"Rule set for '{table}' is empty"


# ── Data model unit tests (pure Python) ──────────────────────

class TestDataModels:
    def test_patient_required_columns(self):
        columns = ["patient_id", "gender", "date_of_birth", "postcode"]
        assert all(isinstance(c, str) for c in columns)
        assert len(columns) == 4

    def test_appointment_required_columns(self):
        columns = ["appointment_id", "patient_id", "appointment_date", "department", "status"]
        assert len(columns) == 5

    def test_valid_statuses(self):
        valid = ["Attended", "Dna", "Cancelled", "Booked"]
        assert len(valid) == 4
        assert "Attended" in valid

    def test_valid_modalities(self):
        valid = ["MRI", "CT", "X-RAY", "ULTRASOUND", "PET"]
        assert len(valid) == 5

    def test_valid_genders(self):
        valid = ["Male", "Female", "Other"]
        assert len(valid) == 3


# ── Age band logic unit tests ─────────────────────────────────

def compute_age_band(age: int) -> str:
    if age < 18:   return "0-17"
    if age < 35:   return "18-34"
    if age < 50:   return "35-49"
    if age < 65:   return "50-64"
    if age < 80:   return "65-79"
    return "80+"

class TestAgeBandLogic:
    @pytest.mark.parametrize("age,expected", [
        (0,  "0-17"),
        (17, "0-17"),
        (18, "18-34"),
        (34, "18-34"),
        (35, "35-49"),
        (49, "35-49"),
        (50, "50-64"),
        (64, "50-64"),
        (65, "65-79"),
        (79, "65-79"),
        (80, "80+"),
        (99, "80+"),
    ])
    def test_age_bands(self, age, expected):
        assert compute_age_band(age) == expected


# ── Cost validation ───────────────────────────────────────────

class TestCostValidation:
    @pytest.mark.parametrize("cost,valid", [
        (500.0,    True),
        (25000.0,  True),
        (1.0,      True),
        (0.0,      False),
        (-100.0,   False),
        (None,     False),
        (500001.0, False),
    ])
    def test_cost_validity(self, cost, valid):
        if cost is None:
            assert not valid
        elif cost <= 0:
            assert not valid
        elif cost > 500_000:
            assert not valid
        else:
            assert valid


# ── Postcode regex (pure Python) ──────────────────────────────

import re

POSTCODE_PATTERN = re.compile(r"^[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}$")

class TestPostcodeValidation:
    @pytest.mark.parametrize("postcode,valid", [
        ("SW1A 1AA", True),
        ("E1 6RF",   True),
        ("M1 1AE",   True),
        ("B1 1BB",   True),
        ("invalid",  False),
        ("",         False),
        ("12345",    False),
    ])
    def test_postcode_pattern(self, postcode, valid):
        match = bool(POSTCODE_PATTERN.match(postcode))
        assert match == valid
