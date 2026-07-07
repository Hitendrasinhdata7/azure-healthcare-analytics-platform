# Branching Strategy

## Comparison

| Strategy | Advantages | Disadvantages |
|---|---|---|
| **GitFlow** | Clear release/hotfix structure; good for scheduled, versioned releases | Heavyweight; long-lived `develop`/`release` branches drift from `main`, which fights GitOps' "one source of truth per environment" principle |
| **Trunk-Based Development** | Single `main`, short-lived feature branches, fast integration, minimal merge conflicts, pairs naturally with continuous deployment to dev | Requires strong CI gating and feature flags for incomplete work, since `main` must always stay releasable |
| **Environment Branches** (`dev`/`staging`/`main` as environments) | Intuitive mapping of branch→environment | Anti-pattern for GitOps: environment state should live in **overlay directories**, not branches — branch-per-env causes painful cherry-picks and makes "what's actually running in prod" ambiguous (is it the tip of the branch? which commit?) |

## Decision: Trunk-Based Development + directory-based environments

A single `main` branch holds all history. **Environments are expressed as Kustomize overlay directories** (`apps/*/overlays/{dev,staging,prod}`), not branches. This means:

- What's running in any environment is always exactly "the content of `overlays/<env>` at commit SHA X" — unambiguous and auditable.
- Promotion is a PR that changes an image tag in an overlay directory (see `promote-staging.yaml` / `promote-prod.yaml`), not a merge between long-lived branches.
- No branch ever needs rebasing against another to "catch up" to prod — there's nothing to catch up to.

## Workflow examples

- **Feature branch**: `feature/add-readiness-probe` → PR into `main` → CI (lint, scan, build, sign) → merge → auto-deployed to dev.
- **Pull request**: every environment transition (dev→staging, staging→prod) is itself a PR against the relevant overlay, giving a reviewable diff and required approvals (CODEOWNERS) rather than an implicit branch merge.
- **Release**: a Git tag (`v1.0.0`) is cut once the corresponding image has been promoted through staging and prod's promotion PR is merged — the tag documents "what actually went to prod," it doesn't drive deployment itself.
- **Hotfix**: `hotfix/fix-oom-crash` branches from `main`, goes through the same CI gates (no skipped scanning, even under pressure), merges to `main`, and is fast-tracked through the same dev→staging→prod promotion PRs — compressed timeline, not a bypassed process.
