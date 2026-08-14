# Production Pit Crew handover

Last reconciled: 14 August 2026 (Australia/Sydney)

## Current state

Production Pit Crew is an unreleased `0.1.0` release candidate containing four portable Agent Skills and four Codex custom agents. The Windows filesystem blocker is resolved in implementation commit `af34771` (`feat: complete safe Windows release path`), and clean uninstall/reinstall is resolved in `67786e0`. The shared installer supports project and user install, upgrade, targeted force with backups, rollback, locking, and precise uninstall on Windows local-drive paths as well as the existing macOS/Linux path.

The repository root is `D:\production-pit-crew\production-pit-crew` on branch `main`. This workspace has a newly initialised local history rather than the original development history. Its import baseline is `a21ff37`, the reconciled-handover baseline is `ea42aa7`, the Windows implementation is `af34771`, licensing/provenance is `35ce64e`, publication hardening is `ab192b8`, and the Unix executable-mode fix is `abc3f01`. Every reachable commit uses GitHub noreply email for both author and committer. The private GitHub remote is `https://github.com/Dutchyballs/production-pit-crew`.

## Verified in this workspace

- `python scripts/validate.py --strict` passed: 4 agents, 4 skills, and 50 files checked.
- `python -m unittest discover -s tests -v` passed: 49 tests run and 4 environment-specific symlink/Bash-platform tests skipped. All installer mutation tests now run on Windows.
- Windows-focused coverage passed for junction escape rejection without symlink privilege, pinned-ancestry rename resistance, unsafe Windows names, lock contention, rollback during install and uninstall, user and project scope, Unicode paths, conflicts, force backups, migration, tampered state, repeat install, clean uninstall/reinstall, and exact-file uninstall.
- Windows PowerShell 5.1 completed a real disposable project install, repeat install, uninstall, clean reinstall, and final inventory verification. Git for Windows Bash passed syntax checking and its supported disposable lifecycle.
- `python -m compileall -q scripts tests` passed.
- OpenAI's official plugin validator passed the repository manifest. The CI YAML parsed successfully.
- The official Codex CLI `0.147.0` discovered all four project skills from a clean installed copy. In a read-only session it also successfully spawned each of the four project custom-agent types without running shell commands or changing project files.
- Private GitHub Actions runs `31800577242` and `31801871553` passed the complete Ubuntu, macOS, and Windows matrix. All six Python validation/test jobs passed, the Bash lifecycle passed on Ubuntu and macOS, both Windows PowerShell 5.1 and PowerShell 7 lifecycles passed, and each exact-commit release archive was built, verified, and uploaded as a private workflow artifact.
- The project MIT licence, complete Agency Agents MIT notice, and origin/ownership/claims record are present and enforced by strict validation.
- Pre-rewrite Codex Security scans completed with full coverage and zero findings for both the Windows mutation implementation and the clean-reinstall fix. A fresh bounded scan of the rewritten release-candidate line also completed with full coverage and zero findings; it must be repeated after any further tracked change.
- Package and plugin versions both report `0.1.0`.

Installer and package tests used isolated temporary homes and projects. The live Codex discovery check reused Jason's existing ChatGPT sign-in in a read-only session. It did not change Codex configuration or run project commands. An ephemeral CLI attempt exposed an intermittent parent-session registration error; the normal persisted read-only session completed the same check successfully.

## Release tooling and three-operating-system state

The CI workflow covers Ubuntu, macOS, and Windows on Python 3.11 plus the current Python 3 release. It runs strict validation and the full unit suite on all three operating systems. Every native wrapper job performs install, repeat install, uninstall, clean reinstall, and final uninstall through Bash on Ubuntu/macOS and Windows PowerShell 5.1 plus PowerShell 7 on Windows. All third-party GitHub Actions are pinned to immutable full commit SHAs.

`scripts/build_release.py` refuses a dirty worktree, archives the exact Git commit with UTC ZIP timestamps for cross-operating-system reproducibility, verifies CRC, the complete tracked-file inventory, and the Bash wrapper's executable metadata, rejects unsafe archive paths/runtime data, writes `SHA256SUMS`, extracts the archive, and reruns strict validation plus all tests. CI builds and verifies the archive independently on Ubuntu, Windows, and macOS, compares all three SHA-256 values, and marks the candidate green only when the values match. The Ubuntu artifact is uploaded only after every operating-system validation and wrapper job passes.

Repository text is pinned to LF through `.gitattributes` so Git archives contain the same migration-sensitive bytes on Windows, macOS, and Linux.

## Not yet verified

- Jason's end-user acceptance check is pending.
- The repository is private and `main` has been pushed. No tag, public publication, or GitHub Release has been performed.

## Release status

The candidate is **technically ready but the v0.1 release decision remains on HOLD for Jason's acceptance and explicit publication approval**. The previous Windows implementation blocker is closed, supported Codex skill/custom-agent discovery passes locally, and current native CI is green on Ubuntu, macOS, and Windows.

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

Before tagging, confirm the exact `HEAD` has a green GitHub Actions run and that the matching archive, checksum, final security scan, and physical Windows proof are present in the external final-candidate evidence pack. Then complete Jason's short acceptance workflow and run `pitcrew-gate-release` against that exact candidate and evidence before any public release.

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
