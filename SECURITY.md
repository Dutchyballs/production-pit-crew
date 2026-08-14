# Security policy

## Supported versions

Security fixes are applied to the latest released minor version.

| Version | Supported |
| --- | --- |
| Latest release | Yes |
| Older releases | No |

## Reporting a vulnerability

Use GitHub's private vulnerability reporting from the repository's **Security** tab when it is available. Include:

- affected version or commit;
- operating system and installation scope;
- reproduction steps or a minimal proof of concept;
- expected and observed behavior;
- impact, especially any path escape, unsafe overwrite, unintended deletion, or secret exposure;
- suggested mitigation, if known.

Do not open a public issue containing exploit details, credentials, personal data, or a working path-traversal payload. If private reporting is not available, open a minimal public issue asking the maintainers for a private contact channel and omit sensitive details.

Please allow the maintainers time to reproduce and coordinate a fix before public disclosure. Reports will be acknowledged and assessed as maintainer availability permits; no fixed response or remediation deadline is promised.

## Security scope

High-priority reports include:

- installation outside the documented agent or skill roots;
- symlink, traversal, case-folding, or platform-name bypasses;
- overwrite or deletion of files not owned by this pack;
- unsafe rollback, backup, or state-file behavior;
- command or argument injection through the wrappers;
- untrusted content causing an agent to exceed its documented sandbox or role;
- credentials or personal data retained in browser evidence.

General prompt-quality disagreements, unsupported environment requests, and findings that require a user to deliberately bypass documented safety checks may be handled as ordinary issues rather than vulnerabilities.

## Safe use

- Review a dry run before installing into an established Codex setup.
- Keep repositories and prompt inputs from untrusted sources under normal code-review controls.
- Inspect retained `.pitcrew/evidence` before sharing it.
- Use dedicated security review tooling for applications with material security risk. The included change reviewer is focused, not a comprehensive security audit.
