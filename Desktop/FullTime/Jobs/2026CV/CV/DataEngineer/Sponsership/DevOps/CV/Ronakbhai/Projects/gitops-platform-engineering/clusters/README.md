# Cluster Registration

Each environment is a **physically separate cluster** (not just a namespace),
which is the recommended enterprise pattern because it provides:

- Blast-radius isolation (a prod incident cannot touch dev/staging control plane)
- Independent upgrade cadence (test Kubernetes version bumps in dev first)
- Separate IAM/network boundaries per environment
- True production-parity testing in staging

ArgoCD is installed once, in a dedicated "hub" management cluster, and
registers dev/staging/prod as remote target clusters (hub-spoke model).
This is why `clusters/<env>/cluster-secret.yaml` exists — it is how
ArgoCD authenticates to each spoke cluster.
