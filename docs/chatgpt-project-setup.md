# ChatGPT Project setup

Use this when creating the matching ChatGPT Project container.

## Project name

Production Pit Crew

## Keep in the project

- The GitHub repository link after publication.
- The latest release archive and checksum.
- The current project brief, roadmap, and release decision.
- Chats for product direction, implementation, testing, and release work.

Do not treat uploaded copies as newer than the repository unless the change has been committed there.

## Project instructions

```text
Production Pit Crew is an evidence-driven workflow pack. Treat the linked GitHub
repository as the source of truth. Read AGENTS.md and the relevant project docs
before making changes.

Use plain English when reporting work. For implementation requests, inspect the
real repository, preserve existing user work, make the scoped change, and run the
required validation before reporting completion. Separate confirmed facts,
assumptions, observations, and unverified areas.

Keep the portable Agent Skills core separate from host-specific adapters. Codex is
the only supported adapter in v0.1. Other hosts are roadmap scope until their
native configuration and workflows are tested.

Never manufacture review findings, claim persistent memory, or call a release
ready without current evidence. Keep attribution and installer safety intact.
```
