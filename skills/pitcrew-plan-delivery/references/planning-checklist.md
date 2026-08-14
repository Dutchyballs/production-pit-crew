# Planning Checklist

Use this reference when work is large, ambiguous, cross-cutting, or high-risk.

## Contents

- Evidence audit
- Scope audit
- Slice design
- Acceptance criteria
- Risk controls
- Common planning failures

## Evidence Audit

- Identify the authoritative requirement source.
- Inspect the current implementation before prescribing a replacement.
- Record the active runtime, framework, package manager, test runner, and deployment boundary when relevant.
- Distinguish existing behavior from desired behavior.
- Label anything inferred from naming, incomplete docs, or a partial code trace.

## Scope Audit

For every proposed item, answer one of:

- Which requested outcome requires it?
- Which existing dependency makes it necessary?
- Which material risk does it control?

If none applies, remove it or label it as an optional follow-up.

Record non-goals that prevent likely scope drift.

## Slice Design

Prefer vertical slices that finish one real journey:

1. Entry or trigger
2. Validation and state transition
3. Core behavior
4. User-visible or machine-verifiable result
5. Focused tests

Avoid plans where all infrastructure is built first and no usable path completes until the final step.

Good slice:

> A user can import one supported flight log, see validation errors, and open the resulting replay.

Weak slice:

> Build the frontend, then build the backend, then add tests.

## Acceptance Criteria

Write criteria as observable behavior.

| Weak | Testable |
| --- | --- |
| The form is user-friendly. | Submitting an empty required field keeps entered values, places an error beside the field, and moves focus to the error summary. |
| Mobile works. | The primary journey completes at the selected narrow viewport without horizontal scrolling or hidden controls. |
| Errors are handled. | A rejected import shows a safe explanation, preserves the original file, and creates no partial record. |

Include a verification method:

- automated test and exact command;
- browser journey and viewport;
- API request and expected status or body;
- file or database inspection;
- review against a documented contract.

Never require a tool or environment the project does not have without adding setup as explicit work.

## Risk Controls

Prioritize risks that can cause data loss, security exposure, broken public contracts, irreversible migration, inaccessible critical journeys, or deployment failure.

For each, record the failure mode, affected surface, preventive control, detection method, and recovery path.

## Common Planning Failures

- **File-list planning:** Naming files without explaining completed behavior.
- **Architecture theatre:** Adding services, abstractions, queues, or flags for hypothetical scale.
- **Verification last:** Deferring every test until after all implementation.
- **Hidden migration:** Changing persisted data without backup, compatibility, or rollback work.
- **Unowned decision:** Hiding a material product or data choice inside an implementation task.
- **False certainty:** Supplying dates, percentages, or estimates without a basis.
- **Gold plating:** Treating polish, analytics, onboarding, or admin features as implied.
