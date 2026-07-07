# HashiCorp Vault Integration

## Why Kubernetes Secrets alone are insufficient

- **Base64 is encoding, not encryption.** Native `Secret` objects are base64-encoded strings stored in etcd; without envelope encryption enabled (and even then, encrypted only at rest, not in transit within manifests) anyone with `get secrets` RBAC or etcd access reads them in plaintext.
- **Secret sprawl.** Secrets committed to Git (even "sealed" ones without a rotation strategy) accumulate across dozens of repos/namespaces with no central audit trail of who accessed what, when.
- **No native rotation.** Kubernetes has no built-in credential lifecycle — a leaked DB password requires manual find-and-replace across every manifest that references it.

## Vault architecture used in this platform

- **Kubernetes auth method**: workloads authenticate to Vault using their own ServiceAccount JWT — no static Vault tokens distributed to pods.
- **KV v2 secrets engine**: versioned static secrets (`secret/data/sample-service/*`), with the option to add **database secrets engine** for fully dynamic, short-lived DB credentials generated per-request.
- **Scoped policies + roles**: each application gets a Vault role bound to exactly its namespace + ServiceAccount name, with a policy granting read-only access to only its own secret path (least privilege, see `platform-services/vault/policies.yaml`).
- **Raft integrated storage, HA mode, 3 replicas**: no external Consul dependency, tolerates single-node failure.
- **Audit logging** enabled to a dedicated storage backend for compliance (every secret read is logged with requester identity).

## Comparing secret-injection approaches

| Approach | How it works | Chosen? | Why |
|---|---|---|---|
| **Vault Agent Injector** | Sidecar injects secrets as files into the pod at startup via mutating webhook | No | Couples secret refresh to pod restarts/sidecar lifecycle; heavier per-pod overhead |
| **External Secrets Operator (ESO)** | Controller syncs Vault secrets into native K8s Secrets on an interval | **Yes** | Decouples secret refresh from pod lifecycle, works with any consumer of a normal Secret (env vars, volumes), is itself GitOps-managed declaratively (`ExternalSecret` CRD lives in Git) |
| **Secrets Store CSI Driver** | Mounts secrets as a volume directly from Vault, no intermediate K8s Secret | No (but valid alternative) | Avoids ever materializing a K8s Secret at all (stronger security posture) but has less mature rotation-on-change support and doesn't fit teams already standardized on `envFrom: secretRef` |

**Decision: External Secrets Operator.** It's declarative (fits the GitOps model — the `ExternalSecret` manifest itself lives in Git, describing *what* to sync without ever containing the secret value), broadly compatible with existing Deployment patterns, and its `refreshInterval` gives a simple, observable rotation mechanism.

## Rotation strategy

1. Vault-side: static secrets versioned in KV v2; dynamic DB credentials (if enabled) have TTL/max-TTL enforced by Vault itself.
2. ESO polls on `refreshInterval: 15m` and rewrites the K8s Secret if the Vault value changed.
3. Pods consuming the Secret via `envFrom` require a rolling restart to pick up new env vars — handled by a `reloader`-style controller (e.g. Stakater Reloader) watching Secret hashes and triggering a rollout, kept fully GitOps/controller-driven rather than manual.
4. All reads are audit-logged in Vault for compliance review.
