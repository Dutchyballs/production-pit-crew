# Repository instructions

These instructions apply to the entire Production Pit Crew repository.

## Purpose

Maintain a small, publishable workflow pack that improves planning, product-interface design, independent verification, change review, and release gating. The portable core is a set of Agent Skills; the first supported adapter is Codex. Preserve the Agency Agents attribution and non-affiliation language.

## Boundaries

- Keep specialist roles narrow. Use built-in Codex exploration and worker behavior for codebase mapping and implementation.
- The parent Codex session orchestrates the workflow. Pack agents must not spawn agents or claim autonomous coordination.
- Do not add persistent-memory claims, fictional context retention, issue quotas, arbitrary scores, or default-failure policies.
- Do not impose frameworks, ports, test tools, viewports, visual trends, or repository conventions.
- Preserve user work. Never make an independent reviewer or verifier silently repair the implementation it is judging.
- Treat missing evidence as unverified or blocked. A clean review is valid.

## Repository contracts

- Agent names and files use `pitcrew_`; skill names and directories use `pitcrew-`.
- `pitcrew-package.json` declares shipped components.
- `.codex-plugin/plugin.json` packages the portable skills and must match the package version.
- `ownership.json` is an explicit allowlist for install and uninstall ownership.
- Project install targets are `.codex/agents` and `.agents/skills`.
- User install targets are `${CODEX_HOME:-~/.codex}/agents` and `~/.agents/skills`.
- New evidence from browser verification belongs under `.pitcrew/evidence` unless a host project explicitly defines another location.
- Host adapters must preserve workflow semantics while isolating host-specific configuration and tool names.

## Editing expectations

- Inspect related manifests, ownership entries, tests, and docs before changing a component name or path.
- Keep skill frontmatter limited to `name` and `description`.
- Put long reference material in a skill's `references/` directory and keep the main workflow concise.
- Use Python standard-library features for repository tooling unless a dependency has a demonstrated need.
- Use `apply_patch` for hand-edited files and avoid unrelated rewrites.
- Never weaken path containment, symlink checks, collision detection, atomic writes, rollback, or exact-file uninstall for convenience.

## Required validation

Run from the repository root after relevant changes:

```bash
python3 scripts/validate.py --strict
python3 -m unittest discover -s tests -v
bash -n scripts/install.sh
```

Also test the PowerShell wrapper on Windows when it changes. Report commands that could not be run; do not convert missing coverage into a pass.

## Review priorities

1. Filesystem safety and ownership correctness.
2. Agent routing and sandbox boundaries.
3. Honest evidence and decision semantics.
4. Portability across projects and platforms.
5. Documentation, attribution, and compatibility.
