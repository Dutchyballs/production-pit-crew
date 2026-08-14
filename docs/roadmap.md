# Roadmap

The roadmap records direction, not promised dates. A host is supported only after native testing and documented limitations.

## v0.1 — Codex foundation

- Rebrand and publish Production Pit Crew.
- Ship four portable skills and four Codex custom agents.
- Package the skills with an OpenAI plugin manifest.
- Preserve safe migration from the Codex Workflow Crew preview.
- Validate on Linux, macOS, and Windows CI; keep Windows mutation fail-closed.
- Publish signed or checksummed release archives and installation guidance.

## Next — Distribution and Windows

- Test the skills-only plugin through a local marketplace.
- Prepare universal plugin-directory submission.
- Complete or replace the Windows agent installer with a reparse-safe distribution path.
- Add end-to-end smoke tests through supported Codex desktop, CLI, and IDE surfaces.

## Later — Additional host adapters

- Define an adapter contract that preserves role boundaries, evidence language, and safety rules.
- Evaluate Claude Code, Gemini CLI, and other Agent Skills-compatible coding hosts.
- Add one adapter at a time with native configuration, installation, representative workflow tests, and explicit capability gaps.
- Keep portable skill logic shared; avoid divergent copies unless a host requires different behavior.

## Possible extensions

- Additional specialist roles only when repeated project evidence justifies them.
- Optional templates for release evidence and interface contracts.
- Automated compatibility checks for supported host versions.
