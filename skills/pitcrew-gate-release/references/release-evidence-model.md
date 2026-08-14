# Release Evidence Model

Use this model to choose a proportionate gate and classify findings consistently.

## Contents

- Evidence strength
- Risk-based evidence
- Severity model
- Decision traps

## Evidence Strength

For a behavioral claim, prefer:

1. repeatable execution against the candidate build;
2. trace, recording, logs, network output, or other runtime evidence;
3. targeted screenshot for a visual-state claim;
4. source inspection showing the implemented path;
5. configuration or documentation claim;
6. assumption.

The ordering depends on the claim. Source inspection can be strongest for static configuration; a screenshot can be strongest for exact appearance.

Require evidence identity: build or commit, environment, test data, method, and date when staleness matters.

## Risk-Based Evidence

### Low-risk prototype

- primary journey executes;
- obvious failures are recoverable;
- no real user data or production credentials are involved;
- limitations are documented.

### Internal application or ordinary feature

- changed and adjacent critical journeys pass;
- relevant automated tests pass;
- responsive and accessibility checks cover changed UI;
- errors, permissions, and observability are adequate;
- deployment has a recovery path.

### High-risk change

Examples include authentication, payments, privacy-sensitive data, destructive actions, public APIs, security controls, or irreversible migration.

Require as relevant:

- independent review;
- negative and permission tests;
- representative environment;
- backup and rollback proof;
- migration rehearsal;
- monitoring and alert ownership;
- incident or support procedure;
- explicit residual-risk acceptance by the appropriate owner.

Do not let a large screenshot set substitute for these controls.

## Severity Model

- **Blocker:** Violates a required outcome or creates credible severe harm with no acceptable control.
- **Significant:** Materially harms a supported journey but has an accepted workaround or limited exposure.
- **Minor:** Real defect with limited impact that does not defeat the release outcome.
- **Follow-up:** Improvement or risk reduction, not a demonstrated defect.

Every blocker must name the affected requirement or risk, impact, evidence, corrective action, and re-verification.

## Decision Traps

- **Default failure:** Treating scepticism as evidence.
- **Approval theatre:** Calling a release ready because a checklist exists.
- **Evidence volume:** Mistaking many screenshots or tests for relevant coverage.
- **Stale proof:** Reusing results from a different build.
- **Scope inflation:** Blocking on features or polish never required.
- **Happy-path approval:** Ignoring failure recovery, permissions, or data safety where they matter.
- **Grade laundering:** Replacing a clear decision with a subjective score.
