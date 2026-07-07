# Pod Security Standard: `restricted`

Every application namespace enforces the Kubernetes **restricted** Pod
Security Standard (see `apps/sample-service/base/namespace.yaml` labels).
This requires, cluster-wide, without exception:

- `runAsNonRoot: true`
- No privilege escalation (`allowPrivilegeEscalation: false`)
- All Linux capabilities dropped (`capabilities.drop: ["ALL"]`)
- `readOnlyRootFilesystem: true` where the workload allows it
- Seccomp profile `RuntimeDefault`

Enforcement is admission-time (native PSA, optionally layered with
Kyverno/OPA Gatekeeper in a real enterprise rollout for custom policies
PSA can't express, e.g. "no `:latest` tags", "no privileged registries").
