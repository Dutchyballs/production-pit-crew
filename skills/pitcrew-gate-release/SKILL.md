---
name: pitcrew-gate-release
description: Make an independent evidence-based release decision for a feature, interface, or application by comparing requirements with implementation, verification results, unresolved defects, operational readiness, and rollback safety. Use before release, handoff, merge, or production-readiness claims when the reviewer must return a fair PASS, HOLD, or BLOCKED decision without default failure or inflated approval.
---

# Gate Release

Decide whether the defined release can proceed. Evaluate agreed scope and risk; do not redesign the product or manufacture faults.

## Decision Meanings

- **PASS:** Required outcomes are verified, no release-blocking defect remains, and operational controls match the risk.
- **HOLD:** Evidence proves a required outcome fails or a known risk exceeds the agreed tolerance.
- **BLOCKED:** A fair decision cannot be made because required evidence, environment, access, or an authoritative requirement is missing.

Never use BLOCKED to hide a known failure. Never use HOLD merely because a first implementation is imperfect.

## Workflow

1. Freeze decision scope.
   - Identify the build, commit, feature set, environment, intended audience, and release target.
   - Read authoritative requirements, acceptance criteria, interface contract, change summary, and verification evidence.
   - Exclude unrequested enhancements and personal preferences.
2. Check evidence integrity.
   - Confirm evidence applies to the candidate build and relevant environment.
   - Distinguish executed checks from claims, source inspection, mocks, and assumptions.
   - Identify stale, partial, contradictory, or missing evidence.
3. Evaluate required outcomes.
   - Map each requirement to pass, fail, or unverified evidence.
   - Check critical journeys, failure recovery, accessibility, security and privacy, data safety, compatibility, performance, observability, migration, and rollback only where relevant.
4. Classify findings.
   - Block release only for a violated requirement or material risk.
   - Separate blockers, significant non-blocking defects, minor defects, and future improvements.
   - State user impact, reproduction or evidence, and required action.
5. Make the decision.
   - PASS when the release bar is met, even if minor follow-ups exist.
   - HOLD when a concrete blocker exists.
   - BLOCKED when decision-grade evidence cannot be obtained.
6. Define the shortest path to PASS.
   - For HOLD, name fixes and exact re-verification.
   - For BLOCKED, name the missing evidence or decision.

## Report Format

~~~markdown
# Release Gate: [candidate]

## Decision: PASS | HOLD | BLOCKED
[Concise evidence-based rationale.]

## Scope and evidence
- Candidate: [...]
- Requirements: [...]
- Verification reviewed: [...]
- Limits: [...]

## Requirement matrix
| Requirement | Evidence | Status |
| --- | --- | --- |
| [...] | [...] | Pass / Fail / Unverified |

## Release blockers
1. [Finding, impact, evidence, required action]

## Non-blocking follow-ups
- [...]

## Path to PASS
- [Action] — re-verify with [method]
~~~

Omit empty sections. Do not assign letter grades, readiness percentages, or invented scores.

## Quality Rules

- Keep the gate independent from implementation. Do not silently fix findings while deciding.
- Accept evidence proportionate to risk; a local prototype and a destructive migration require different bars.
- Do not claim production readiness when only a component or happy path was tested.
- Do not require screenshots for non-visual claims when tests, logs, traces, or inspections are stronger.
- Treat zero observed issues as possible, not suspicious.
- Preserve explicit residual risks in a PASS decision.
- Redact secrets and personal data from the report.

Read references/release-evidence-model.md for risk-based evidence selection and finding severity.
