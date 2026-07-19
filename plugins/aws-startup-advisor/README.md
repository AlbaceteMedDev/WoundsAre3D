# aws-startup-advisor

A Claude Code plugin that turns Claude into a pragmatic **AWS advisor for
startups**. It reviews your AWS setup — cost, architecture, security, and
scaling — through the lens of the AWS Well-Architected Framework, but
deliberately adapted for small teams on a tight budget: bias toward
managed/serverless services, avoid premature complexity, keep the monthly bill
legible, and reach a security baseline a 3-person team can actually maintain.
It is portable — it auto-detects your infrastructure-as-code (Terraform, AWS
CDK, CloudFormation/SAM, Pulumi, or raw AWS CLI/boto usage) in whatever repo you
run it in, reads the real config, and gives concrete, repo-specific findings
instead of generic advice.

## Install

From inside Claude Code:

```
/plugin marketplace add AlbaceteMedDev/WoundsAre3D
/plugin install aws-startup-advisor@albacetemeddev
```

Or from the CLI:

```
claude plugin marketplace add AlbaceteMedDev/WoundsAre3D
claude plugin install aws-startup-advisor@albacetemeddev
```

You can also add a local checkout: `claude plugin marketplace add /path/to/WoundsAre3D`.

## What's inside

### Skills

Skills load automatically when your request matches. You don't invoke them
directly — just describe what you need.

- **aws-startup-advisor** — Primary orientation / router skill. Triages a broad
  "help with our AWS" ask and points to the right specialist skill and command.
- **aws-cost-optimization** — Cost control: get visibility, find the top line
  items, right-size, commit, eliminate waste, prevent regressions. Includes a
  detailed cost-trap catalog.
- **aws-architecture-review** — Startup-adapted Well-Architected review and
  service selection (Lambda vs Fargate vs EC2 vs EKS, data stores, async). When
  a VPC/NAT is actually needed; managed vs self-hosted.
- **aws-security-baseline** — The minimum viable security baseline in priority
  order (identity → guardrails → data → network → detection), with a grouped,
  actionable checklist.
- **aws-scaling-plan** — A staged roadmap (MVP → early traction → scaling →
  scale) describing what to add at each stage, and just as importantly, what
  NOT to add yet.

### Commands

- **/aws-startup-advisor:aws-cost-review** — Cost audit → ranked savings
  opportunities with rough effort/impact. Applies the `aws-cost-optimization`
  skill.
- **/aws-startup-advisor:aws-architecture-review** — Well-Architected-lite review
  across the 6 pillars, startup-weighted. Applies the `aws-architecture-review`
  skill.
- **/aws-startup-advisor:aws-security-baseline** — Audit against the security
  baseline checklist; report gaps by severity. Applies the
  `aws-security-baseline` skill.
- **/aws-startup-advisor:aws-scaling-plan** — Produce a staged scaling roadmap for
  the current system, optionally targeting a scenario passed as an argument
  (e.g. "10x traffic", "Product Hunt launch"). Applies the `aws-scaling-plan`
  skill.

### Agent

- **aws-advisor** — A read-only AWS reviewer Claude can delegate deep-dive
  reviews to. It reads your IaC/config, reasons with the Well-Architected +
  startup-pragmatic lens, and returns structured findings (severity, area,
  finding, impact, recommended fix, effort). Strictly advisory: it never
  modifies files and never runs mutating AWS commands.

## How to use

Just talk to Claude in natural language — the skills trigger on their own:

- "Review our AWS setup — are we set up well?"
- "Our AWS bill jumped this month, help me cut costs."
- "Should we use Lambda or Fargate for this service?"
- "Are we secure on AWS? We're starting a SOC 2 audit."
- "We're launching on Product Hunt next week — will we hold up?"

Or drive a focused review with a slash command:

```
/aws-startup-advisor:aws-cost-review
/aws-startup-advisor:aws-architecture-review
/aws-startup-advisor:aws-security-baseline
/aws-startup-advisor:aws-scaling-plan 10x traffic
```

Each command auto-detects and reads your IaC, applies the matching skill's
framework, and returns a **prioritized, actionable report** (P0/P1/P2) where
every finding is problem → impact → concrete fix, ideally a diff or exact
change.

## Design philosophy

Startup-pragmatic Well-Architected. The six pillars (Operational Excellence,
Security, Reliability, Performance Efficiency, Cost Optimization, and
Sustainability) are the backbone, but early on **Cost Optimization and
operational simplicity dominate** — a 5-person team should not run a
multi-region EKS fleet. The plugin recommends the simplest thing that works,
calls out when a "best practice" is premature, and always weighs
cost/complexity against benefit. It ties every recommendation to how Claude can
act in your repo: read the IaC, grep for the anti-pattern, propose the concrete
diff.

## Disclaimer

This plugin is **not affiliated with, endorsed by, or a substitute for Amazon
Web Services or its own tooling** (AWS Well-Architected Tool, Trusted Advisor,
Cost Explorer, Security Hub, and so on). It provides advisory guidance only and
does not make changes to your AWS account. AWS services, limits, pricing, and
best practices change frequently — **always verify current pricing and
practices against the official AWS documentation** before acting, and treat any
cost figures as illustrative, not quotes. For regulated workloads (SOC 2,
HIPAA, PCI, etc.), confirm requirements with your compliance and security
advisors.

## License

MIT
