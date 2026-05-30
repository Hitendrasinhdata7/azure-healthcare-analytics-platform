"""
Synthetic Healthcare Data Generator
Generates realistic NHS-style datasets for the Azure Healthcare Analytics Platform.
No real patient data is used.
"""

import csv
import random
import uuid
from datetime import datetime, timedelta
import os

random.seed(42)

GENDERS = ["Male", "Female", "Other"]
DEPARTMENTS = ["Cardiology", "Orthopaedics", "Neurology", "Oncology", "Radiology",
               "Emergency", "Paediatrics", "Obstetrics", "Psychiatry", "General Surgery"]
APPOINTMENT_STATUSES = ["Attended", "DNA", "Cancelled", "Booked"]
MODALITIES = ["MRI", "CT", "X-Ray", "Ultrasound", "PET"]
PROCEDURE_TYPES = ["Hip Replacement", "Knee Replacement", "Appendectomy",
                   "Cataract Surgery", "Coronary Bypass", "Colonoscopy",
                   "Tonsillectomy", "Hernia Repair", "Cholecystectomy", "Angioplasty"]
SPECIALITIES = ["Cardiology", "Neurology", "Oncology", "Orthopaedics", "Gastroenterology",
                "Dermatology", "Endocrinology", "Haematology", "Nephrology", "Rheumatology"]
POSTCODES = ["SW1A 1AA", "E1 6RF", "M1 1AE", "B1 1BB", "LS1 1BA",
             "BS1 1AA", "G1 1AA", "EH1 1AA", "CF10 1AA", "NE1 1AA"]

NUM_PATIENTS = 1000
NUM_APPOINTMENTS = 5000
NUM_IMAGING = 2000
NUM_PROCEDURES = 1500
NUM_REFERRALS = 2500

def rand_date(start_year=2020, end_year=2024):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return (start + timedelta(days=random.randint(0, (end - start).days))).strftime("%Y-%m-%d")

def rand_dob():
    start = datetime(1940, 1, 1)
    end = datetime(2005, 12, 31)
    return (start + timedelta(days=random.randint(0, (end - start).days))).strftime("%Y-%m-%d")

output_dir = os.path.dirname(os.path.abspath(__file__))

# Patients
patient_ids = [str(uuid.uuid4()) for _ in range(NUM_PATIENTS)]
with open(f"{output_dir}/patients.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["patient_id", "gender", "date_of_birth", "postcode"])
    for pid in patient_ids:
        # Introduce ~2% nulls for data quality testing
        gender = random.choice(GENDERS) if random.random() > 0.02 else ""
        dob = rand_dob() if random.random() > 0.02 else ""
        postcode = random.choice(POSTCODES) if random.random() > 0.02 else ""
        w.writerow([pid, gender, dob, postcode])

# Appointments
with open(f"{output_dir}/appointments.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["appointment_id", "patient_id", "appointment_date", "department", "status"])
    seen_ids = set()
    for _ in range(NUM_APPOINTMENTS):
        aid = str(uuid.uuid4())
        seen_ids.add(aid)
        pid = random.choice(patient_ids)
        w.writerow([aid, pid, rand_date(), random.choice(DEPARTMENTS), random.choice(APPOINTMENT_STATUSES)])
    # Add ~1% duplicate rows for dedup testing
    for _ in range(int(NUM_APPOINTMENTS * 0.01)):
        aid = random.choice(list(seen_ids))
        pid = random.choice(patient_ids)
        w.writerow([aid, pid, rand_date(), random.choice(DEPARTMENTS), random.choice(APPOINTMENT_STATUSES)])

# Imaging
with open(f"{output_dir}/imaging.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["imaging_id", "patient_id", "modality", "scan_date"])
    for _ in range(NUM_IMAGING):
        w.writerow([str(uuid.uuid4()), random.choice(patient_ids), random.choice(MODALITIES), rand_date()])

# Procedures
with open(f"{output_dir}/procedures.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["procedure_id", "patient_id", "procedure_type", "cost"])
    for _ in range(NUM_PROCEDURES):
        cost = round(random.uniform(500, 25000), 2) if random.random() > 0.03 else ""
        w.writerow([str(uuid.uuid4()), random.choice(patient_ids), random.choice(PROCEDURE_TYPES), cost])

# Referrals
with open(f"{output_dir}/referrals.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["referral_id", "patient_id", "referral_date", "speciality"])
    for _ in range(NUM_REFERRALS):
        w.writerow([str(uuid.uuid4()), random.choice(patient_ids), rand_date(), random.choice(SPECIALITIES)])

print("Sample data generated successfully.")
print(f"  patients.csv      → {NUM_PATIENTS} rows")
print(f"  appointments.csv  → {NUM_APPOINTMENTS + int(NUM_APPOINTMENTS*0.01)} rows (with ~1% dupes)")
print(f"  imaging.csv       → {NUM_IMAGING} rows")
print(f"  procedures.csv    → {NUM_PROCEDURES} rows")
print(f"  referrals.csv     → {NUM_REFERRALS} rows")
