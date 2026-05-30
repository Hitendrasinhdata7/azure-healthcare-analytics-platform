# Security Architecture
## Azure Healthcare Analytics Platform

---

## Overview

The platform follows **Zero Trust** principles: authenticate every request, authorise with least privilege, assume breach. No credentials are stored in code or configuration files.

---

## Authentication — Azure Active Directory

All service-to-service communication uses **Managed Identity** (system-assigned). No passwords or connection strings appear in notebooks, pipelines, or Terraform code.

| Service | Auth Method |
|---------|-------------|
| Databricks → ADLS Gen2 | Managed Identity via Unity Catalog / Service Principal |
| ADF → Databricks | Managed Identity |
| ADF → ADLS Gen2 | Managed Identity |
| Synapse → ADLS Gen2 | Managed Identity |
| Synapse → Key Vault | Managed Identity |
| Power BI → Synapse | Azure AD OAuth2 / Service Principal |
| GitHub Actions → Azure | Service Principal (OIDC) |

---

## Authorisation — Role-Based Access Control (RBAC)

### Storage Account (ADLS Gen2)

| Principal | Role | Scope |
|-----------|------|-------|
| ADF Managed Identity | Storage Blob Data Contributor | Raw container only |
| Databricks Managed Identity | Storage Blob Data Contributor | Bronze, Silver, Gold |
| Synapse Managed Identity | Storage Blob Data Reader | Gold container |
| Data Engineers | Storage Blob Data Contributor | Dev environment only |
| Data Analysts | Storage Blob Data Reader | Gold container |
| Power BI Service Principal | Storage Blob Data Reader | Gold container |

### Synapse Analytics

| Role | Members |
|------|---------|
| Synapse Administrator | Data Platform team leads |
| Synapse SQL Administrator | Data Engineering team |
| Synapse Contributor | CI/CD Service Principal |
| Synapse Artifact Publisher | Developers (read-only in prod) |

### Databricks

| Group | Cluster Policy | Workspace Permission |
|-------|----------------|----------------------|
| data-engineers | Standard job cluster | Can edit, Can restart |
| data-analysts | SQL Warehouse | Read-only notebooks |
| ci-service-principal | Automated job cluster | Jobs admin |

---

## Secrets Management — Azure Key Vault

All secrets, keys, and certificates are stored in Key Vault. RBAC authorisation is enabled (not Access Policies).

### Secrets stored

| Secret Name | Description |
|-------------|-------------|
| `synapse-sql-admin-password` | Synapse SQL Pool admin password |
| `databricks-token` | Databricks PAT for CI/CD |
| `adf-service-principal-secret` | ADF linked service auth |
| `storage-account-key` | Fallback (Managed Identity preferred) |

### Access pattern in Databricks notebooks

```python
from azure.keyvault.secrets import SecretClient
from azure.identity import ManagedIdentityCredential

credential = ManagedIdentityCredential()
client = SecretClient(vault_url="https://kv-healthcare-prod.vault.azure.net/", credential=credential)
secret = client.get_secret("synapse-sql-admin-password").value
```

---

## Network Security

### Virtual Network Architecture

```
VNet: 10.0.0.0/16
├── snet-databricks-public  10.0.1.0/24  (Databricks, no-public-IP)
├── snet-databricks-private 10.0.2.0/24  (Databricks internal)
└── snet-services           10.0.3.0/24  (Key Vault, Storage private endpoints)
```

### Private Endpoints

| Service | DNS Override |
|---------|-------------|
| ADLS Gen2 | `privatelink.dfs.core.windows.net` |
| Key Vault | `privatelink.vaultcore.azure.net` |
| Synapse | `privatelink.sql.azuresynapse.net` |

### Network Security Groups

- All inbound traffic blocked by default
- Outbound to Azure services via Service Endpoints
- Databricks cluster traffic stays within VNet
- No public IP on Databricks workers

---

## Encryption

### At Rest
- ADLS Gen2: AES-256 (Microsoft-managed keys in dev/test; Customer-managed via Key Vault in prod)
- Delta Lake: Inherits storage encryption
- Synapse SQL Pool: Transparent Data Encryption (TDE) enabled

### In Transit
- TLS 1.2 minimum enforced on all Azure services
- HTTPS enforced on storage accounts (`enable_https_traffic_only = true`)
- Databricks cluster communication encrypted

---

## Data Protection (PII)

Healthcare data contains PII. Controls implemented:

- **Dynamic Data Masking** on Synapse: `date_of_birth` and `postcode` masked for Analyst role
- **Column-level security** in Synapse: procedure `cost` visible only to Finance role
- **Delta Lake column masking** (Unity Catalog): applied in prod workspace

```sql
-- Synapse Dynamic Data Masking
ALTER TABLE dbo.DimPatient
ALTER COLUMN DateOfBirth ADD MASKED WITH (FUNCTION = 'partial(0,"XXXX-XX-",2)');

ALTER TABLE dbo.DimPatient
ALTER COLUMN Postcode ADD MASKED WITH (FUNCTION = 'partial(2,"XXX",0)');
```

---

## Audit & Compliance

- **Azure Monitor Diagnostic Settings** enabled on all resources
- **Log Analytics** retention: 90 days (prod), 30 days (dev/test)
- **Key Vault audit logs** sent to Log Analytics
- **Databricks audit logs** via `AuditLog` table in Log Analytics
- All Terraform changes tracked in Git history
- No real patient data — synthetic data only (GDPR / DSP Toolkit compliant)
