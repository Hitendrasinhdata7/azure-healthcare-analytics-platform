# Security Architecture

## Supply Chain Security
- **Image scanning**: Trivy blocks CRITICAL/HIGH CVEs at CI time before an image is ever pushed.
- **Signing**: every image is signed with `cosign` using keyless (Sigstore/OIDC) signing tied to the GitHub Actions identity — no long-lived signing keys to leak.
- **SBOM**: CycloneDX SBOM generated per build and attached as a signed attestation, giving downstream consumers (and auditors) a verifiable dependency manifest.
- **Provenance**: the production promotion gate (`promote-prod.yaml`) verifies the cosign signature before allowing a promotion PR, so an unsigned or tampered image can never reach prod even if someone bypasses CI.

## Kubernetes Security
- **RBAC**: least-privilege `Role`/`RoleBinding` per application ServiceAccount (see `apps/sample-service/base/rbac.yaml`) — no ServiceAccount gets cluster-admin.
- **Network Policies**: default-deny-all per namespace, with narrow explicit allows (ingress only from `ingress-nginx`, egress only to DNS + Vault) — zero-trust east-west traffic.
- **Pod Security Standards**: `restricted` profile enforced at the namespace level (non-root, no privilege escalation, dropped capabilities, read-only root filesystem).
- **Least privilege**: `ResourceQuota` + `LimitRange` bound every namespace's blast radius on both permissions and compute.

## GitOps Security
- **Repository permissions**: CI only ever has *push* access to Git (to bump image tags); it never holds cluster credentials. Only ArgoCD (running inside the cluster) has apply access.
- **ArgoCD RBAC**: `AppProject`s scope which clusters/namespaces each team can touch (see `bootstrap/argocd-projects/*.yaml`) — dev engineers cannot sync a change into `prod-*` namespaces even if they wanted to.
- **Secret protection**: no plaintext secret value is ever committed to Git; `ExternalSecret` manifests describe *references* to Vault paths only.

## Vault Security
- **Authentication**: Kubernetes auth method — no static tokens distributed to workloads.
- **Authorization**: per-application least-privilege policies scoped to a single secret path.
- **Audit logs**: every secret access is logged for compliance review and incident forensics.

## Architectural justification

Each control here maps to a specific attack surface: supply-chain controls stop a compromised dependency or build step from reaching production; Kubernetes-native controls contain a *runtime* compromise (a compromised pod can't reach other namespaces or escalate privilege); GitOps/ArgoCD RBAC contains a *credential* compromise (a leaked dev-team GitHub token still can't touch prod); Vault controls contain a *secret* compromise (a leaked Vault token is scoped to one path and short-lived where dynamic secrets are used). Defense in depth: no single control is asked to be the only thing standing between an attacker and production.
