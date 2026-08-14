# Usage

## Choose the layer

Production Pit Crew has a portable skill layer and a Codex adapter:

| Layer | Contains | Availability |
| --- | --- | --- |
| OpenAI plugin | Four Agent Skills | Packaged for ChatGPT and Codex; public directory submission is planned |
| Codex adapter | Four custom-agent TOML files plus the skills | Installed through the safe filesystem installer on supported platforms |

The skills carry the reusable workflow. The custom agents add independent delegation and sandbox profiles where Codex supports them.

## Requirements

- Python 3.11 or newer.
- Bash on macOS or Linux, or Windows PowerShell 5.1/PowerShell 7 on Windows.
- A Codex installation that supports project or user custom agents and skills.

## Choose a scope

| Scope | Agent destination | Skill destination | Use when |
| --- | --- | --- | --- |
| Project | `<project>/.codex/agents` | `<project>/.agents/skills` | The workflow belongs with one repository and should be shared with its contributors. |
| User | `${CODEX_HOME:-~/.codex}/agents` | `~/.agents/skills` | You want the workflow available across your own projects. |

`CODEX_HOME` changes the user agent root only. User skills remain under `~/.agents/skills`.

## Install

Preview a project installation without writing:

```bash
./scripts/install.sh --scope project --project-dir . --dry-run
```

```powershell
pwsh -File .\scripts\install.ps1 -Scope project -ProjectDir . -DryRun
```

Install after reviewing the plan:

```bash
./scripts/install.sh --scope project --project-dir .
```

```powershell
powershell -File .\scripts\install.ps1 -Scope Project -ProjectDir .
```

For a user installation:

```bash
./scripts/install.sh --scope user
```

```powershell
powershell -File .\scripts\install.ps1 -Scope User
```

Windows mutation is supported only on absolute local-drive paths. The installer rejects UNC locations and every symlink, junction, or other reparse point in the destination ancestry. It pins validated directory ancestry while staging, replacing, and deleting files so a concurrent directory rename cannot redirect a checked operation.

Start a fresh Codex session after a supported installation.

## Options

| Bash | PowerShell | Meaning |
| --- | --- | --- |
| `--scope project\|user` | `-Scope project\|user` | Required installation scope. |
| `--project-dir PATH` | `-ProjectDir PATH` | Project root; defaults to the current directory for project scope. |
| `--dry-run` | `-DryRun` | Print the validated action plan without filesystem mutation. |
| `--force` | `-Force` | Permit managed replacement or removal where normal conflict protection stops. Review backups and output carefully. |
| `--uninstall` | `-Uninstall` | Remove files owned by this pack at the selected scope. |

The installer is repeatable: content already installed exactly is reported as unchanged. A different unmanaged file at a target path stops the entire operation before writes unless `--force` is explicit.

On POSIX systems, installation also stops when a destination has a group- or world-writable ancestor without sticky-directory protection. This prevents another local account from swapping a checked directory while files are being replaced. Move the project to an owner-controlled path or install the files manually after reviewing that environment; `--force` does not bypass this check.

On Windows, `--force` likewise does not bypass reparse-point, local-drive, exact-ownership, locking, or apply-time digest protections.

## Uninstall

Preview first:

```bash
./scripts/install.sh --scope project --project-dir . --uninstall --dry-run
```

Then uninstall:

```bash
./scripts/install.sh --scope project --project-dir . --uninstall
```

Uninstall uses exact-file ownership plus trusted current or historical package hashes. Unrelated files and every directory are left alone, and modified managed files stop normal removal rather than being silently deleted. Use force only after inspecting the reported path and preserving any wanted changes.

Because directories are deliberately preserved, a later reinstall may reuse a safe existing skill directory tree only when it contains no files. A non-empty unowned skill directory remains a conflict unless the operator explicitly uses force.

## Use the skills directly

Mention a skill by name and provide the real task context.

### Plan delivery

```text
Use pitcrew-plan-delivery to plan the requested account-export feature. Inspect the
repository first, separate facts from assumptions, and include observable
acceptance criteria and rollback risks.
```

### Define an interface

```text
Use pitcrew-design-interface to define the interface contract for the flight-log
import flow. Preserve the existing component system and cover narrow screens,
keyboard operation, validation, partial imports, and recovery.
```

### Verify a browser experience

```text
Use pitcrew-verify-browser to verify the implemented import journey against these
acceptance criteria. Discover the project's own start command and routes, retain
targeted evidence, and report anything unavailable as not tested.
```

### Gate a release

```text
Use pitcrew-gate-release to decide whether candidate <commit> can be handed off.
Map every required outcome to current evidence and return PASS, HOLD, or BLOCKED
with the shortest evidence-based path forward.
```

## Use the custom agents

The parent Codex session should delegate bounded work and remain responsible for the overall task.

```text
Ask pitcrew_product_designer for a read-only interface contract before implementation.
After the feature runs, ask pitcrew_browser_verifier to exercise the critical journeys
without changing product code. Ask pitcrew_ui_critic for a cold finish assessment and
pitcrew_change_reviewer for a focused diff review.
```

Do not ask the verifier or critics to fix what they inspect in the same pass. Independent evidence is most useful when it is not shaped by the implementation agent's self-assessment.

## Proportional workflows

### Material UI feature

1. Plan the smallest complete journey with `pitcrew-plan-delivery`.
2. Define hierarchy, interaction, content, states, accessibility, and responsive behavior with `pitcrew_product_designer` or `pitcrew-design-interface`.
3. Let Codex explore and implement within the repository's existing conventions.
4. Verify the running candidate with `pitcrew_browser_verifier`.
5. Review finish and code changes independently.
6. Use `pitcrew-gate-release` when making a release, merge, or handoff claim.

### Small non-visual change

Use a short plan when ambiguity exists, implement the focused change, run the project's tests, and use `pitcrew_change_reviewer` for meaningful regression risk. Skip interface stages that do not apply.

### High-risk change

The pack does not replace dedicated security, privacy, migration, performance, or incident-readiness workflows. Add evidence appropriate to the risk and require the relevant owner to accept residual risk.

## Reading results

- `PASS` means defined outcomes were supported by current, relevant evidence.
- `PASS WITH NOTES` means the finish bar passed with non-blocking observations.
- `HOLD` requires a concrete failed requirement or material risk.
- `BLOCKED` or `NOT VERIFIED` means required evidence or access was missing.
- `PARTIAL` means some browser criteria were tested and others were not.

Zero findings is valid. A large finding count is not evidence of review quality.
