# Contributing

Contributions that make Production Pit Crew more useful, portable, evidence-driven, or safe are welcome.

## Before opening a change

1. Search existing issues and pull requests for the same problem.
2. Describe the user-visible outcome or failure, not only the proposed files.
3. Keep the change within the pack's boundaries: focused agents, reusable skills, safe installation, validation, tests, and documentation.
4. Open a design discussion before adding a new role, changing install locations, or altering the ownership/state format.

## Development setup

The project requires Python 3.11 or newer and has no runtime package dependency. From the repository root, run:

```bash
python3 scripts/validate.py --strict
python3 -m unittest discover -s tests -v
bash -n scripts/install.sh
```

On Windows, also exercise the PowerShell wrapper when it changes.

Before publishing a candidate from a clean commit, build and verify the exact archive:

```bash
python3 scripts/build_release.py --output-dir dist --verify-extracted
```

Test installer work in a temporary directory or with `--dry-run`. Do not point development tests at a real user installation.

## Contribution rules

### Agents

- Keep the `pitcrew_` namespace and make the description precise enough for routing.
- Give each agent one clear responsibility and an explicit non-responsibility.
- Preserve the sandbox needed for the role; reviewers and designers should remain read-only.
- Do not hard-code a framework, port, browser, viewport, test runner, theme, or repository layout.
- Do not let specialist agents spawn other agents. The parent Codex session owns orchestration.
- Permit a clean result. Never require an issue quota, arbitrary score, or default failure.

### Skills

- Keep the `pitcrew-` namespace and frontmatter limited to `name` and `description`.
- Make the core workflow useful without loading every reference.
- Put detailed checklists or rubrics in `references/` and link them from the skill only when needed.
- Describe observable evidence and honest coverage limits.
- Do not claim memory, autonomous coordination, compliance certification, or production readiness without proof.

### Installer and manifest

- Treat `pitcrew-package.json` as the installation manifest and `ownership.json` as the exact-file ownership boundary.
- Preserve full preflight validation, path containment, symlink rejection, collision detection, atomic writes, safe conflict handling, and exact-file uninstall.
- Record every accepted retired file digest in `ownership.json` before an upgrade may treat old state as ownership proof.
- A dry run must not mutate the filesystem.
- Never recursively delete an installation root or remove a file that the pack cannot prove it owns.
- Add tests for install, repeat install, conflict, forced replacement, dry run, uninstall, and failure rollback behavior when the affected code changes.

### Documentation

- Keep examples platform-neutral or show both Bash and PowerShell.
- Call out assumptions and evidence limits.
- Maintain the independent-derivative notice and third-party attribution.
- Update [Usage](docs/usage.md) and [Architecture](docs/architecture.md) when behavior or boundaries change.

## Pull requests

Keep pull requests narrow enough to review as one outcome. Include:

- the problem and intended behavior;
- affected agents, skills, installer paths, or state formats;
- the exact validation commands run and their results;
- manual evidence where automated tests cannot prove the change;
- compatibility or migration notes for existing installations.

Do not include generated caches, local `.pitcrew` evidence, credentials, screenshots with personal data, or unrelated formatting changes. The `.cwc` directory is retained only as a legacy installer-state location for safe preview upgrades.

## Attribution

If a contribution adapts material from another project, confirm that its license permits reuse and update [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) with the source, license, and extent of adaptation.
