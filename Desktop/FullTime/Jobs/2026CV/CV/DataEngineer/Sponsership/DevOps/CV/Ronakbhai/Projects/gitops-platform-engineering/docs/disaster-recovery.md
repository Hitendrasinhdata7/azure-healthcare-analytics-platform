# Disaster Recovery and Reliability

## Backup Strategy

| Component | Backup Method | Frequency |
|---|---|---|
| Git repository | GitHub's own redundancy + a scheduled mirror push to a secondary Git host | Continuous / daily mirror |
| Vault | Raft snapshot (`vault operator raft snapshot save`) to S3 (versioned, encrypted) | Every 6h |
| Kubernetes cluster state | Velero backup of cluster resources + PV snapshots to S3 | Every 6h, retained 90 days |

## Recovery Strategy

1. **Cluster rebuild**: `terraform apply` in the affected environment recreates the EKS control plane and node groups from `infrastructure/terraform/environments/<env>` — this alone reconstructs *infrastructure*, not workloads.
2. **GitOps restoration**: bootstrap ArgoCD (`bootstrap/argocd-install-notes.md`), apply the single `root-app.yaml`, and the App of Apps pattern reconstructs every workload, platform service, and config exactly as Git describes it — no manual `kubectl apply` sequence to remember.
3. **Vault restoration**: restore the latest Raft snapshot into the freshly provisioned Vault HA cluster before ArgoCD/ESO come up, so secret-dependent workloads don't crash-loop on missing secrets.

## High Availability

- **ArgoCD HA**: 2+ replicas of `argocd-server` and `argocd-repo-server`, HA Redis backing store — no single point of failure in the GitOps control plane itself.
- **Vault HA**: 3-node Raft cluster tolerates 1 node failure with no downtime and no external Consul dependency.
- **Multi-AZ**: node groups and subnets span 2-3 AZs per environment (see `terraform.tfvars`); PodDisruptionBudgets (`apps/sample-service/overlays/prod/pdb.yaml`) ensure rolling node maintenance never drops below minimum available replicas.

## RTO / RPO targets (example)

| Scenario | RTO | RPO |
|---|---|---|
| Single pod/node failure | < 2 min (K8s self-healing + HPA) | 0 (no data loss, stateless app) |
| Full cluster loss (region-local) | ~45–90 min (Terraform + ArgoCD bootstrap + Vault restore) | ≤ 6h (Vault snapshot interval) |
| Git repository loss | < 30 min (restore from mirror) | Near-zero (GitHub redundancy + mirror) |
