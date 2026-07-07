# ArgoCD Bootstrap

ArgoCD is installed once per cluster via Helm (not GitOps-managed for the initial bootstrap,
since ArgoCD must exist before it can manage itself — the classic "chicken and egg" problem).

```bash
kubectl create namespace argocd
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd \
  --namespace argocd \
  --values platform-services/argocd/values.yaml \
  --version 7.6.12
```

After this bootstrap, ArgoCD takes over management of itself via the
`platform-services/argocd` GitOps manifests (self-managing ArgoCD pattern),
and everything else through the App of Apps root application below.
