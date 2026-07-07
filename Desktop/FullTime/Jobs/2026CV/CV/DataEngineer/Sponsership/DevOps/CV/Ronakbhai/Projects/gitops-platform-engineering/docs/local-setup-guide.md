# Local Setup Guide

Run the entire platform on your laptop using `kind` (Kubernetes-in-Docker) — no cloud account
or cost required. This is how to demo the project live in an interview.

## Prerequisites

- Docker Desktop (or another container runtime) running
- `kind` (`brew install kind` / see kind.sigs.k8s.io)
- `kubectl`
- `helm`
- `kustomize` (optional — `kubectl kustomize` also works)

## One-command bootstrap

```bash
git clone https://github.com/org/gitops-platform-engineering.git
cd gitops-platform-engineering
./scripts/bootstrap-local.sh
```

This script (`scripts/bootstrap-local.sh`):
1. Creates a 3-node `kind` cluster (1 control-plane, 2 workers) via `scripts/kind-cluster-config.yaml`.
2. Installs ArgoCD via Helm.
3. Installs Vault in dev mode (single replica, in-memory — **local demo only**, real environments use `platform-services/vault/values.yaml`'s HA Raft config).
4. Applies the single App of Apps root Application, which then pulls in everything else declaratively.
5. Port-forwards the ArgoCD UI to `https://localhost:8081`.

## Accessing ArgoCD

```bash
# Get the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d

# UI: https://localhost:8081  (user: admin)
```

You should see the `root-app` Application, which owns `dev-apps`, `staging-apps` (if you've
registered additional local clusters), and `platform-services` — watch them sync in real time.

## Demonstrating drift detection live

```bash
# Manually break a running Deployment
kubectl -n dev-sample-service scale deploy dev-sample-service --replicas=0

# Watch ArgoCD detect drift and self-heal within ~1 sync cycle
kubectl -n argocd logs deploy/argocd-application-controller -f
```

Within moments, ArgoCD reverts the manual change back to the Git-defined replica count —
this is the single most compelling live demo moment for an interview.

## Exploring Kustomize overlays

```bash
kubectl kustomize apps/sample-service/overlays/dev
kubectl kustomize apps/sample-service/overlays/staging
kubectl kustomize apps/sample-service/overlays/prod
```

Compare the rendered output across environments to see replica counts, resource limits, and
image tags diverge from the same shared base.

## Tearing down

```bash
./scripts/teardown-local.sh
```

## Notes on what's simulated locally vs. real-world

| Component | Local (`kind`) | Real deployment |
|---|---|---|
| Vault | Dev mode, single node, in-memory, unsealed automatically | HA Raft, 3 replicas, KMS-backed auto-unseal, audit storage |
| Clusters | Single `kind` cluster, all envs as namespaces for demo simplicity | 3 separate EKS clusters via `infrastructure/terraform` |
| Ingress/TLS | Not exposed publicly, port-forwarded only | ALB + Route53 + cert-manager/Let's Encrypt |
| CI/CD | Manually trigger workflows locally with `act` (optional) or read as reference | Real GitHub Actions in `.github/workflows/` |
