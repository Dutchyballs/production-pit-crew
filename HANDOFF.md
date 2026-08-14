# Production Pit Crew handover

Last reconciled: 14 August 2026 (Australia/Sydney)

## Current state

Production Pit Crew is an unreleased `0.1.0` release candidate containing four portable Agent Skills and four Codex custom agents. The Windows filesystem blocker is resolved in implementation commit `9563267` (`feat: complete safe Windows release path`). The shared installer now supports project and user install, upgrade, targeted force with backups, rollback, locking, and precise uninstall on Windows local-drive paths as well as the existing macOS/Linux path.

The repository root is `D:\production-pit-crew\production-pit-crew` on branch `main`. This workspace has a newly initialised local history rather than the original development history. Its import baseline is `fce8f8f`, the reconciled-handover baseline is `6244c2e`, and the Windows/release implementation is `9563267`. No Git remote is configured.

## Verified in this workspace

- `python scripts/validate.py --strict` passed: 4 agents, 4 skills, and 50 files checked.
- `python -m unittest discover -s tests -v` passed: 44 tests run and 4 environment-specific symlink/Bash-platform tests skipped. All 19 installer mutation tests now run on Windows.
- Windows-focused coverage passed for junction escape rejection without symlink privilege, pinned-ancestry rename resistance, unsafe Windows names, lock contention, rollback during install and uninstall, user and project scope, Unicode paths, conflicts, force backups, migration, tampered state, repeat install, and exact-file uninstall.
- Windows PowerShell 5.1 completed a real disposable project install and uninstall. Git for Windows Bash passed syntax checking and the same real disposable lifecycle.
- `python -m compileall -q scripts tests` passed.
- OpenAI's official plugin validator passed the repository manifest. The CI YAML parsed successfully.
- The project MIT licence, complete Agency Agents MIT notice, and origin/ownership/claims record are present and enforced by strict validation.
- Codex Security diff scan `648ee5ca-4af7-42bd-bf52-de095f830af2` completed with full coverage of the five security-sensitive changed files and zero findings against exact range `6244c2e..9563267`.
- Package and plugin versions both report `0.1.0`.

All tests used isolated temporary homes and projects. Jason's real Codex configuration was not modified.

## Release tooling and three-operating-system state

The CI workflow covers Ubuntu, macOS, and Windows on Python 3.11 plus the current Python 3 release. It runs strict validation and the full unit suite on all three operating systems, real Bash install/uninstall lifecycles on Ubuntu and macOS, and real Windows PowerShell 5.1 and PowerShell 7 lifecycles on Windows.

`scripts/build_release.py` refuses a dirty worktree, archives the exact Git commit, verifies CRC and the complete tracked-file inventory, rejects unsafe archive paths/runtime data, writes `SHA256SUMS`, extracts the archive, and reruns strict validation plus all tests. CI uploads only the verified ZIP and checksum after every operating-system job passes.

Repository text is pinned to LF through `.gitattributes` so Git archives contain the same migration-sensitive bytes on Windows, macOS, and Linux.

## Not yet verified

- The updated CI has not run because this local repository has no remote. Native macOS and Linux results therefore remain pending even though their test jobs and real wrapper lifecycles are defined.
- PowerShell 7 is not installed locally; Windows PowerShell 5.1 is verified here and PowerShell 7 is covered by the pending Windows CI job.
- Local Codex plugin-marketplace installation and fresh-session discovery could not be exercised because the desktop-bundled `codex.exe` is inaccessible through the WindowsApps ACL in this environment. The official manifest validator did pass, and the skills were used directly from the repository.
- Jason's end-user acceptance check is pending.
- No push, tag, publication, or public release has been performed.

## Release status

The candidate is **locally ready but the v0.1 release decision is BLOCKED on missing external evidence**. This is not a known product failure: the previous Windows implementation blocker is closed. A final PASS or HOLD cannot be decided until there is current green CI on Ubuntu, macOS, and Windows, a supported Codex install/discovery smoke test, Jason's acceptance, and explicit approval to tag or publish.

Do not describe `0.1.0` as released until those conditions pass. Missing remote or host evidence must remain pending rather than being inferred from local Windows results.

## Important boundaries

- Windows automatic mutation supports absolute local-drive paths only. UNC paths, symlinks, junctions, and all other reparse-point ancestry fail closed.
- `--force` can replace a targeted unmanaged conflict only after creating an exclusive backup. It never bypasses path, ownership, locking, reparse, or digest protections.
- Uninstall removes only exact managed files that still match trusted recorded content and preserves unrelated or modified user files.
- Tests must remain isolated and must never target a real user Codex setup.
- The parent Codex session orchestrates the workflow. Pack agents do not spawn one another or claim autonomous coordination or persistent memory.
- Preserve MIT licensing, attribution, third-party notices, security guidance, and non-affiliation wording.
- Do not push, publish, tag, or create a public release without Jason's explicit approval.

## Next bounded step

Configure an approved Git remote and run the existing CI workflow. If all three operating systems pass, install the verified candidate through a supported Codex plugin/adapter path, start a fresh task, confirm the four skills and four agents are discoverable, and complete Jason's short acceptance workflow. Then run `pitcrew-gate-release` against the exact candidate commit and evidence before any tag or publication.

Start a continuation by reading, in order:

1. `AGENTS.md`
2. this handover
3. `README.md`
4. `docs/project-brief.md`
5. `docs/architecture.md`
6. `docs/roadmap.md`
7. `docs/usage.md`
8. `CONTRIBUTING.md`
9. `SECURITY.md`
