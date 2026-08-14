# Origin, ownership, attribution, and claims

This document records what Production Pit Crew can honestly claim, what informed
it, and which notices must remain with redistributed copies. It is a practical
project record, not a substitute for advice from an intellectual-property
lawyer in a particular country.

## What is original to this project

The project claims copyright in its original expression and implementation,
including its code, documentation, original project assets, the selected and
arranged four-role workflow, the Codex agent and Agent Skill adaptations, the
dependency-free safe installer, Windows handle-pinned filesystem adapter,
ownership/state format, validation suite, release builder, tests, and CI
configuration. The project name is branding and is not claimed as a copyright
work merely because it appears in those materials.

This claim is limited to the material actually created and arranged for this
project. It does not claim ownership of general software-delivery methods,
public standards, platform APIs, Agent Skill or plugin formats, third-party
products, or upstream material identified below.

## What informed the project

Agency Agents provided useful examples of specialist workflow roles. Production
Pit Crew retained the ideas of repository-aware planning, minimal complete
changes, independent review, running-product verification, accessibility-aware
design, and evidence-based release decisions. The prompts were rewritten and
substantially narrowed rather than installed wholesale. The exact conceptual
mapping is recorded in [Honourable mentions](honourable-mentions.md).

Agency Agents remains copyright its contributors and is MIT licensed. Its full
copyright and permission notice is reproduced in
[Third-party notices](../THIRD_PARTY_NOTICES.md).

## Distribution terms

Production Pit Crew is released under the [MIT License](../LICENSE). Anyone may
use, copy, modify, merge, publish, distribute, sublicense, or sell copies under
that licence, provided the Production Pit Crew copyright and permission notice
remain with copies or substantial portions.

Redistributors should keep these files together:

- `LICENSE` — Production Pit Crew licence and warranty disclaimer.
- `THIRD_PARTY_NOTICES.md` — upstream attribution and the complete upstream MIT
  notice.
- `docs/origin-and-claims.md` — provenance, ownership limits, and permitted
  product claims.

The MIT licence grants broad copyright permission but does not transfer
third-party trademarks, imply endorsement, provide a warranty, certify security,
or promise fitness for a particular purpose.

## Safe public wording

Appropriate descriptions include:

- "Production Pit Crew is an independently developed, MIT-licensed workflow
  pack for Codex."
- "It contains original installer, safety, validation, packaging, and workflow
  adaptation work, informed by selected Agency Agents ideas under the MIT
  licence."
- "It is designed for Codex compatibility but is not affiliated with or
  endorsed by OpenAI."

Avoid claims that it is an official OpenAI product, that all workflow concepts
were invented here, that it owns the Codex or Agent Skill formats, that it is
security certified, or that an unverified candidate is production released.

## Repository dependency and asset record

- Runtime code uses Python's standard library and Windows platform APIs only.
- Bash and PowerShell are thin launch wrappers, not bundled runtimes.
- CI references official GitHub-hosted actions; their source is fetched during
  CI and is not included in release archives.
- Project icons are distributed as project assets; no third-party logo or font
  is included.
- The project currently contains no vendored third-party package tree.

If future work copies code, prompts, icons, fonts, templates, models, datasets,
or other assets, update this record and `THIRD_PARTY_NOTICES.md` before release.
