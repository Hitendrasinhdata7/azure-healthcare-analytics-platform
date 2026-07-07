# Platform Architecture

## High-Level Platform Architecture

```mermaid
graph TB
    subgraph Git["Git Repository (Source of Truth)"]
        A1[bootstrap/]
        A2[apps/]
        A3[platform-services/]
        A4[infrastructure/terraform/]
    end

    subgraph Hub["Management / Hub Cluster"]
        ARGO[ArgoCD]
    end

    subgraph Dev["Dev Cluster"]
        D1[Sample Service]
        D2[Platform Services]
    end
    subgraph Staging["Staging Cluster"]
        S1[Sample Service]
        S2[Platform Services]
    end
    subgraph Prod["Production Cluster"]
        P1[Sample Service]
        P2[Platform Services]
        VAULT[Vault HA]
    end

    Git -->|watched by| ARGO
    ARGO -->|reconciles| Dev
    ARGO -->|reconciles| Staging
    ARGO -->|reconciles - manual sync| Prod
    VAULT -->|secrets via ESO| P1
```

## GitOps Reconciliation Loop

```mermaid
sequenceDiagram
    participant Git as Git Repo
    participant Argo as ArgoCD Controller
    participant K8s as Kubernetes API

    loop every 3 minutes (or on webhook)
        Argo->>Git: Poll / receive webhook
        Argo->>Argo: Render manifests (Kustomize)
        Argo->>K8s: Diff desired vs live state
        alt Drift detected
            Argo->>K8s: Apply corrective changes (selfHeal)
            Argo->>Argo: Emit OutOfSync -> Synced event
        else No drift
            Argo->>Argo: Mark Synced/Healthy
        end
    end
```

## Vault Secret Flow

```mermaid
sequenceDiagram
    participant Pod as App Pod (ServiceAccount)
    participant ESO as External Secrets Operator
    participant Vault as Vault (Kubernetes auth)
    participant K8s as Native K8s Secret

    ESO->>Vault: Authenticate using ServiceAccount JWT
    Vault->>Vault: Validate token via Kubernetes auth method
    Vault-->>ESO: Short-lived scoped secret
    ESO->>K8s: Write/refresh native Secret (every refreshInterval)
    Pod->>K8s: Mount Secret as env/volume
    Note over ESO,Vault: Repeats every 15m - this IS the rotation mechanism
```

## Environment Promotion Flow

```mermaid
flowchart LR
    PR[Feature PR] -->|merge| Main[main branch]
    Main --> CI[CI: build, scan, sign, SBOM]
    CI -->|auto| Dev[Dev overlay auto-updated]
    Dev -->|ArgoCD auto-sync| DevCluster[Dev Cluster]
    DevCluster -->|manual: verified in dev| PromoStaging[Promotion PR to Staging]
    PromoStaging -->|reviewed + merged| StagingCluster[Staging Cluster]
    StagingCluster -->|24h soak + signature verify| PromoProd[Promotion PR to Prod]
    PromoProd -->|CODEOWNERS approval + merge| ProdSync[ArgoCD manual sync]
    ProdSync --> ProdCluster[Production Cluster]
```

## Why GitOps

- **Auditability**: every change to cluster state is a Git commit with an author, timestamp, and PR review trail — no `kubectl apply` from a laptop leaves cluster state unexplained.
- **Repeatability**: rebuilding an entire environment is `git clone` + point ArgoCD at it, not a runbook of manual steps.
- **Security**: cluster credentials never leave the cluster/ArgoCD boundary; CI never needs `kubectl` access to prod, only push access to Git.
- **Operational consistency**: dev, staging, and prod are the same Kustomize base with explicit, reviewable overlays — configuration drift between environments becomes a diff, not a mystery.
- **Disaster recovery**: Git + Vault backup is sufficient to reconstruct full cluster state from nothing.
