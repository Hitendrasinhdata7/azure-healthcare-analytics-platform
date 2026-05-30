# Cost Optimisation Guide
## Azure Healthcare Analytics Platform

---

## Storage Optimisation

### Delta Lake OPTIMIZE & VACUUM
Small files are the most common cause of slow reads and unnecessary storage costs.

```python
# Run weekly in a maintenance notebook
from delta.tables import DeltaTable

tables = ["bronze/patients", "silver/patients", "gold/fact_patient_activity"]
for t in tables:
    DeltaTable.forPath(spark, f"abfss://.../{t}").optimize().executeCompaction()
    spark.sql(f"VACUUM delta.`abfss://.../{t}` RETAIN 168 HOURS")
```

### Partitioning Strategy
| Table | Partition Key | Rationale |
|-------|---------------|-----------|
| Appointments | `appointment_year`, `appointment_month` | Filters always include date range |
| Imaging | `modality` | Scans frequently filtered by modality |
| Fact | `activity_year`, `activity_type` | Power BI queries filter by year + type |

Avoid over-partitioning: keep partition file sizes between 128MB–1GB.

### Z-Ordering
```python
spark.sql("OPTIMIZE delta.`/gold/fact_patient_activity` ZORDER BY (patient_id, activity_date)")
```
Used for multi-dimensional filters (patient_id + date) that can't both be partition keys.

---

## Cluster Sizing

### Databricks Cluster Recommendations

| Job Type | Driver | Workers | Instance |
|----------|--------|---------|----------|
| Bronze ingestion | Standard_D4s_v3 | 2–4 (auto-scale) | Spot |
| Silver processing | Standard_D8s_v3 | 4–8 (auto-scale) | Spot |
| Gold aggregation | Standard_D4s_v3 | 2–4 | On-demand |
| DQ checks | Standard_D4s_v3 | 2 | Spot |

**Spot instance savings:** 60–80% cost reduction; suitable for all batch jobs.  
**Auto-scaling:** Set min=2, max=8; scale-down after 10 minutes idle.

---

## Synapse SQL Pool

- **Auto-pause:** Enabled at 15 minutes idle → saves ~65% in dev/test
- **Workload management:** Separate resource classes for ETL (largerc) vs BI (mediumrc)
- **Right-sizing:**
  - Dev: DW100c (~£1.80/hr → auto-pause to ~£13/day)
  - Test: DW100c
  - Prod: DW200c (increase on-demand for month-end reporting)

---

## Reserved Instances & Savings Plans

| Resource | Commitment | Est. Saving |
|----------|-----------|-------------|
| Databricks DBUs | 1-year pre-purchase | ~40% |
| Synapse SQL Pool | 1-year RI | ~36% |
| ADLS Gen2 | Reserved capacity (100 TB) | ~18% |

---

## Estimated Monthly Costs (Dev)

| Service | Est. Cost |
|---------|-----------|
| ADLS Gen2 (1 TB, LRS) | ~£18 |
| Databricks (200 DBU/month, Standard) | ~£80 |
| Synapse SQL Pool DW100c (auto-pause) | ~£130 |
| Azure Data Factory (1000 runs) | ~£4 |
| Key Vault | ~£2 |
| Log Analytics (5 GB/day) | ~£8 |
| **Total Dev** | **~£242/month** |

Prod (GRS storage, DW200c, reserved instances) estimated at ~£600–800/month.
