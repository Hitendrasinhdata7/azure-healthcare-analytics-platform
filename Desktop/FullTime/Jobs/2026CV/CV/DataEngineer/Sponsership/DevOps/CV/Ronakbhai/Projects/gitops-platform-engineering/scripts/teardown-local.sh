#!/usr/bin/env bash
set -euo pipefail
kind delete cluster --name gitops-platform-local
echo "Local cluster removed."
