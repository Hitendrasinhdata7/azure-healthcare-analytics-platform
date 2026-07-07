# Drift Detection and Self-Healing

## What counts as drift

| Scenario | Example | How ArgoCD Detects It |
|---|---|---|
| Manual config change | An engineer runs `kubectl edit deploy` on a live Deployment | Live-state diff shows a field that doesn't match the rendered Git manifest → `OutOfSync` |
| Unauthorized change | A compromised credential scales a Deployment to 0 | Same diff mechanism; `selfHeal` reverts within one reconciliation cycle (default 3 min, can be event-driven via `kubectl` watch informers for near-instant detection) |
| Resource deletion | Someone deletes a ConfigMap directly | ArgoCD sees the expected resource missing from live state → recreates it |
| Cluster-level drift | A cloud console change alters a LoadBalancer's annotations | Detected the same way if the resource is Git-managed; unmanaged infra drift (e.g. raw AWS console changes) is instead caught by **Terraform plan** in CI, not ArgoCD |

## Self-Healing mechanics

`syncPolicy.automated.selfHeal: true` (set on dev/staging Applications, deliberately **omitted** on prod) makes ArgoCD:

1. Detect the diff between live and desired state.
2. Re-apply the Git-defined manifest, overwriting the manual change.
3. Emit a Kubernetes event and (via `argocd-notifications`) a Slack alert to `#gitops-drift`.
4. Prometheus's `ArgoCDAppOutOfSync` alert (see `platform-services/observability/prometheus/drift-alerts.yaml`) fires if a resource stays out-of-sync for >10 minutes, which should be rare since self-heal is nearly immediate — a persistent alert usually means the *live* state is being changed faster than ArgoCD can correct it (a signal of an active incident, not just drift).

## Why production disables `selfHeal`

In dev/staging, silently reverting manual changes is desirable — it enforces "everything through Git" discipline early and cheaply. In production, an engineer's manual intervention during an active incident (e.g. temporarily scaling up to handle a traffic spike) should **not** be auto-reverted mid-incident. Instead, prod relies on:
- Alerting on drift (visibility without auto-correction)
- A deliberate `argocd app sync` (or a follow-up Git commit) to reconcile once the incident is over

This is a senior-level tradeoff: **automation vs. operator control** during an active incident.
