-- ============================================================
-- Load Gold Delta Lake → Synapse Dedicated SQL Pool
-- Azure Healthcare Analytics Platform
-- Run after each Silver→Gold Databricks pipeline completes.
-- ============================================================
USE HealthcareAnalytics;
GO

-- ── Truncate and reload DimDate (full refresh, small table) ──
TRUNCATE TABLE [dbo].[DimDate];

INSERT INTO [dbo].[DimDate]
    ([DateKey],[Year],[Quarter],[Month],[MonthName],[Week],[DayOfWeek],[DayName],[IsWeekend],[FinancialYear])
SELECT
    [date_key]    AS DateKey,
    [year]        AS Year,
    [quarter]     AS Quarter,
    [month]       AS Month,
    [month_name]  AS MonthName,
    [week]        AS Week,
    [day_of_week] AS DayOfWeek,
    [day_name]    AS DayName,
    CAST([is_weekend] AS BIT) AS IsWeekend,
    [financial_year] AS FinancialYear
FROM OPENROWSET(
    BULK 'https://adlshealthcareprod.dfs.core.windows.net/gold/dim_date/**',
    FORMAT = 'DELTA'
) AS src;
GO

-- ── Upsert DimPatient ─────────────────────────────────────────
MERGE [dbo].[DimPatient] AS target
USING (
    SELECT
        [patient_id]    AS PatientId,
        [gender]        AS Gender,
        [date_of_birth] AS DateOfBirth,
        [postcode]      AS Postcode,
        CAST([age] AS TINYINT) AS Age,
        [age_band]      AS AgeBand
    FROM OPENROWSET(
        BULK 'https://adlshealthcareprod.dfs.core.windows.net/gold/dim_patient/**',
        FORMAT = 'DELTA'
    ) AS src
) AS source
ON target.[PatientId] = source.[PatientId]
WHEN MATCHED THEN
    UPDATE SET
        target.[Gender]    = source.[Gender],
        target.[DateOfBirth]= source.[DateOfBirth],
        target.[Postcode]  = source.[Postcode],
        target.[Age]       = source.[Age],
        target.[AgeBand]   = source.[AgeBand],
        target.[UpdatedAt] = GETUTCDATE()
WHEN NOT MATCHED BY TARGET THEN
    INSERT ([PatientId],[Gender],[DateOfBirth],[Postcode],[Age],[AgeBand])
    VALUES (source.[PatientId],source.[Gender],source.[DateOfBirth],
            source.[Postcode],source.[Age],source.[AgeBand]);
GO

-- ── Truncate and reload DimDepartment ────────────────────────
TRUNCATE TABLE [dbo].[DimDepartment];

INSERT INTO [dbo].[DimDepartment] ([DepartmentName],[DepartmentGroup])
SELECT
    [department]       AS DepartmentName,
    [department_group] AS DepartmentGroup
FROM OPENROWSET(
    BULK 'https://adlshealthcareprod.dfs.core.windows.net/gold/dim_department/**',
    FORMAT = 'DELTA'
) AS src;
GO

-- ── Incremental load FactPatientActivity (by year/month) ─────
-- Only load current month to keep loads fast.
DECLARE @LoadYear  SMALLINT = YEAR(GETUTCDATE());
DECLARE @LoadMonth TINYINT  = MONTH(GETUTCDATE());

DELETE FROM [dbo].[FactPatientActivity]
WHERE [ActivityYear] = @LoadYear AND [ActivityMonth] = @LoadMonth;

INSERT INTO [dbo].[FactPatientActivity]
(
    [ActivityId],[ActivityType],[PatientKey],[DateKey],[DepartmentKey],
    [Status],[Cost],[Modality],[Speciality],
    [ActivityYear],[ActivityMonth],[AgeBand],[Gender],
    [TotalActivitiesPerPatient]
)
SELECT
    f.[activity_id]                      AS ActivityId,
    f.[activity_type]                    AS ActivityType,
    p.[PatientKey]                       AS PatientKey,
    f.[activity_date]                    AS DateKey,
    d.[DepartmentKey]                    AS DepartmentKey,
    f.[status]                           AS Status,
    CAST(f.[cost] AS DECIMAL(12,2))      AS Cost,
    f.[modality]                         AS Modality,
    f.[speciality]                       AS Speciality,
    CAST(f.[activity_year]  AS SMALLINT) AS ActivityYear,
    CAST(f.[activity_month] AS TINYINT)  AS ActivityMonth,
    f.[age_band]                         AS AgeBand,
    f.[gender]                           AS Gender,
    CAST(f.[total_activities_per_patient] AS INT) AS TotalActivitiesPerPatient
FROM OPENROWSET(
    BULK 'https://adlshealthcareprod.dfs.core.windows.net/gold/fact_patient_activity/**',
    FORMAT = 'DELTA'
) AS f
LEFT JOIN [dbo].[DimPatient]    p ON f.[patient_id]  = p.[PatientId]
LEFT JOIN [dbo].[DimDepartment] d ON f.[department]  = d.[DepartmentName]
WHERE CAST(f.[activity_year] AS SMALLINT) = @LoadYear
  AND CAST(f.[activity_month] AS TINYINT) = @LoadMonth;
GO

PRINT 'Synapse load complete — ' + CONVERT(VARCHAR, GETUTCDATE(), 120);
