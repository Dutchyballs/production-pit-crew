---
name: pitcrew-plan-delivery
description: Convert a product idea, feature request, specification, or unclear body of work into an evidence-based delivery plan with explicit scope, dependencies, acceptance criteria, risks, and verification. Use before implementation to plan a new project, break down a feature, repair a vague task list, or align work with an existing repository.
---

# Plan Delivery

Produce a plan that another developer can execute and verify without guessing. Keep it proportional to the work.

## Workflow

1. Establish the evidence base.
   - Read supplied requirements and relevant project instructions.
   - When a repository exists, inspect its manifests, entry points, existing patterns, tests, and delivery commands before proposing structure.
   - Separate confirmed facts, reasonable assumptions, and unresolved decisions.
2. Define the outcome.
   - State the user or operator, the job they must complete, and the observable result.
   - Record constraints, required compatibility, protected behavior, and explicit non-goals.
   - Preserve the existing stack and conventions unless the task requires a change.
3. Resolve only material ambiguity.
   - Ask when a missing choice changes architecture, data ownership, destructive behavior, public API, cost, or user experience.
   - Make a labelled, reversible assumption for low-risk details and continue.
4. Design delivery slices.
   - Organize work by independently verifiable outcomes, not arbitrary file lists or job titles.
   - Put enabling work before dependent work.
   - Keep research, implementation, migration, testing, documentation, and rollout visible when genuinely required.
   - Avoid speculative abstractions and unrequested infrastructure.
5. Write acceptance criteria.
   - Make every criterion observable from the product, API, file output, log, or test.
   - Include the verification method beside the criterion.
   - Cover relevant happy paths, failure states, compatibility, accessibility, and data safety.
6. Identify delivery risk.
   - Name the failure mode, affected surface, prevention or detection step, and fallback.
   - Distinguish blockers from follow-up improvements.
7. Return a build-ready plan.

## Required Output

Use the smallest structure that preserves these elements:

~~~markdown
# Delivery Plan: [outcome]

## Outcome
[Who can do what when this is complete.]

## Evidence and assumptions
- Confirmed: [...]
- Assumed: [...]
- Decision needed: [...]  # omit when empty

## Scope
- In: [...]
- Out: [...]
- Constraints: [...]

## Delivery slices
1. **[Verifiable slice]**
   - Work: [...]
   - Depends on: [...]
   - Acceptance:
     - [Observable criterion] — verify with [method]

## Risks and controls
| Risk | Impact | Control or fallback |
| --- | --- | --- |
| [...] | [...] | [...] |

## Final verification
- [Command, browser journey, inspection, or review]
~~~

Do not invent calendar estimates, staffing, or confidence percentages unless requested and supported.

## Quality Rules

- Trace every planned item to a requested outcome, discovered dependency, or material risk.
- Quote exact requirements only when preserving wording matters.
- Prefer a small first usable slice over a broad scaffold with no completed journey.
- Treat documentation and tests as work only when they protect adoption, operation, or change safety.
- Do not silently add redesigns or cleanups. List valuable extras as optional follow-ups.
- State inspection limits instead of implying the entire repository was understood.

For deeper acceptance-criteria and risk checks, read references/planning-checklist.md.
