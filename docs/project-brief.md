# Project brief

## Product

**Production Pit Crew** is a focused set of reusable specialists that helps a primary coding agent turn a request into production-quality software. It adds planning, interface definition, independent browser verification, code review, finish criticism, and evidence-based release gating without pretending to be an autonomous company or persistent memory system.

The first release is **Production Pit Crew for Codex**.

## Users

- Builders who want higher-quality GUI and UI work without prescribing a framework or visual trend.
- Small teams that need repeatable planning, verification, review, and handoff evidence.
- Agent users who want independent specialist judgment without a large prompt collection.

## v0.1 outcome

A user can install or package the four skills, add the Codex custom agents where supported, invoke only the stages relevant to a task, and receive concrete artifacts that another developer can inspect and verify.

## In scope

- Four portable Agent Skills.
- Four focused Codex custom agents.
- OpenAI plugin packaging for the skills.
- Safe project/user installation, validation, upgrade, and uninstall on supported platforms.
- Honest evidence semantics, clean-review support, and proportional workflows.
- Documentation, CI, release archives, attribution, and security guidance.

## Out of scope for v0.1

- Autonomous agent-to-agent orchestration.
- Persistent memory or background operation.
- A replacement for dedicated security, privacy, migration, performance, or incident-readiness workflows.
- Claims that untested host adapters are supported.

## Success criteria

- Every shipped skill and agent passes strict structural and prompt-hygiene validation.
- Install, conflict, upgrade, rollback, and uninstall behavior is covered by isolated tests.
- Existing preview installs migrate only when exact historical ownership is proven.
- The Codex workflow produces observable plans, interface contracts, verification evidence, reviews, and release decisions.
- Documentation clearly separates portable core behavior from Codex-specific configuration.
