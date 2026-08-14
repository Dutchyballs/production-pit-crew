# Project handover

Last checked: 14 August 2026 (Australia/Sydney)

## Current state

Production Pit Crew is an unreleased `0.1.0` candidate containing four portable Agent Skills and four Codex custom agents. The package manifest, plugin manifest, ownership allowlist, documentation, validation tooling, installer wrappers, tests, and CI workflow are present and internally consistent.

The usable repository root is the inner `production-pit-crew` directory. In this workspace it is located at `D:\production-pit-crew\production-pit-crew`; the outer directory is only a container. No Git metadata is present in either directory, so the current branch, commit, tags, remote, history, and clean working-tree state cannot be verified from this copy.

## Verified in this workspace

- `python scripts/validate.py --strict` passed: 4 agents, 4 skills, and 44 shipped files checked.
- `python -m unittest discover -s tests -v` passed: 31 tests run, 21 skipped as expected on Windows. Nineteen installer mutation tests are intentionally skipped because v0.1 fails closed on Windows; two symlink tests were skipped because symlink creation is unavailable in this environment.
- `powershell -File .\scripts\install.ps1 -Scope Project -ProjectDir <temporary-directory> -DryRun` passed and reported no writes.
- The package and plugin versions both report `0.1.0`.

## Not verified here

- `bash -n scripts/install.sh` and the Bash dry run could not run because the available WSL Bash service returned `E_ACCESSDENIED`.
- PowerShell 7 (`pwsh`) is not installed; the wrapper was exercised with Windows PowerShell.
- CI, real POSIX install/upgrade/uninstall behavior, local plugin-marketplace loading, signed or checksummed release archives, and end-to-end Codex discovery were not run from this snapshot.
- No public publication or production release was performed.

## Important boundaries

- Windows install and uninstall mutation must remain disabled until a reparse-safe backend or supported distribution path exists. Windows validation and dry run are supported.
- The parent Codex session orchestrates the workflow. Pack agents do not spawn other agents and do not claim autonomous coordination or persistent memory.
- Missing runtime evidence remains unverified or blocked; it must not be converted into a pass.
- Preserve exact-file ownership, path containment, collision detection, atomic writes, rollback, and safe uninstall behavior.

## Recommended next step

Restore or initialise the intended Git repository at the inner project root, then run the existing GitHub Actions matrix from a pushed branch. A release decision should remain on hold until Linux/macOS Bash installer tests, Windows wrapper CI, local plugin loading, end-to-end Codex discovery, and release archive checksums have current evidence.

Start a fresh task by reading, in order:

1. `AGENTS.md`
2. this handover
3. `README.md`
4. `docs/project-brief.md`
5. `docs/architecture.md`
6. `docs/roadmap.md`
