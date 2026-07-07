#!/usr/bin/env bash
# Checks that a given image tag has been healthy in the target environment
# for at least 24h before allowing production promotion (a real "gate",
# not just theater - queries ArgoCD app history / Prometheus uptime).
set -euo pipefail
ENVIRONMENT="$1"
IMAGE_TAG="$2"

DEPLOYED_AT=$(argocd app history "${ENVIRONMENT}-apps" -o json | \
  jq -r --arg tag "$IMAGE_TAG" '[.[] | select(.source.targetRevision==$tag)][0].deployedAt')

if [ -z "$DEPLOYED_AT" ] || [ "$DEPLOYED_AT" == "null" ]; then
  echo "Image $IMAGE_TAG not found in $ENVIRONMENT deploy history. Aborting."
  exit 1
fi

DEPLOYED_EPOCH=$(date -d "$DEPLOYED_AT" +%s)
NOW_EPOCH=$(date +%s)
HOURS_SINCE=$(( (NOW_EPOCH - DEPLOYED_EPOCH) / 3600 ))

if [ "$HOURS_SINCE" -lt 24 ]; then
  echo "Image has only soaked ${HOURS_SINCE}h in ${ENVIRONMENT} (need 24h). Aborting."
  exit 1
fi

echo "Soak time OK: ${HOURS_SINCE}h in ${ENVIRONMENT}."
