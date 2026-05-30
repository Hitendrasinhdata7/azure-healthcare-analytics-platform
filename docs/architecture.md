# Architecture Diagrams
## Azure Healthcare Analytics Platform

---

## 1. End-to-End Architecture

```mermaid
flowchart TD
    subgraph Sources["🏥 Healthcare Source Systems"]
        S1[Patient Registry]
        S2[Appointment System]
        S3[Imaging PACS]
        S4[Procedure System]
        S5[Referral System]
    end

    subgraph Ingestion["⚙️ Azure Data Factory"]
        ADF[Pipeline: pl_ingest_healthcare_bronze\nScheduled Daily 01:00 UTC]
    end

    subgraph Lake["☁️ Azure Data Lake Storage Gen2"]
        RAW[📁 raw/\nCSV source files]

        subgraph Bronze["🥉 Bronze Container"]
            B1[bronze/patients/]
            B2[bronze/appointments/]
            B3[bronze/imaging/]
            B4[bronze/procedures/]
            B5[bronze/referrals/]
        end

        subgraph Silver["🥈 Silver Container"]
            SL1[silver/patients/\nDeduplicated · Standardised · DQ flagged]
            SL2[silver/appointments/]
            SL3[silver/imaging/]
            SL4[silver/procedures/]
            SL5[silver/referrals/]
        end

        subgraph Gold["🥇 Gold Container"]
            G1[gold/dim_patient/]
            G2[gold/dim_department/]
            G3[gold/dim_date/]
            G4[gold/fact_patient_activity/]
            G5[gold/kpi_*/\nPre-aggregated KPIs]
        end
    end

    subgraph Databricks["⚡ Azure Databricks — PySpark + Delta Lake"]
        DB1[add_bronze_metadata.py]
        DB2[bronze_to_silver.py]
        DB3[silver_to_gold.py]
        DB4[data_quality.py]
    end

    subgraph Synapse["🔷 Azure Synapse Analytics"]
        SYN1[DimPatient]
        SYN2[DimDepartment]
        SYN3[DimDate]
        SYN4[FactPatientActivity]
        SYN5[Analytics Views]
    end

    subgraph BI["📊 Power BI"]
        PBI1[Executive Summary]
        PBI2[Appointment Analytics]
        PBI3[Referral Trends]
        PBI4[Imaging Utilisation]
        PBI5[Procedure Costs]
    end

    subgraph Security["🔐 Security"]
        KV[Azure Key Vault]
        AD[Azure Active Directory\nManaged Identity · RBAC]
        PE[Private Endpoints]
    end

    subgraph Monitor["📡 Observability"]
        MON[Azure Monitor\n+ Log Analytics]
        ALERT[Alerts & Notifications]
    end

    S1 & S2 & S3 & S4 & S5 -->|CSV export| RAW
    RAW --> ADF
    ADF --> DB1
    DB1 --> B1 & B2 & B3 & B4 & B5
    B1 & B2 & B3 & B4 & B5 --> DB2
    DB2 --> SL1 & SL2 & SL3 & SL4 & SL5
    SL1 & SL2 & SL3 & SL4 & SL5 --> DB3
    SL1 & SL2 & SL3 & SL4 & SL5 --> DB4
    DB3 --> G1 & G2 & G3 & G4 & G5
    G1 & G2 & G3 & G4 --> SYN1 & SYN2 & SYN3 & SYN4
    SYN4 --> SYN5
    SYN5 --> PBI1 & PBI2 & PBI3 & PBI4 & PBI5

    KV -.->|Secrets| ADF & Databricks & Synapse
    AD -.->|AuthN/AuthZ| ADF & Databricks & Synapse & BI
    ADF & Databricks & Synapse -.->|Logs| MON
    MON --> ALERT
```

---

## 2. Medallion Architecture Data Flow

```mermaid
flowchart LR
    RAW["📁 Raw\nCSV files\nUnvalidated"] 
    -->|ADF Copy| 
    BRONZE["🥉 Bronze\nDelta Lake\nImmutable\n+ Audit columns\nAppend only"]
    -->|bronze_to_silver.py\nDeduplicate\nStandardise\nValidate| 
    SILVER["🥈 Silver\nDelta Lake\nCleansed\nDQ flags\nMERGE / upsert"]
    -->|silver_to_gold.py\nAggregate\nEnrich\nModel|
    GOLD["🥇 Gold\nDelta Lake\nFact + Dim\nKPI tables\nBusiness-ready"]
    -->|External tables|
    SYNAPSE["🔷 Synapse\nSQL Pool\nAnalytics views"]
    -->|DirectQuery / Import|
    PBI["📊 Power BI\nDashboards"]
```

---

## 3. CI/CD Pipeline

```mermaid
flowchart TD
    DEV[Developer\npushes code] --> PR[Pull Request\nto develop]
    PR --> CI["CI Checks\n✅ flake8 lint\n✅ pytest unit tests\n✅ terraform validate"]
    CI -->|PR merged| DEPLOY_DEV["Deploy Dev\nterraform apply\ndatabricks notebooks"]
    DEPLOY_DEV --> PR_MAIN[Pull Request\nto main]
    PR_MAIN --> CI2["CI Checks\n(same as above)"]
    CI2 -->|PR merged| DEPLOY_TEST["Deploy Test\nterraform apply"]
    DEPLOY_TEST --> MANUAL["Manual Approval\n(GitHub Environment)"]
    MANUAL --> DEPLOY_PROD["Deploy Prod\nterraform apply\nDatabricks deploy"]
```

---

## 4. Security Model

```mermaid
flowchart TD
    USER["👤 User / Service"] --> AAD["Azure AD\nAuthentication"]
    AAD --> RBAC["RBAC\nRole Assignment"]
    RBAC -->|Storage Blob Data Contributor| ADLS["ADLS Gen2\nBronze · Silver · Gold"]
    RBAC -->|Key Vault Secrets User| KV["Azure Key Vault\nSecrets"]
    RBAC -->|Synapse Contributor| SYN["Azure Synapse"]
    ADLS & KV & SYN --> PE["Private Endpoints\nNo public internet"]
    PE --> VNET["VNet 10.0.0.0/16\nNSG enforced"]
```

---

## 5. Data Model (Star Schema)

```mermaid
erDiagram
    FactPatientActivity {
        string ActivityId PK
        string ActivityType
        bigint PatientKey FK
        date   DateKey FK
        bigint DepartmentKey FK
        string Status
        decimal Cost
        string Modality
        string Speciality
        int    ActivityYear
        int    ActivityMonth
    }
    DimPatient {
        bigint PatientKey PK
        string PatientId
        string Gender
        date   DateOfBirth
        string Postcode
        int    Age
        string AgeBand
    }
    DimDepartment {
        bigint DepartmentKey PK
        string DepartmentName
        string DepartmentGroup
    }
    DimDate {
        date   DateKey PK
        int    Year
        int    Quarter
        int    Month
        string MonthName
        int    Week
        string FinancialYear
        bit    IsWeekend
    }
    FactPatientActivity }o--|| DimPatient : "PatientKey"
    FactPatientActivity }o--|| DimDepartment : "DepartmentKey"
    FactPatientActivity }o--|| DimDate : "DateKey"
```
