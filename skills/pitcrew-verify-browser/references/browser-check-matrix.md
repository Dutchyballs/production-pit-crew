# Browser Check Matrix

Select checks based on the changed surface and risk. Do not run everything mechanically.

## Contents

- Journey selection
- Functional checks
- Responsive and visual checks
- Accessibility checks
- Reliability and performance signals
- Evidence rules

## Journey Selection

Prioritize:

1. the changed journey;
2. authentication or permission boundaries it crosses;
3. consequential creation, update, import, export, payment, or deletion;
4. one nearby regression path;
5. recovery from the most likely failure.

Use lower-level tests for exhaustive validation matrices when browser integration is not the risk.

## Functional Checks

- Entry route loads without uncaught errors.
- Primary action is discoverable and operates on the intended object.
- Validation preserves safe user input and explains recovery.
- Loading prevents accidental duplicate actions where needed.
- Success reflects persisted reality, not only optimistic UI.
- Back, refresh, deep link, and reload match the application model.
- Destructive actions identify their target and provide appropriate confirmation or recovery.
- Permission-limited states do not expose unavailable actions.

## Responsive and Visual Checks

- No unintended page-level horizontal overflow.
- Critical content and actions remain reachable.
- Fixed and sticky regions do not cover the task.
- Text wraps without clipping or unusably narrow measures.
- Dense data has an intentional narrow-screen treatment.
- Dialogs, menus, popovers, and toasts remain in the viewport.
- Content order still matches decision order.
- Loading, empty, error, selected, disabled, and focus states are distinct.

## Accessibility Checks

Automated checks may identify obvious name, role, contrast, label, and landmark problems. Inspect affected components manually.

Manual keyboard:

- reach every control in a logical order;
- see focus at all times;
- open, operate, and close overlays;
- return focus to the logical trigger;
- submit and recover from form errors;
- avoid keyboard traps.

Manual inspection:

- meaningful page title and heading structure;
- persistent labels and instructions;
- errors connected to fields and summaries;
- appropriate status announcements;
- no icons or colour as sole communication;
- zoom and text resizing preserve the journey;
- reduced motion removes non-essential movement.

Do not report compliance certification from this workflow alone.

## Reliability and Performance Signals

- Record console exceptions and failed critical requests.
- Inspect duplicate submissions and race-prone transitions.
- Note delayed interaction feedback and layout instability.
- Use measured performance tools only when performance is in scope.
- Distinguish third-party or environment failures from application failures.

## Evidence Rules

Good evidence connects the exact build, environment, viewport, data, reproduction steps, expected and observed behavior, artifact, and limitations.

A screenshot proves appearance at one instant. A trace, test, recording, or repeatable interaction proves behavior more strongly. Source inspection can explain ownership but does not replace running-product evidence.
