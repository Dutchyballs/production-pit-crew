# Production Pit Crew handover

Last reconciled: 14 August 2026 (Australia/Sydney)

## Current state

Production Pit Crew is an unreleased `0.1.0` candidate containing four portable Agent Skills and four Codex custom agents. The package manifest, plugin manifest, ownership allowlist, documentation, validation tooling, installer wrappers, tests, and CI workflow are present and internally consistent.

The repository root is `D:\production-pit-crew\production-pit-crew` in this workspace. A new local Git repository was initialised on `main`, with import baseline commit `fce8f8f` (`chore: import Production Pit Crew snapshot`). No Git remote is configured, and this new history is not the original development history.

The supplied historical handover identifies `ea40d11` as the last independently reviewed commit in the original development workspace. It reports that candidate passed the complete 31-test suite, skill validation, compilation, Bash checks, Git checks, a 20-file legacy migration rehearsal, and an independent release gate. This ZIP does not contain the original `.git` data, so that commit identity and evidence are useful provenance notes but cannot be independently verified from this copy.

## Verified in this workspace

- `python scripts/validate.py --strict` passed: 4 agents, 4 skills, and 45 files checked, including this handover.
- `python -m unittest discover -s tests -v` passed: 31 tests run, 21 skipped as expected on this Windows environment. Nineteen installer mutation tests are intentionally skipped because v0.1 currently fails closed on Windows; two symlink tests were skipped because symlink creation is unavailable.
- `powershell -File .\scripts\install.ps1 -Scope Project -ProjectDir <temporary-directory> -DryRun` passed and reported zero writes.
- Package and plugin versions both report `0.1.0`.

## Not verified here

- `bash -n scripts/install.sh` and the Bash dry run could not run because the available WSL Bash service returned `E_ACCESSDENIED`.
- PowerShell 7 (`pwsh`) is not installed; the wrapper was exercised with Windows PowerShell 5.1.
- Current CI, real POSIX install/upgrade/uninstall behavior, local plugin-marketplace loading, signed or checksummed release archives, and end-to-end Codex discovery were not run from this snapshot.
- No public publication or production release was performed.

## Release status

`0.1.0` remains under development. Do not tag, publish, or describe this snapshot as the finished release. The current release decision is **HOLD** because native Windows mutation is deliberately disabled and cross-platform/current CI evidence is incomplete.

The release requires safe Windows install, upgrade, targeted force with backups, rollback, locking, and precise uninstall; green tests and CI on all supported operating systems; matching documentation and manifests; a clean Git tree; an independent release PASS; and Jason's acceptance test and approval.

## Active development objective

Implement the native, reparse-safe Windows mutation backend in the shared dependency-free Python installer core. Keep Bash and PowerShell as thin wrappers over the same behavior.

The implementation must preserve the existing fail-closed protections: exact ownership, full preflight before writes, safe path containment, rejection of symlinks/junctions/reparse escapes and unsafe Windows path forms, apply-time rechecks, atomic same-filesystem staging where supported, conflict backups, rollback, untrusted-state validation, exact-file uninstall, preservation of user files, and an exclusive mutation lock.

Remove the broad Windows mutation test skips only after this behavior has real focused coverage, including project and user install, dry run, repeat install, conflicts, targeted force, uninstall, tampered state, Unicode paths, rollback, locking, legacy migration, reserved/drive/UNC/ADS paths, case collisions, and reparse-point race or escape scenarios.

## Important boundaries

- Windows install and uninstall mutation must remain disabled until the new backend is proven safe. Windows validation and dry run are currently supported.
- Tests must use isolated temporary homes and must never touch Jason's real Codex configuration.
- The parent Codex session orchestrates the workflow. Pack agents do not spawn other agents and do not claim autonomous coordination or persistent memory.
- Missing runtime evidence remains unverified or blocked; it must not be converted into a pass.
- Preserve attribution, MIT licensing, third-party notices, and non-affiliation wording.
- Do not push, publish, tag, or create a public release without Jason's explicit approval.

## Next bounded step

Use `pitcrew-plan-delivery` to inspect `scripts/install_core.py` and `tests/test_installer.py`, map the existing POSIX safety model, and produce an implementation contract for the Windows backend before changing installer behavior. Then implement and verify the smallest complete Windows safety slice.

Start a fresh task by reading, in order:

1. `AGENTS.md`
2. this handover
3. `README.md`
4. `docs/project-brief.md`
5. `docs/architecture.md`
6. `docs/roadmap.md`
7. `docs/usage.md`
8. `CONTRIBUTING.md`
9. `SECURITY.md`
