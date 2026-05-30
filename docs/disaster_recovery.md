# Disaster Recovery Runbook
## Azure Healthcare Analytics Platform

---

## Recovery Objectives

| Component | RPO | RTO |
|-----------|-----|-----|
| ADLS Gen2 (Gold/Silver) | 1 hour | 4 hours |
| Delta Lake data | 1 hour | 2 hours |
| Synapse SQL Pool | 8 hours | 24 hours |
| Databricks notebooks | Near-zero (Git) | 1 hour |
| Key Vault | Near-zero | 1 hour |
| ADF Pipelines | Near-zero (Git) | 1 hour |

---

## Backup Strategy

### ADLS Gen2
- **Dev/Test:** LRS (locally redundant, 3 copies same datacenter)
- **Prod:** GRS (geo-redundant, async replication to paired region)
- **Soft delete:** 30-day retention on blob containers
- **Versioning:** Enabled — previous versions recoverable via Azure Portal or CLI

```bash
# Restore a deleted blob
az storage blob undelete \
  --account-name adlshealthcareprod \
  --container-name gold \
  --name patients/_delta_log/00000000000000000001.json
```

### Delta Lake — Time Travel
Delta tables retain history. Default retention: 30 days (configurable).

```python
# Restore a table to a specific version
df = spark.read.format("delta") \
    .option("versionAsOf", 5) \
    .load("abfss://gold@adlshealthcareprod.dfs.core.windows.net/fact_patient_activity")

# Or restore in-place
from delta.tables import DeltaTable
dt = DeltaTable.forPath(spark, "abfss://gold@.../fact_patient_activity")
dt.restoreToVersion(5)
```

### Synapse SQL Pool
- **Automatic restore points:** Created every 8 hours, retained for 7 days (managed by Azure)
- **User-defined restore points:** Create before major loads

```sql
-- Create a restore point before bulk load
EXEC sys.sp_create_database_snapshot @Name = N'BeforeMonthEndLoad_20240301';
```

### Key Vault
- **Soft-delete:** 30 days (enabled by Terraform — `purge_protection_enabled = true`)
- **Backup secrets to secondary vault in DR region:**

```bash
az keyvault secret backup \
  --vault-name kv-healthcare-prod \
  --name synapse-sql-admin-password \
  --file ./backups/synapse-sql-admin-password.bak
```

---

## Geo-Replication (Prod Only)

Primary region: **UK South**  
Secondary region: **UK West** (Azure paired region)

| Service | Replication |
|---------|-------------|
| ADLS Gen2 | GRS (async — ~15 min lag) |
| Key Vault | Manual backup to secondary |
| Synapse | Geo-backup (8hr RPO) |

### Failover Procedure

1. Confirm primary region outage via [Azure Status](https://status.azure.com)
2. Initiate ADLS GRS failover (Microsoft-initiated or manual):
   ```bash
   az storage account failover --name adlshealthcareprod --resource-group rg-healthcare-prod
   ```
3. Re-deploy infrastructure to UK West using Terraform:
   ```bash
   terraform apply -var="location=ukwest" -var="environment=prod"
   ```
4. Update Databricks linked service and ADF connections to new storage endpoint
5. Restore Synapse from geo-backup
6. Update Power BI data source to new Synapse endpoint
7. Communicate RTO status to stakeholders

---

## Pipeline Recovery

### Replay missed incremental loads
All pipelines are idempotent (Delta MERGE). Re-trigger from last successful checkpoint:

```bash
# Trigger ADF pipeline for a specific date range
az datafactory pipeline create-run \
  --resource-group rg-healthcare-prod \
  --factory-name adf-healthcare-prod \
  --name pl_ingest_healthcare_bronze \
  --parameters '{"reprocess_from":"2024-03-01","reprocess_to":"2024-03-05"}'
```

### Databricks notebook recovery
Notebooks are version-controlled in Git. Re-deploy at any time:
```bash
databricks workspace import_dir databricks/notebooks /Shared/healthcare --overwrite
```

---

## Testing the DR Plan

DR tests should be conducted:
- **Annually:** Full failover simulation to secondary region
- **Quarterly:** Delta time-travel restore test
- **Monthly:** Backup restoration of Key Vault secrets

Document results in the DR test log and update this runbook accordingly.
