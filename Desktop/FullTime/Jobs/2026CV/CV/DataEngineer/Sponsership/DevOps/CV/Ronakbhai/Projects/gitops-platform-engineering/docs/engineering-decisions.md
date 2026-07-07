# Engineering Decisions (ADR-style)

## ArgoCD vs FluxCD
- **Decision**: ArgoCD.
- **Alternatives considered**: FluxCD (GitOps Toolkit).
- **Tradeoffs**: Flux is more lightweight/composable (separate controllers per concern) and arguably more "Kubernetes-native"; ArgoCD bundles a UI, RBAC model, and App-of-Apps pattern out of the box, which matters more for multi-team platform adoption than for a single pipeline.
- **Risks**: ArgoCD's monolithic-ish architecture (fewer, larger controllers) can be a scaling bottleneck at very large app counts (1000s of Applications) without sharding the application-controller.
- **Mitigations**: `controller` sharding by cluster, ApplicationSets for templated app generation instead of hand-writing hundreds of Application manifests.
- **Why ArgoCD**: the built-in UI and AppProject RBAC model directly serve this project's goals — recruiter/interviewer visibility into sync state, and clean team-scoped access control without bolting on extra tooling.

## Kustomize vs Helm
- **Decision**: Kustomize for application overlays; Helm reserved for third-party charts (ArgoCD, Vault, ingress-nginx, kube-prometheus-stack).
- **Tradeoffs**: Helm's templating is more powerful (loops, conditionals) but introduces a templating language on top of YAML, harder to `diff` cleanly, and encourages "one giant values.yaml" complexity creep. Kustomize's patch-based overlays keep base manifests as plain, valid YAML at every layer, and diffs between environments are just `git diff`.
- **Risks**: Kustomize is less expressive for deeply parameterized logic.
- **Mitigations**: use Helm exactly where the ecosystem already standardized on it (installing third-party software), and Kustomize for everything this team authors and needs to diff/review.
- **Why this split**: it matches how each tool is strongest — Helm for "install someone else's software," Kustomize for "manage our own manifests across environments."

## Vault vs Kubernetes Secrets
- Covered in detail in `vault-integration.md`. Summary: base64 ≠ encryption, no native rotation, no audit trail — Vault + ESO solves all three while staying GitOps-declarative.

## Trunk-Based Development vs GitFlow
- Covered in detail in `branching-strategy.md`. Summary: GitFlow's long-lived branches fight GitOps' single-source-of-truth-per-environment model; trunk-based + overlay directories keep "what's live" unambiguous.

## App of Apps Pattern
- **Decision**: adopt App of Apps as the single bootstrap entrypoint.
- **Alternatives considered**: manually applying N separate ArgoCD Applications.
- **Tradeoffs**: adds one layer of indirection (an Application that manages other Applications) but reduces bootstrap to a single `kubectl apply -f root-app.yaml`.
- **Risks**: at very large scale, a flat list of Application manifests under `app-of-apps/` becomes unwieldy.
- **Mitigations**: migrate to ApplicationSets with a generator (e.g. Git directory generator) once app count grows past what's comfortably hand-maintained (roughly 20-30+).
- **Why chosen**: for this project's scope, App of Apps is simpler to reason about and demonstrate than the added abstraction of ApplicationSets, while still being the recognized enterprise entrypoint pattern.

## Multi-Environment Strategy (separate clusters vs. separate namespaces)
- **Decision**: separate clusters per environment.
- **Tradeoffs**: more infrastructure to manage and higher cost than namespace-per-env, but eliminates entire classes of risk (a prod-scoped RBAC bug can't reach dev; a noisy-neighbor dev workload can't starve prod control-plane resources).
- **Why chosen**: blast-radius isolation is worth the operational overhead for anything handling real production traffic; namespace-isolation is acceptable for genuinely low-stakes internal tools, which this platform is explicitly not modeling.

## Promotion Model (merge-based vs. PR-based vs. image-tag promotion)
- **Decision**: PR-based promotion of image tags between overlay directories.
- **Tradeoffs**: adds pipeline complexity (workflow_dispatch + PR automation) versus a simple branch merge, but every environment transition becomes independently reviewable and auditable, and never accidentally carries unrelated manifest changes along with it (which a `git merge dev->staging` risks).
- **Why chosen**: it isolates *what* is being promoted (an image tag) from *how the environment is configured* (the overlay), so a promotion PR's diff is exactly one line — trivially reviewable, even under time pressure.

## Observability Stack (kube-prometheus-stack + Loki vs. a commercial SaaS APM)
- **Decision**: self-hosted Prometheus/Grafana/Loki/Alertmanager.
- **Tradeoffs**: more operational ownership than a SaaS vendor (Datadog, New Relic), but zero per-host licensing cost, full data ownership, and every alert/dashboard is itself GitOps-managed (dashboards-as-code, alerts-as-code) rather than living in a vendor's proprietary UI.
- **Why chosen**: it keeps the entire platform's observability configuration inside the same audit/version-control trail as everything else — consistent with the project's GitOps-first philosophy end to end.
