---
name: pitcrew-verify-browser
description: Verify a web interface through real browser journeys, targeted screenshots, responsive checks, keyboard use, accessibility checks, console and network evidence, and existing automated tests. Use after UI implementation or during frontend debugging when the verifier must report observed behavior honestly, distinguish defects from untested areas, and avoid biased QA or invented findings.
---

# Verify Browser Experience

Test the product that actually runs. Report evidence, limitations, and reproducible defects without requiring a predetermined number of problems.

## Workflow

1. Establish the verification contract.
   - Read requested behavior, acceptance criteria, interface contract, and relevant project instructions.
   - Identify critical journeys, representative data, supported browsers, and viewports.
   - Find the project's own start and test commands. Never assume a framework, port, route, or screenshot script.
2. Prepare safely.
   - Reuse a running development server when available.
   - Start only documented local services needed for the test and stop only processes created by this verification.
   - Use isolated test data and avoid production systems unless explicitly authorized.
3. Exercise critical journeys.
   - Test the smallest end-to-end paths that prove the requested integration.
   - Use semantic selectors and condition-based waits.
   - Capture screenshots at decisions, failures, and required responsive states rather than every click.
   - Retain console, network, trace, or test output when it explains behavior.
4. Check responsive behavior.
   - Verify at least one representative narrow and wide viewport for responsive interfaces.
   - Add intermediate, touch, or high-density checks only when warranted.
   - Look for hidden controls, unintended overflow, lost context, poor reordering, and unusable fixed regions.
5. Check accessibility within available tools.
   - Complete the critical journey by keyboard.
   - Inspect names, roles, labels, focus visibility and movement, heading and landmark structure, error association, non-colour cues, zoom resilience, and reduced motion where relevant.
   - Run automated accessibility checks when available, but do not treat them as complete coverage.
   - Do not claim screen-reader or voice-control compatibility unless that technology was actually used.
6. Classify the result.
   - Mark each criterion pass, fail, or not tested.
   - Report defects only when evidence supports them.
   - Separate product defects, test-environment failures, and coverage gaps.
   - A clean result is valid when defined checks pass; never manufacture findings.
7. Return an evidence-based report.

## Report Format

~~~markdown
# Browser Verification: [scope]

## Result
[PASS / FAIL / PARTIAL / BLOCKED] — [one-sentence basis]

## Environment
- Build or commit: [...]
- Browser and viewport: [...]
- Data and account: [...]
- Commands: [...]

## Acceptance results
| Criterion or journey | Result | Evidence |
| --- | --- | --- |
| [...] | Pass / Fail / Not tested | [...] |

## Findings
1. **[Severity] [Observed problem]**
   - Reproduce: [...]
   - Expected: [...]
   - Observed: [...]
   - Evidence: [...]
   - Likely owning surface: [...]  # label as inference when not traced

## Coverage limits
- [...]

## Evidence retained
- [...]
~~~

Omit findings when no defects were observed.

## Quality Rules

- Prefer role, label, text, and stable test-ID selectors over DOM chains.
- Wait for observable state, response, URL, or event. Do not use hard sleeps as synchronization.
- Never infer that an interaction works from a static screenshot.
- Never infer visual correctness from passing unit tests.
- Redact secrets and personal data from screenshots, logs, URLs, and reports.
- Do not change application code during independent verification unless the user also requests a fix.
- Re-run the failed path after a fix before calling it resolved.

Read references/browser-check-matrix.md to select checks for a larger or higher-risk interface.
