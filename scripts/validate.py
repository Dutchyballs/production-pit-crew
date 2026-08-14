#!/usr/bin/env python3
"""Validate Production Pit Crew for Codex's package, agents, skills, and references."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

import install_core


AGENT_KEYS = {"name", "description", "developer_instructions", "sandbox_mode"}
AGENT_REQUIRED = {"name", "description", "developer_instructions"}
ALLOWED_SANDBOXES = {"read-only", "workspace-write", "danger-full-access"}
FRONTMATTER_KEYS = {"name", "description"}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
IGNORED_DIRS = {".git", ".cwc", ".pitcrew", "__pycache__", "dist"}
PLUGIN_MANIFEST = ".codex-plugin/plugin.json"
PLUGIN_REQUIRED_KEYS = {"name", "version", "description", "author", "skills", "interface"}
PLUGIN_ALLOWED_KEYS = PLUGIN_REQUIRED_KEYS | {
    "apps",
    "author",
    "homepage",
    "id",
    "interface",
    "keywords",
    "license",
    "mcpServers",
    "repository",
}

HYGIENE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?:localhost|127\.0\.0\.1):\d+", re.I), "hard-coded local port"),
    (re.compile(r"(?:resources/views|app/Http|src/pages|pages/api)(?:/|\\)", re.I), "framework-specific path"),
    (re.compile(r"\bmust\s+(?:find|report|produce)\s+(?:at least\s+)?\d+\b", re.I), "forced finding quota"),
    (re.compile(r"\bdefault(?:s|ed)?\s+to\s+(?:fail|failure|hold)\b", re.I), "default-failure instruction"),
    (re.compile(r"\bremember(?:s|ed)?\s+(?:this|everything|context)\s+(?:forever|between sessions)\b", re.I), "unsupported persistence claim"),
    (re.compile(r"\b(?:rm\s+-rf|Remove-Item\s+[^\n]*-Recurse|git\s+reset\s+--hard)\b", re.I), "destructive command instruction"),
)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def regular_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        original_directories = list(directories)
        for directory in original_directories:
            path = current_path / directory
            if install_core.is_linklike(path):
                result.append(path)
        directories[:] = [
            name
            for name in original_directories
            if name not in IGNORED_DIRS and not install_core.is_linklike(current_path / name)
        ]
        for filename in files:
            result.append(current_path / filename)
    return sorted(result, key=lambda path: path.as_posix().casefold())


def parse_skill_frontmatter(path: Path) -> dict[str, str]:
    """Parse the pack's intentionally constrained key: value frontmatter subset."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("must start with a --- frontmatter fence")
    data: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:], start=2):
        if line == "---":
            if not data:
                raise ValueError("frontmatter must not be empty")
            return data
        if not line or line.startswith((" ", "\t")) or ":" not in line:
            raise ValueError(f"line {line_number} is outside the supported 'key: value' subset")
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if not key or not value:
            raise ValueError(f"line {line_number} needs a non-empty key and value")
        if key in data:
            raise ValueError(f"duplicate frontmatter key {key!r}")
        data[key] = value
    raise ValueError("frontmatter closing fence is missing")


