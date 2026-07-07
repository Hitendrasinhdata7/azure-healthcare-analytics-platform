#!/usr/bin/env bash
# One-command local bootstrap of the entire GitOps platform on kind.
# Usage: ./scripts/bootstrap-local.sh
set -euo pipefail

CLUSTER_NAME="gitops-platform-local"

echo "==> Creating local kind cluster"
kind create cluster --name "$CLUSTER_NAME" --config scripts/kind-cluster-config.yaml

echo "==> Installing ArgoCD"
kubectl create namespace argocd
helm repo add argo https://argoproj.github.io/argo-helm --force-update
helm install argocd argo/argo-cd -n argocd -f platform-services/argocd/values.yaml \
  --set server.ingress.enabled=false --set server.service.type=ClusterIP --wait

echo "==> Installing Vault (dev mode, single replica for local use only)"
helm repo add hashicorp https://helm.releases.hashicorp.com --force-update
helm install vault hashicorp/vault -n vault --create-namespace \
  --set server.dev.enabled=true --set server.ha.enabled=false --wait

echo "==> Applying App of Apps (root application)"
kubectl apply -f bootstrap/app-of-apps/root-app.yaml

echo "==> Port-forwarding ArgoCD UI to https://localhost:8081"
kubectl -n argocd port-forward svc/argocd-server 8081:443 &

echo ""
echo "Bootstrap complete."
echo "ArgoCD UI:       https://localhost:8081"
echo "ArgoCD admin pw: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
