# `albacetemeddev` — Claude Code plugin marketplace

This directory is a **Claude Code plugin marketplace** published by Albacete
MedDev. A marketplace is just a repository that Claude Code can register once and
then install one or more plugins from. The marketplace manifest lives at
[`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) in the
repo root; the plugins themselves live in subdirectories here under `plugins/`.

## Why it's named `albacetemeddev`

The name `claude-plugins-official` is **reserved by Anthropic** for the official
plugin marketplace, so third-party marketplaces cannot use it. This one is named
`albacetemeddev` after its publisher. When you install a plugin you reference it
as `<plugin>@albacetemeddev` (see below).

## Plugins in this marketplace

### `aws-startup-advisor`

Turns Claude into a pragmatic **AWS advisor for startups** — seed / Series-A
teams with small headcount and a tight budget shipping on AWS. It is grounded in
the AWS Well-Architected Framework but deliberately adapted for startups: bias
toward managed and serverless services, avoid premature complexity, keep the
monthly bill legible, and reach a security baseline that a 3-person team can
actually maintain.

The plugin is **portable** — it runs in whatever repository you install it into
and auto-detects your infrastructure-as-code (Terraform, AWS CDK,
CloudFormation/SAM, Pulumi, or raw AWS CLI/boto usage) rather than assuming a
specific project.

What's inside:

- **5 skills** — a primary router skill (`aws-startup-advisor`) plus specialists
  for cost optimization, architecture review, the security baseline, and a
  scaling plan.
- **4 slash commands** — `/aws-startup-advisor:aws-cost-review`,
  `/aws-startup-advisor:aws-architecture-review`,
  `/aws-startup-advisor:aws-security-baseline`, and
  `/aws-startup-advisor:aws-scaling-plan`.
- **1 subagent** — `aws-advisor`, a strictly read-only AWS reviewer that Claude
  can delegate deep-dive reviews to.

Full details, usage, and design philosophy are in the plugin's own README:
[`plugins/aws-startup-advisor/README.md`](./aws-startup-advisor/README.md).

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

(You can also add a local checkout: `claude plugin marketplace add /path/to/WoundsAre3D`.)

## Disclaimer

The plugins here are **not affiliated with, endorsed by, or a substitute for
AWS's own tools** (Well-Architected Tool, Cost Explorer, Trusted Advisor,
Security Hub, etc.). They provide advisory guidance only. AWS pricing, service
limits, and best practices change frequently — **always verify current pricing
and practices in the official AWS documentation** before acting on a
recommendation.

## License

MIT.
