# Honourable mentions

Production Pit Crew is an independent, curated derivative inspired by [Agency Agents](https://github.com/msitarzewski/agency-agents). It is not affiliated with or endorsed by Agency Agents or its contributors. License attribution is recorded in [Third-party notices](../THIRD_PARTY_NOTICES.md).

The upstream repository is broad by design. This pack extracts a small set of ideas that strengthen everyday Codex work while leaving generic or specialist capabilities to built-in Codex behavior and dedicated tools.

## Ideas carried into the pack

| Upstream material | What was useful | Where the idea landed |
| --- | --- | --- |
| Codebase Onboarding Engineer | Inspect real manifests, entry points, conventions, and tests before planning changes. | Evidence-first planning in `pitcrew-plan-delivery`; ordinary repository exploration remains a built-in Codex job. |
| Minimal Change Engineer | Protect existing behavior and prefer the smallest complete change. | Delivery slices, explicit non-goals, and focused change review. |
| Code Reviewer | Trace concrete findings to affected behavior and explain impact. | `pitcrew_change_reviewer`, without a mandatory finding count. |
| UI Finish-Gate Reviewer | Separate implementation from the final interface-quality judgment. | `pitcrew_ui_critic`, with product fit and observable criteria replacing taste or arbitrary scores. |
| Test Automation Engineer | Prove critical journeys at the running-product boundary. | `pitcrew-verify-browser` and `pitcrew_browser_verifier`, without a fixed framework, port, or test tool. |
| Accessibility Auditor | Treat keyboard use, focus, names, roles, labels, zoom, and reduced motion as product requirements. | Integrated into interface design and browser verification instead of isolated as a late checklist. |
| AI-Generated Code Security Auditor | Review generated changes sceptically and distinguish material risk from style. | Focused safety checks in change review; exhaustive security work is intentionally routed elsewhere. |

## Good ideas deliberately kept as supporting guidance

These were valuable enough to retain, but not useful as separate always-on agents:

- **Repository onboarding:** Codex can inspect a codebase directly; a duplicate persona adds routing cost. The planning skill makes the inspection expectation explicit.
- **Minimal-change discipline:** This is a rule for every implementation, not a specialist role that needs its own handoff.
- **Accessibility review:** Design and verification both need it. Splitting it into one final audit makes accessibility easier to defer.
- **Security review:** A focused diff reviewer can catch visible permission and data-safety mistakes, but broad threat modelling and vulnerability discovery require dedicated security workflows.
- **Test strategy:** The right test boundary depends on the change. The browser verifier covers integrated UI journeys while the host project's own test tools cover lower layers.

## What was not copied

- Hundreds of agents installed wholesale.
- Fictional persistent memory or claims that roles retain context between sessions.
- Agents autonomously spawning or managing other agents.
- Framework-specific directories, fixed localhost ports, or mandatory browser tooling.
- Default-failure rules, issue quotas, readiness percentages, and arbitrary letter grades.
- Visual rules that treat dark themes, gradients, cards, animation, minimalism, or density as inherently good or bad.
- Security or accessibility certification based on prompt output alone.

Those constraints keep the pack portable and make its claims easier to trust. The best upstream lesson was not that every concern needs a persona; it was that important concerns need explicit ownership, observable evidence, and honest limits.
