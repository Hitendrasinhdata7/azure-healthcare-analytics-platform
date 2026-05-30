-- ============================================================
-- Analytics Views - Azure Healthcare Analytics Platform
-- ============================================================
USE HealthcareAnalytics;
GO

-- ── vw_AppointmentsByDepartment ───────────────────────────────
CREATE OR ALTER VIEW [dbo].[vw_AppointmentsByDepartment] AS
SELECT
    d.[DepartmentName],
    d.[DepartmentGroup],
    dt.[Year],
    dt.[Month],
    dt.[MonthName],
    dt.[FinancialYear],
    f.[Status],
    COUNT(f.[ActivityId])           AS AppointmentCount,
    COUNT(DISTINCT f.[PatientKey])  AS UniquePatients,
    SUM(CASE WHEN f.[Status] = 'Attended'  THEN 1 ELSE 0 END) AS Attended,
    SUM(CASE WHEN f.[Status] = 'DNA'       THEN 1 ELSE 0 END) AS DidNotAttend,
    SUM(CASE WHEN f.[Status] = 'Cancelled' THEN 1 ELSE 0 END) AS Cancelled,
    CAST(SUM(CASE WHEN f.[Status] = 'Attended' THEN 1 ELSE 0 END) AS FLOAT)
        / NULLIF(COUNT(f.[ActivityId]), 0) * 100                AS AttendanceRatePct
FROM [dbo].[FactPatientActivity] f
JOIN [dbo].[DimDepartment]        d  ON f.[DepartmentKey]  = d.[DepartmentKey]
JOIN [dbo].[DimDate]              dt ON f.[DateKey]        = dt.[DateKey]
WHERE f.[ActivityType] = 'APPOINTMENT'
GROUP BY d.[DepartmentName], d.[DepartmentGroup],
         dt.[Year], dt.[Month], dt.[MonthName], dt.[FinancialYear], f.[Status];
GO

-- ── vw_PatientDemographics ────────────────────────────────────
CREATE OR ALTER VIEW [dbo].[vw_PatientDemographics] AS
SELECT
    p.[Gender],
    p.[AgeBand],
    p.[Postcode],
    COUNT(DISTINCT p.[PatientKey])            AS PatientCount,
    AVG(CAST(p.[Age] AS FLOAT))               AS AvgAge,
    COUNT(f.[ActivityId])                     AS TotalActivities
FROM [dbo].[DimPatient]          p
LEFT JOIN [dbo].[FactPatientActivity] f ON p.[PatientKey] = f.[PatientKey]
GROUP BY p.[Gender], p.[AgeBand], p.[Postcode];
GO

-- ── vw_ProcedureCosts ─────────────────────────────────────────
CREATE OR ALTER VIEW [dbo].[vw_ProcedureCosts] AS
SELECT
    dt.[Year],
    dt.[Month],
    dt.[MonthName],
    dt.[FinancialYear],
    f.[Speciality],
    COUNT(f.[ActivityId])            AS ProcedureCount,
    SUM(f.[Cost])                    AS TotalCost,
    AVG(f.[Cost])                    AS AvgCost,
    MAX(f.[Cost])                    AS MaxCost,
    MIN(f.[Cost])                    AS MinCost,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.[Cost])
        OVER (PARTITION BY dt.[Year], dt.[Month]) AS MedianCost
FROM [dbo].[FactPatientActivity] f
JOIN [dbo].[DimDate]             dt ON f.[DateKey] = dt.[DateKey]
WHERE f.[ActivityType] = 'PROCEDURE'
  AND f.[Cost] IS NOT NULL;
GO

-- ── vw_ReferralTrends ─────────────────────────────────────────
CREATE OR ALTER VIEW [dbo].[vw_ReferralTrends] AS
SELECT
    dt.[Year],
    dt.[Quarter],
    dt.[Month],
    dt.[MonthName],
    f.[Speciality],
    COUNT(f.[ActivityId])           AS ReferralCount,
    COUNT(DISTINCT f.[PatientKey])  AS UniquePatients,
    -- Rolling 3-month average
    AVG(COUNT(f.[ActivityId])) OVER (
        PARTITION BY f.[Speciality]
        ORDER BY dt.[Year], dt.[Month]
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    )                               AS RollingAvg3Month
FROM [dbo].[FactPatientActivity] f
JOIN [dbo].[DimDate]             dt ON f.[DateKey] = dt.[DateKey]
WHERE f.[ActivityType] = 'REFERRAL'
GROUP BY dt.[Year], dt.[Quarter], dt.[Month], dt.[MonthName], f.[Speciality];
GO

-- ── vw_ImagingUtilisation ─────────────────────────────────────
CREATE OR ALTER VIEW [dbo].[vw_ImagingUtilisation] AS
SELECT
    dt.[Year],
    dt.[Month],
    dt.[MonthName],
    f.[Modality],
    COUNT(f.[ActivityId])           AS ScanCount,
    COUNT(DISTINCT f.[PatientKey])  AS UniquePatients,
    -- % of total scans this modality represents
    CAST(COUNT(f.[ActivityId]) AS FLOAT) /
        NULLIF(SUM(COUNT(f.[ActivityId])) OVER (PARTITION BY dt.[Year], dt.[Month]), 0) * 100
        AS ModalitySharePct
FROM [dbo].[FactPatientActivity] f
JOIN [dbo].[DimDate]             dt ON f.[DateKey] = dt.[DateKey]
WHERE f.[ActivityType] = 'IMAGING'
GROUP BY dt.[Year], dt.[Month], dt.[MonthName], f.[Modality];
GO

-- ── vw_DQDashboard ────────────────────────────────────────────
CREATE OR ALTER VIEW [dbo].[vw_DataQualityDashboard] AS
SELECT
    [table],
    [rule_name],
    [dimension],
    [total_rows],
    [failed_rows],
    [passed],
    [threshold],
    [actual_rate],
    [run_ts]
FROM OPENROWSET(
    BULK 'https://adlshealthcaredev.dfs.core.windows.net/monitoring/dq_results/**',
    FORMAT = 'DELTA'
) AS dq;
GO