def validate_manifest(repo: Path, report: Report) -> tuple[dict | None, dict | None]:
    try:
        manifest = install_core.load_json(repo / "pitcrew-package.json", "package manifest")
        ownership_data = install_core.load_json(repo / "ownership.json", "ownership registry")
        entries = install_core.build_entries(repo, manifest)
        ownership = install_core.load_ownership(repo)
    except install_core.PackageError as exc:
        report.error(str(exc))
        return None, None

    if not isinstance(manifest.get("version"), str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", manifest["version"]):
        report.error("pitcrew-package.json version must be a SemVer-like string")

    declared_agents = {item["target"] for item in manifest["agents"] if isinstance(item, dict) and "target" in item}
    actual_agents = {path.name for path in (repo / "agents").glob("*.toml")}
    if declared_agents != actual_agents:
        report.error(
            f"agent inventory mismatch; undeclared={sorted(actual_agents - declared_agents)}, missing={sorted(declared_agents - actual_agents)}"
        )

    declared_skills = {item["name"] for item in manifest["skills"] if isinstance(item, dict) and "name" in item}
    actual_skills = {path.name for path in (repo / "skills").iterdir() if path.is_dir()}
    if declared_skills != actual_skills:
        report.error(
            f"skill inventory mismatch; undeclared={sorted(actual_skills - declared_skills)}, missing={sorted(declared_skills - actual_skills)}"
        )

    agent_owners = ownership.paths["agents"]
    skill_owners = ownership.paths["skills"]
    if declared_agents - agent_owners:
        report.error(f"manifest agent targets absent from ownership registry: {sorted(declared_agents - agent_owners)}")
    declared_skill_files = {entry.relative for entry in entries if entry.root == "skills"}
    if declared_skill_files - skill_owners:
        report.error(
            f"manifest skill files absent from ownership registry: {sorted(declared_skill_files - skill_owners)}"
        )

    folded = [(entry.root, entry.relative.casefold()) for entry in entries]
    if len(folded) != len(set(folded)):
        report.error("manifest contains a case-insensitive installed-path collision")
    return manifest, ownership_data


def validate_plugin(repo: Path, manifest: dict | None, report: Report) -> None:
    path = repo / PLUGIN_MANIFEST
    try:
        data = install_core.load_json(path, "plugin manifest")
    except install_core.PackageError as exc:
        report.error(str(exc))
        return
    unknown = set(data) - PLUGIN_ALLOWED_KEYS
    missing = PLUGIN_REQUIRED_KEYS - set(data)
    if unknown:
        report.error(f"{PLUGIN_MANIFEST}: unsupported keys: {sorted(unknown)}")
    if missing:
        report.error(f"{PLUGIN_MANIFEST}: missing keys: {sorted(missing)}")
    if data.get("name") != install_core.PACK_ID:
        report.error(f"{PLUGIN_MANIFEST}: name must equal {install_core.PACK_ID!r}")
    if manifest is not None and data.get("version") != manifest.get("version"):
        report.error(f"{PLUGIN_MANIFEST}: version must match pitcrew-package.json")
    if not isinstance(data.get("description"), str) or not data["description"].strip():
        report.error(f"{PLUGIN_MANIFEST}: description must be a non-empty string")
    if data.get("skills") != "./skills/":
        report.error(f"{PLUGIN_MANIFEST}: skills must point to './skills/'")
    for key in ("id", "homepage", "repository", "license", "apps"):
        if key in data and (not isinstance(data[key], str) or not data[key].strip()):
            report.error(f"{PLUGIN_MANIFEST}: {key} must be a non-empty string")
    if "apps" in data and data["apps"] not in {".app.json", "./.app.json"}:
        report.error(f"{PLUGIN_MANIFEST}: apps must resolve to '.app.json'")
    if "mcpServers" in data:
        mcp_servers = data["mcpServers"]
        if isinstance(mcp_servers, str):
            if mcp_servers not in {".mcp.json", "./.mcp.json"}:
                report.error(f"{PLUGIN_MANIFEST}: mcpServers must resolve to '.mcp.json'")
        elif not isinstance(mcp_servers, dict):
            report.error(f"{PLUGIN_MANIFEST}: mcpServers must be a path or object")
    if "keywords" in data and (
        not isinstance(data["keywords"], list)
        or not data["keywords"]
        or any(not isinstance(item, str) or not item.strip() for item in data["keywords"])
    ):
        report.error(f"{PLUGIN_MANIFEST}: keywords must be a non-empty list of non-empty strings")
    if "author" in data:
        author = data["author"]
        if not isinstance(author, dict) or not author:
            report.error(f"{PLUGIN_MANIFEST}: author must be a non-empty object")
        elif any(key not in {"name", "email", "url"} for key in author) or any(
            not isinstance(value, str) or not value.strip() for value in author.values()
        ):
            report.error(f"{PLUGIN_MANIFEST}: author supports non-empty name, email, and url strings")
    interface = data.get("interface")
    if not isinstance(interface, dict):
        report.error(f"{PLUGIN_MANIFEST}: interface must be an object")
    else:
        for key in (
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
        ):
            if not isinstance(interface.get(key), str) or not interface[key].strip():
                report.error(f"{PLUGIN_MANIFEST}: interface.{key} must be a non-empty string")
        capabilities = interface.get("capabilities")
        if (
            not isinstance(capabilities, list)
            or not capabilities
            or any(not isinstance(item, str) or not item.strip() for item in capabilities)
        ):
            report.error(
                f"{PLUGIN_MANIFEST}: interface.capabilities must be a non-empty list of non-empty strings"
            )
        prompts = interface.get("defaultPrompt")
        if (
            not isinstance(prompts, list)
            or not prompts
            or len(prompts) > 3
            or any(
                not isinstance(item, str) or not item.strip() or len(item) > 128
                for item in prompts
            )
        ):
            report.error(
                f"{PLUGIN_MANIFEST}: interface.defaultPrompt must contain one to three non-empty strings of at most 128 characters"
            )


def validate_agents(repo: Path, manifest: dict | None, report: Report) -> None:
    names: dict[str, Path] = {}
    manifest_names = {
        item.get("target"): item.get("name") for item in (manifest or {}).get("agents", []) if isinstance(item, dict)
    }
    for path in sorted((repo / "agents").glob("*.toml")):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            report.error(f"{path.relative_to(repo)}: invalid TOML: {exc}")
            continue
        unknown = set(data) - AGENT_KEYS
        missing = AGENT_REQUIRED - set(data)
        if unknown:
            report.error(f"{path.relative_to(repo)}: unsupported top-level keys: {sorted(unknown)}")
        if missing:
            report.error(f"{path.relative_to(repo)}: missing required keys: {sorted(missing)}")
        for key in AGENT_REQUIRED:
            if key in data and (not isinstance(data[key], str) or not data[key].strip()):
                report.error(f"{path.relative_to(repo)}: {key} must be a non-empty string")
        name = data.get("name")
        if isinstance(name, str):
            if name != path.stem:
                report.error(f"{path.relative_to(repo)}: name {name!r} must equal filename stem {path.stem!r}")
            folded = name.casefold()
            if folded in names:
                report.error(f"duplicate case-insensitive agent name {name!r}: {names[folded]} and {path}")
            names[folded] = path
            declared_name = manifest_names.get(path.name)
            if declared_name != name:
                report.error(f"{path.relative_to(repo)}: manifest name {declared_name!r} does not match {name!r}")
        sandbox = data.get("sandbox_mode")
        if sandbox is not None and sandbox not in ALLOWED_SANDBOXES:
            report.error(f"{path.relative_to(repo)}: unsupported sandbox_mode {sandbox!r}")


def validate_openai_yaml(skill_dir: Path, report: Report, repo: Path) -> None:
    path = skill_dir / "agents" / "openai.yaml"
    if not path.is_file():
        report.error(f"{path.relative_to(repo)}: missing skill UI metadata")
        return
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        report.error(f"{path.relative_to(repo)}: cannot read: {exc}")
        return
    for required in ("interface:", "display_name:", "short_description:", "default_prompt:"):
        if required not in text:
            report.error(f"{path.relative_to(repo)}: missing {required.rstrip(':')}")
    prompt_match = re.search(r"^\s*default_prompt:\s*(.*)$", text, re.MULTILINE)
    if prompt_match and f"${skill_dir.name}" not in prompt_match.group(1):
        report.error(f"{path.relative_to(repo)}: default_prompt must mention ${skill_dir.name}")
    for icon in re.findall(r"^\s*icon_(?:small|large):\s*(\S+)\s*$", text, re.MULTILINE):
        icon = icon.strip('"\'')
        normalized_icon = icon.removeprefix("./")
        try:
            relative = install_core.validate_relative(normalized_icon, "skill icon")
        except install_core.PackageError as exc:
            report.error(f"{path.relative_to(repo)}: {exc}")
            continue
        target = skill_dir.joinpath(*PurePosixPath(relative).parts)
        if not target.is_file():
            report.error(f"{path.relative_to(repo)}: icon does not exist: {relative}")


def validate_skills(repo: Path, manifest: dict | None, report: Report) -> None:
    names: dict[str, Path] = {}
    declared = {
        item.get("name") for item in (manifest or {}).get("skills", []) if isinstance(item, dict)
    }
    skills_root = repo / "skills"
    if not skills_root.is_dir():
        report.error("skills directory is missing")
        return
    for skill_dir in sorted((path for path in skills_root.iterdir() if path.is_dir()), key=lambda p: p.name.casefold()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            report.error(f"{skill_dir.relative_to(repo)}: SKILL.md is missing")
            continue
        try:
            data = parse_skill_frontmatter(skill_file)
        except (OSError, UnicodeError, ValueError) as exc:
            report.error(f"{skill_file.relative_to(repo)}: invalid constrained frontmatter: {exc}")
            continue
        unknown = set(data) - FRONTMATTER_KEYS
        missing = FRONTMATTER_KEYS - set(data)
        if unknown:
            report.error(f"{skill_file.relative_to(repo)}: unsupported frontmatter keys: {sorted(unknown)}")
        if missing:
            report.error(f"{skill_file.relative_to(repo)}: missing frontmatter keys: {sorted(missing)}")
        name = data.get("name")
        if name != skill_dir.name:
            report.error(f"{skill_file.relative_to(repo)}: name {name!r} must equal directory {skill_dir.name!r}")
        if name not in declared:
            report.error(f"{skill_file.relative_to(repo)}: skill is not declared in pitcrew-package.json")
        if isinstance(name, str):
            folded = name.casefold()
            if folded in names:
                report.error(f"duplicate case-insensitive skill name {name!r}: {names[folded]} and {skill_dir}")
            names[folded] = skill_dir
        validate_openai_yaml(skill_dir, report, repo)


def validate_filesystem(repo: Path, report: Report) -> None:
    collision_map: dict[str, Path] = {}
    for path in regular_files(repo):
        relative = path.relative_to(repo)
        key = relative.as_posix().casefold()
        prior = collision_map.get(key)
        if prior is not None and prior != path:
            report.error(f"case-insensitive path collision: {prior.relative_to(repo)} and {relative}")
        collision_map[key] = path
        if install_core.is_linklike(path):
            report.error(f"{relative}: symlinks and reparse points are not allowed in the package")
            continue
        try:
            info = path.stat()
        except OSError as exc:
            report.error(f"{relative}: cannot inspect: {exc}")
            continue
        if not stat.S_ISREG(info.st_mode):
            report.error(f"{relative}: special files are not allowed in the package")


def validate_markdown_links(repo: Path, report: Report) -> None:
    for path in regular_files(repo):
        if path.suffix.lower() != ".md" or install_core.is_linklike(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for raw in MARKDOWN_LINK.findall(text):
            link = raw.strip().strip("<>").split(maxsplit=1)[0]
            parsed = urlsplit(link)
            if not link or link.startswith("#") or parsed.scheme or parsed.netloc:
                continue
            local = unquote(parsed.path)
            if not local:
                continue
            target = (path.parent / local).resolve(strict=False)
            try:
                target.relative_to(repo.resolve())
            except ValueError:
                report.error(f"{path.relative_to(repo)}: local link escapes repository: {raw}")
                continue
            if not target.exists():
                report.error(f"{path.relative_to(repo)}: broken local link: {raw}")


def validate_legal_notices(repo: Path, report: Report) -> None:
    required_fragments = {
        "LICENSE": (
            "MIT License",
            "Copyright (c) 2026 Jason Darlington and Production Pit Crew contributors",
            "Permission is hereby granted, free of charge",
            'THE SOFTWARE IS PROVIDED "AS IS"',
        ),
        "THIRD_PARTY_NOTICES.md": (
            "Copyright (c) 2025 AgentLand Contributors",
            "Permission is hereby granted, free of charge",
            "github.com/msitarzewski/agency-agents",
            "not affiliated with, sponsored by, or endorsed",
        ),
        "docs/origin-and-claims.md": (
            "What is original to this project",
            "What informed the project",
            "Safe public wording",
            "THIRD_PARTY_NOTICES.md",
        ),
    }
    for relative, fragments in required_fragments.items():
        path = repo / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            report.error(f"{relative}: required legal record cannot be read: {exc}")
            continue
        for fragment in fragments:
            if fragment not in text:
                report.error(f"{relative}: required legal notice is missing: {fragment!r}")


def lint_prompts(repo: Path, report: Report) -> None:
    prompt_files = list((repo / "agents").glob("*.toml")) + list((repo / "skills").glob("*/SKILL.md"))
    for path in prompt_files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for pattern, message in HYGIENE_RULES:
            match = pattern.search(text)
            if match:
                report.warning(f"{path.relative_to(repo)}: {message}: {match.group(0)!r}")


def validate_python(repo: Path, report: Report) -> None:
    for relative in (
        "scripts/build_release.py",
        "scripts/install_core.py",
        "scripts/validate.py",
        "scripts/windows_fs.py",
    ):
        path = repo / relative
        if not path.is_file():
            report.error(f"{relative}: required script is missing")
            continue
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
        except (OSError, UnicodeError, SyntaxError) as exc:
            report.error(f"{relative}: Python compilation failed: {exc}")


def validate_repo(repo: Path, strict: bool = False) -> Report:
    report = Report()
    repo = repo.resolve()
    manifest, _ownership = validate_manifest(repo, report)
    validate_plugin(repo, manifest, report)
    validate_agents(repo, manifest, report)
    validate_skills(repo, manifest, report)
    validate_filesystem(repo, report)
    validate_markdown_links(repo, report)
    validate_legal_notices(repo, report)
    lint_prompts(repo, report)
    validate_python(repo, report)
    if strict and report.warnings:
        report.errors.extend(f"strict: {warning}" for warning in report.warnings)
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Validate Production Pit Crew for Codex")
    result.add_argument("--strict", action="store_true", help="treat prompt-hygiene warnings as errors")
    result.add_argument("--repo", type=Path, help=argparse.SUPPRESS)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repo = (args.repo or Path(__file__).resolve().parent.parent).resolve()
    report = validate_repo(repo, strict=args.strict)
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if report.errors:
        print(f"Validation failed: {len(report.errors)} error(s), {len(report.warnings)} warning(s).", file=sys.stderr)
        return 1
    print(f"Validation passed: 4 agents, 4 skills, {len(regular_files(repo))} files checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
