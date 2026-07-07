# Senior-Level Talking Points for Interviews

Use this as a cheat sheet for walking an interviewer through the project. Don't recite it —
pick the 2-3 threads most relevant to the role and go deep.

## Architectural decisions
"I chose separate clusters per environment over namespace isolation because blast-radius
containment matters more than the extra Terraform/IAM overhead once you're modeling real
production traffic. The tradeoff is cost and cluster-sprawl management, which I mitigated with
a shared hub-cluster ArgoCD instance managing all spokes, so I'm not running N separate GitOps
control planes."

## Scalability considerations
"App of Apps works cleanly at this scale, but I documented the ApplicationSet migration path
for when app count grows past ~20-30 — that's the kind of thing I'd flag in a design review
before it becomes a problem, not after."

## Security considerations
"Supply chain, runtime, GitOps-credential, and secrets-management security are four separate
layers here, each defending against a different compromise scenario. I can walk through what
happens if any single layer fails — e.g., a leaked CI token still can't touch prod because CI
never holds cluster credentials, only Git push access."

## Reliability considerations
"Self-heal is deliberately disabled in production — that's a decision I'd defend in an
interview: automatic reconciliation is right for dev/staging to enforce Git-only discipline,
but during an active prod incident, silently reverting an engineer's manual mitigation is the
wrong tradeoff. Visibility (alerting) without auto-correction is the safer default there."

## Operational excellence
"Every environment promotion is a PR with an isolated, one-line diff (an image tag change),
which means the audit trail answers 'what changed and who approved it' with zero ambiguity —
that was a deliberate design goal, not an accident of tooling."

## Cost optimization
"Node sizing and autoscaling bounds scale up by environment tier — t3.medium/1-3 nodes in dev,
m6i.xlarge/3-12 in prod — and dev clusters are disposable (`kind` locally, spot-friendly in
cloud) since they carry no SLA."

## Governance
"AppProjects encode which teams can touch which clusters/namespaces at the ArgoCD RBAC layer,
and CODEOWNERS enforces required review on Terraform, Vault config, and prod overlays — access
control isn't just 'who can commit to the repo,' it's layered with what that commit is actually
allowed to change once it merges."

## Risk management
"The production promotion pipeline has three independent gates before a human even reviews the
PR: image signature verification, staging soak-time verification, and CI's own vulnerability
scan at build time. No single missed step lets an unverified image reach prod."

## How to frame the project overall
This project demonstrates the difference between "I can write Kubernetes YAML" and "I can
design a platform a team of engineers operates safely for years." The strongest signal to a
Staff/Principal-level panel isn't any single component — it's the visible tradeoff reasoning:
why self-heal is on in dev but off in prod, why clusters are separated instead of namespaces,
why promotion is PR-based instead of branch-merge-based. Lead with the *decisions*, not the
YAML.
