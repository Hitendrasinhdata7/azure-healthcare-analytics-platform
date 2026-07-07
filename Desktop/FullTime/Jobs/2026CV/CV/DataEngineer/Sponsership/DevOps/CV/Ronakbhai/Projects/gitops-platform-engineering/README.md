# GitOps Platform Engineering — Enterprise Reference Implementation

> A production-grade GitOps platform demonstrating Kubernetes, ArgoCD, Kustomize, HashiCorp
> Vault, Terraform, and CI/CD promotion workflows the way a Platform/SRE team would actually
> build them — not a beginner tutorial.

[![CI](https://img.shields.io/badge/CI-build--scan--sign-blue)]()
[![GitOps](https://img.shields.io/badge/GitOps-ArgoCD-orange)]()
[![IaC](https://img.shields.io/badge/IaC-Terraform-purple)]()
[![Secrets](https://img.shields.io/badge/Secrets-Vault-black)]()

## Executive Summary

This repository is a complete, self-contained **GitOps Platform Engineering** reference
implementation: multi-cluster Kubernetes, ArgoCD-driven continuous delivery, Kustomize-based
environment management, HashiCorp Vault secrets, Terraform-provisioned infrastructure, a full
observability stack, and an auditable dev → staging → production promotion pipeline with
drift detection and self-healing.

It is built to be **run locally in minutes** (`./scripts/bootstrap-local.sh`, no cloud cost)
and to **read like a real platform team's repository** — every design decision is documented
with the alternatives considered and the tradeoffs accepted.

## Business Problem

Manual, ClickOps-driven Kubernetes operations don't scale past a handful of services: cluster
state drifts silently from intent, secrets sprawl across dashboards and Slack messages,
deployments are unauditable, and disaster recovery means "hope someone remembers the runbook."
This platform solves that with **Git as the single source of truth** for infrastructure,
application config, secrets *references*, and platform services alike.

## Solution Overview

| Layer | Technology | Purpose |
|---|---|---|
| Infrastructure | Terraform (VPC, EKS, IAM/IRSA, S3, Route53, ALB) | Provision the clusters and cloud resources GitOps runs on top of |
| GitOps Control Plane | ArgoCD (App of Apps) | Continuously reconcile cluster state to match Git |
| App Configuration | Kustomize (base + dev/staging/prod overlays) | Environment-specific config without manifest duplication |
| Secrets | HashiCorp Vault + External Secrets Operator | Dynamic, audited, rotated secrets — never in Git |
| CI/CD | GitHub Actions | Build, scan, sign, SBOM, and promote images through environments |
| Observability | Prometheus, Grafana, Loki, Alertmanager | Metrics, logs, drift/health alerting, dashboards-as-code |
| Security | cert-manager, NetworkPolicies, Pod Security Standards, cosign | TLS automation, zero-trust networking, supply-chain integrity |

## Architecture Diagram

See [`docs/architecture.md`](docs/architecture.md) for the full set of Mermaid diagrams:
high-level platform architecture, the ArgoCD reconciliation loop, the Vault secret flow, and
the environment promotion sequence.

## Repository Structure

```
.
├── bootstrap/              # ArgoCD install notes, AppProjects, App-of-Apps root
├── clusters/               # Per-environment cluster registration (hub-spoke model)
├── apps/sample-service/    # Kustomize base + dev/staging/prod overlays
├── platform-services/      # GitOps-managed ArgoCD, Vault, ESO, cert-manager, ingress, observability
├── infrastructure/terraform/ # Networking, EKS, IAM/IRSA, storage, DNS, security groups, LB
├── .github/workflows/      # CI (build/scan/sign) + promotion pipelines (dev/staging/prod)
├── policies/               # Pod security baseline documentation
├── scripts/                # One-command local bootstrap (kind), teardown, soak-time gate
└── docs/                   # Architecture, decisions, security, DR, interview talking points
```

## GitOps Workflow

`main` branch → CI (lint, Trivy scan, cosign sign, SBOM attestation) → **auto-deployed to
dev** → verified manually → **PR-based promotion** to staging (image tag bump only) → 24h soak
+ signature verification gate → **PR-based promotion** to production, requiring CODEOWNERS
(SRE team) approval → manual ArgoCD sync. Full detail: [`docs/architecture.md`](docs/architecture.md).

## Drift Detection & Self-Healing

ArgoCD continuously diffs live cluster state against Git. In dev/staging, `selfHeal: true`
auto-reverts manual/unauthorized changes within one reconciliation cycle. Production
deliberately **disables** auto-heal to preserve operator control during incidents, relying on
Prometheus alerts for visibility instead. Full detail: [`docs/drift-detection.md`](docs/drift-detection.md).

## Vault Integration

Kubernetes-auth-based Vault access, External Secrets Operator syncing secrets into native K8s
Secrets on a 15-minute refresh, least-privilege per-app policies, and full audit logging — with
a documented comparison against Vault Agent Injector and the Secrets Store CSI Driver. Full
detail: [`docs/vault-integration.md`](docs/vault-integration.md).

## Promotion Workflow

Merge-based deploys to dev; **PR-based, image-tag-only promotion** to staging and production,
so every environment transition is a single reviewable line-diff. See
[`docs/architecture.md`](docs/architecture.md) for the sequence diagram and `.github/workflows/`
for the actual pipelines.

## Security Features

Signed + SBOM-attested container images, default-deny NetworkPolicies, `restricted` Pod
Security Standard, least-privilege RBAC, ArgoCD AppProject-scoped team access, and Vault-backed
secrets that never touch Git in plaintext. Full detail: [`docs/security.md`](docs/security.md).

## Observability Features

Prometheus + kube-state-metrics for cluster/app metrics, Loki for centralized logs, Grafana
dashboards-as-code, and Alertmanager routing (drift alerts, deployment-health alerts, resource
pressure alerts) to Slack/PagerDuty by severity.

## Disaster Recovery Features

Vault Raft snapshots to S3 every 6h, Velero cluster backups every 6h/90-day retention,
Terraform-reproducible infrastructure, and a documented RTO/RPO table. Full detail:
[`docs/disaster-recovery.md`](docs/disaster-recovery.md).

## Deployment Instructions

**Local (recommended for demos/interviews):**
```bash
./scripts/bootstrap-local.sh
```
Full walkthrough, including a live drift-detection demo: [`docs/local-setup-guide.md`](docs/local-setup-guide.md).

**Cloud (reference):**
```bash
cd infrastructure/terraform/environments/dev
terraform init && terraform apply
# then follow bootstrap/argocd-install-notes.md against the new cluster
```

## Engineering Decisions

Every major technology choice — ArgoCD vs FluxCD, Kustomize vs Helm, Vault vs K8s Secrets,
trunk-based vs GitFlow, App of Apps, cluster-per-env vs namespace-per-env, promotion model,
observability stack — is documented ADR-style with alternatives, tradeoffs, risks, mitigations,
and rationale in [`docs/engineering-decisions.md`](docs/engineering-decisions.md).

## Lessons Learned

- Disabling `selfHeal` in production is a small config line that represents a real operational
  philosophy: automation should never silently fight an engineer during an active incident.
- Cluster-per-environment costs more than namespace-per-environment, but the isolation
  guarantees are worth it the moment "prod" means real traffic and real money.
- PR-based promotion with a one-line image-tag diff makes audits trivial in a way that
  branch-merge promotion never quite achieves.

## Future Improvements

- Migrate `app-of-apps/` to `ApplicationSet` generators once managed application count grows.
- Add OPA/Kyverno policy-as-code for constraints Pod Security Standards can't express (e.g.
  banning `:latest` tags, restricting allowed registries).
- Add a database secrets engine in Vault for fully dynamic, per-request database credentials.
- Multi-region DR (currently single-region with multi-AZ).

## Senior-Level Talking Points for Interviews

See [`docs/interview-talking-points.md`](docs/interview-talking-points.md) — a cheat sheet for
discussing this project's architecture, scalability, security, reliability, operational
excellence, cost, governance, and risk-management decisions at a Staff/Principal level.

---

**Full documentation index:** [`docs/`](docs/) — architecture, drift detection, Vault
integration, branching strategy, security, disaster recovery, engineering decisions, local
setup guide, and interview talking points.
