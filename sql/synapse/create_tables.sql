-- ============================================================
-- Azure Synapse Analytics - Healthcare Data Warehouse
-- Azure Healthcare Analytics Platform
-- ============================================================

-- ── Database setup ────────────────────────────────────────────
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'HealthcareAnalytics')
    CREATE DATABASE HealthcareAnalytics;
GO
USE HealthcareAnalytics;
GO

-- ── DimDate ───────────────────────────────────────────────────
CREATE TABLE [dbo].[DimDate]
(
    [DateKey]       DATE         NOT NULL,
    [Year]          SMALLINT     NOT NULL,
    [Quarter]       TINYINT      NOT NULL,
    [Month]         TINYINT      NOT NULL,
    [MonthName]     NVARCHAR(10) NOT NULL,
    [Week]          TINYINT      NOT NULL,
    [DayOfWeek]     TINYINT      NOT NULL,
    [DayName]       NVARCHAR(10) NOT NULL,
    [IsWeekend]     BIT          NOT NULL DEFAULT 0,
    [FinancialYear] NVARCHAR(9)  NOT NULL   -- e.g. 2023/2024
)
WITH
(
    DISTRIBUTION = REPLICATE,
    CLUSTERED COLUMNSTORE INDEX
);
GO

-- ── DimPatient ────────────────────────────────────────────────
CREATE TABLE [dbo].[DimPatient]
(
    [PatientKey]   BIGINT       NOT NULL IDENTITY(1,1),
    [PatientId]    NVARCHAR(36) NOT NULL,   -- UUID
    [Gender]       NVARCHAR(10) NULL,
    [DateOfBirth]  DATE         NULL,
    [Postcode]     NVARCHAR(10) NULL,
    [Age]          TINYINT      NULL,
    [AgeBand]      NVARCHAR(10) NULL,       -- 0-17, 18-34, ...
    [LoadedAt]     DATETIME2    NOT NULL DEFAULT GETUTCDATE(),
    [UpdatedAt]    DATETIME2    NOT NULL DEFAULT GETUTCDATE()
)
WITH
(
    DISTRIBUTION = REPLICATE,
    CLUSTERED COLUMNSTORE INDEX
);
GO

-- ── DimDepartment ─────────────────────────────────────────────
CREATE TABLE [dbo].[DimDepartment]
(
    [DepartmentKey]   BIGINT       NOT NULL IDENTITY(1,1),
    [DepartmentName]  NVARCHAR(50) NOT NULL,
    [DepartmentGroup] NVARCHAR(20) NOT NULL  -- Specialist / Acute / Other
)
WITH
(
    DISTRIBUTION = REPLICATE,
    CLUSTERED COLUMNSTORE INDEX
);
GO

-- ── FactPatientActivity ───────────────────────────────────────
CREATE TABLE [dbo].[FactPatientActivity]
(
    [ActivityId]                 NVARCHAR(36)  NOT NULL,
    [ActivityType]               NVARCHAR(20)  NOT NULL,  -- APPOINTMENT/IMAGING/PROCEDURE/REFERRAL
    [PatientKey]                 BIGINT        NULL,
    [DateKey]                    DATE          NULL,
    [DepartmentKey]              BIGINT        NULL,
    [Status]                     NVARCHAR(20)  NULL,
    [Cost]                       DECIMAL(12,2) NULL,
    [Modality]                   NVARCHAR(20)  NULL,
    [Speciality]                 NVARCHAR(50)  NULL,
    [ActivityYear]               SMALLINT      NULL,
    [ActivityMonth]              TINYINT       NULL,
    [AgeBand]                    NVARCHAR(10)  NULL,
    [Gender]                     NVARCHAR(10)  NULL,
    [TotalActivitiesPerPatient]  INT           NULL,
    [LoadedAt]                   DATETIME2     NOT NULL DEFAULT GETUTCDATE()
)
WITH
(
    DISTRIBUTION = HASH([PatientKey]),
    CLUSTERED COLUMNSTORE INDEX
)
PARTITION
(
    [ActivityYear] RANGE RIGHT FOR VALUES (2020, 2021, 2022, 2023, 2024, 2025)
);
GO

-- ── Indexes ───────────────────────────────────────────────────
CREATE INDEX IX_Fact_ActivityType ON [dbo].[FactPatientActivity] ([ActivityType]);
CREATE INDEX IX_Fact_DateKey      ON [dbo].[FactPatientActivity] ([DateKey]);
GO
