---
name: pitcrew-design-interface
description: Define an implementation-ready product interface contract covering user job, product identity, information hierarchy, interaction model, responsive behavior, states, accessibility, and visual direction. Use before building or materially redesigning a web, desktop, or mobile GUI when the implementation must avoid generic AI-generated UI and align design choices with real product needs and an existing codebase.
---

# Design Interface

Turn product requirements into deliberate interface decisions before implementation. Judge choices by product fit, not fashion.

## Workflow

1. Inspect product context.
   - Identify the primary user, their job, the first-read object, the primary action, and high-risk actions.
   - Inspect the existing interface, brand assets, component library, tokens, content, and technical constraints when available.
   - Preserve useful conventions unless evidence supports changing them.
2. Establish the product lens.
   - Describe what the interface must communicate in the first viewport.
   - Select an interaction model that matches the work, such as editor, timeline, canvas, table, form, feed, or control surface.
   - Choose information density from task frequency and consequence rather than aesthetic preference.
3. Define visual direction.
   - Name a small set of product-specific principles.
   - Define typography roles, colour roles, spacing rhythm, surface treatment, icon and imagery approach, and motion purpose.
   - Identify common defaults that would make this product interchangeable.
4. Specify hierarchy and layout.
   - Map the first read, primary action, supporting controls, status, details, and secondary actions.
   - Describe wide and narrow arrangements, not only component stacking.
   - Protect the primary job as space contracts.
5. Specify the state model.
   - Cover initial, loading, empty, partial, success, validation, error, disabled, focus, selection, destructive confirmation, and disconnected states when relevant.
   - Define what the user sees, can do, and needs to understand in each state.
6. Set accessibility and interaction requirements.
   - Prefer native semantics and keyboard-operable patterns.
   - Specify focus behavior for overlays, dynamic updates, errors, and route changes.
   - Respect reduced motion, zoom, contrast, target size, and readable content.
7. Produce the design contract and implementation handoff.

## Design Contract

~~~markdown
# Interface Contract: [screen or flow]

## Product lens
- User and job: [...]
- First-read object: [...]
- Primary action: [...]
- High-risk action: [...]
- Product character: [three grounded qualities]

## Existing constraints
- Stack and components: [...]
- Brand or product conventions to preserve: [...]
- Content and data constraints: [...]

## Interaction and hierarchy
- Interaction model: [...]
- Density decision: [...]
- First viewport order: [...]
- Secondary information: [...]

## Visual direction
- Typography roles: [...]
- Colour roles: [...]
- Spacing and surfaces: [...]
- Icon, imagery, and motion: [...]
- Forbidden generic defaults: [...]

## Responsive contract
- Wide: [...]
- Narrow: [...]
- What collapses, moves, scrolls, or remains fixed: [...]

## State contract
| State | What appears | Available action | Focus or announcement |
| --- | --- | --- | --- |
| [...] | [...] | [...] | [...] |

## Acceptance evidence
- [Observable interface criterion] — verify with [viewport, journey, or test]
~~~

## Quality Rules

- Do not impose dark mode, glass effects, gradients, cards, animation, or a design system unless the product needs them.
- Do not use placeholder copy where wording carries hierarchy, trust, safety, or empty-state meaning.
- Do not redesign for novelty. Simple interfaces pass when their decisions clearly serve the work.
- Do not call an interface clean, premium, intuitive, or modern without naming observable properties.
- Treat accessibility, responsive behavior, and non-happy states as design inputs.
- Make the contract concrete enough for implementation without prescribing needless pixel values before component context is known.

Read references/interface-quality-rubric.md when the interface is complex or risks becoming generic.
