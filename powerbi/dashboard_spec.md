# Power BI Dashboard Specification
## Azure Healthcare Analytics Platform

---

## Dashboard Pages

### Page 1 — Executive Summary
| Visual               | Type        | Fields                                      |
|----------------------|-------------|---------------------------------------------|
| Total Patients       | Card        | DISTINCTCOUNT(DimPatient[PatientId])         |
| Total Appointments   | Card        | COUNTROWS FILTER ActivityType=APPOINTMENT    |
| Attendance Rate      | Card        | % Attended of total appointments             |
| Monthly Trend        | Line Chart  | Month × AppointmentCount                    |
| Department Workload  | Bar Chart   | Department × AppointmentCount               |

### Page 2 — Appointment Analytics
- Appointment status breakdown (Donut)
- DNA rate by department (Bar)
- Monthly appointment volume (Area chart)
- Department heatmap by month

### Page 3 — Referral Trends
- Referrals by speciality (Bar)
- Rolling 3-month average (Line)
- Year-on-year comparison

### Page 4 — Imaging Utilisation
- Scan count by modality (Pie/Donut)
- Monthly scan volume (Line)
- Modality share % (100% stacked bar)

### Page 5 — Procedure Costs
- Total cost by month (Column)
- Average cost by procedure type
- Cost distribution (Box plot / Histogram)

### Page 6 — Patient Demographics
- Age band distribution (Bar)
- Gender split (Donut)
- Activity by age band and gender

---

## DAX Measures

```dax
-- ── Core Measures ──────────────────────────────────────────

Total Patients = DISTINCTCOUNT(DimPatient[PatientId])

Total Appointments =
CALCULATE(
    COUNTROWS(FactPatientActivity),
    FactPatientActivity[ActivityType] = "APPOINTMENT"
)

Attendance Rate % =
DIVIDE(
    CALCULATE(
        COUNTROWS(FactPatientActivity),
        FactPatientActivity[ActivityType] = "APPOINTMENT",
        FactPatientActivity[Status] = "Attended"
    ),
    [Total Appointments],
    0
) * 100

DNA Rate % =
DIVIDE(
    CALCULATE(
        COUNTROWS(FactPatientActivity),
        FactPatientActivity[ActivityType] = "APPOINTMENT",
        FactPatientActivity[Status] = "Dna"
    ),
    [Total Appointments],
    0
) * 100

-- ── Procedure Costs ────────────────────────────────────────

Total Procedure Cost =
CALCULATE(
    SUM(FactPatientActivity[Cost]),
    FactPatientActivity[ActivityType] = "PROCEDURE"
)

Avg Procedure Cost =
CALCULATE(
    AVERAGEX(
        FILTER(FactPatientActivity, FactPatientActivity[ActivityType] = "PROCEDURE"),
        FactPatientActivity[Cost]
    )
)

-- ── Rolling Averages ───────────────────────────────────────

Appointments 3M Rolling Avg =
CALCULATE(
    [Total Appointments],
    DATESINPERIOD(DimDate[DateKey], LASTDATE(DimDate[DateKey]), -3, MONTH)
) / 3

-- ── Year-on-Year ───────────────────────────────────────────

Appointments YoY Change % =
VAR CurrentYear = [Total Appointments]
VAR PriorYear =
    CALCULATE(
        [Total Appointments],
        DATEADD(DimDate[DateKey], -1, YEAR)
    )
RETURN
    DIVIDE(CurrentYear - PriorYear, PriorYear, 0) * 100

-- ── Referrals ──────────────────────────────────────────────

Total Referrals =
CALCULATE(
    COUNTROWS(FactPatientActivity),
    FactPatientActivity[ActivityType] = "REFERRAL"
)

-- ── Imaging ────────────────────────────────────────────────

Total Scans =
CALCULATE(
    COUNTROWS(FactPatientActivity),
    FactPatientActivity[ActivityType] = "IMAGING"
)

MRI Share % =
DIVIDE(
    CALCULATE([Total Scans], FactPatientActivity[Modality] = "MRI"),
    [Total Scans],
    0
) * 100

-- ── Dynamic Title ──────────────────────────────────────────

Report Title =
"Healthcare Analytics — "
    & SELECTEDVALUE(DimDate[FinancialYear], "All Years")
    & " | "
    & SELECTEDVALUE(DimDepartment[DepartmentName], "All Departments")
```

---

## Data Source Connection

Connect Power BI Desktop to Azure Synapse Analytics:

1. **Get Data** → **Azure Synapse Analytics SQL**
2. Server: `synw-healthcare-prod.sql.azuresynapse.net`
3. Database: `HealthcareAnalytics`
4. Authentication: **Microsoft Account** (Azure AD)
5. Import the following tables/views:
   - `dbo.DimPatient`
   - `dbo.DimDepartment`
   - `dbo.DimDate`
   - `dbo.FactPatientActivity`
   - `dbo.vw_AppointmentsByDepartment`
   - `dbo.vw_ProcedureCosts`
   - `dbo.vw_ReferralTrends`
   - `dbo.vw_ImagingUtilisation`

## Relationships

| From                              | To                          | Cardinality |
|-----------------------------------|-----------------------------|-------------|
| FactPatientActivity[PatientKey]   | DimPatient[PatientKey]      | Many:1      |
| FactPatientActivity[DepartmentKey]| DimDepartment[DepartmentKey]| Many:1      |
| FactPatientActivity[DateKey]      | DimDate[DateKey]            | Many:1      |

## Scheduled Refresh

Configure dataset refresh in Power BI Service:
- Frequency: Daily at 06:00 UTC
- Gateway: Azure Data Gateway (managed)
- Credentials: Service Principal
