#!/usr/bin/env python3
"""Safe, dependency-free installer for Production Pit Crew for Codex."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Iterable


EXIT_CLI = 2
EXIT_PACKAGE = 3
EXIT_CONFLICT = 4
EXIT_IO = 5
REPARSE_POINT = 0x400
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
SEMVER = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?")
MAX_JSON_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 4 * 1024 * 1024
PACK_ID = "production-pit-crew"
LEGACY_PACK_IDS = {"codex-workflow-crew"}
PACKAGE_MANIFEST = "pitcrew-package.json"


class PackageError(RuntimeError):
    pass


class ConflictError(RuntimeError):
    pass


class InstallIOError(RuntimeError):
    pass


@dataclass(frozen=True)
class Layout:
    roots: dict[str, Path]
    anchors: dict[str, Path]
    state_dir: Path


@dataclass(frozen=True)
class Entry:
    root: str
    relative: str
    source: Path
    digest: str
    content: bytes

    @property
    def key(self) -> tuple[str, str]:
        return self.root, self.relative


@dataclass(frozen=True)
class Action:
    verb: str
    root: str
    relative: str
    source: Path | None = None
    forced: bool = False
    expected_digest: str | None = None
    expect_absent: bool = False

    @property
    def key(self) -> tuple[str, str]:
        return self.root, self.relative


@dataclass(frozen=True)
class Ownership:
    paths: dict[str, set[str]]
    historical_hashes: dict[tuple[str, str], set[str]]


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PackageError(f"{label} must be a non-empty relative path")
    if "\x00" in value or "\\" in value or ":" in value:
        raise PackageError(f"{label} contains a non-portable path character: {value!r}")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        raise PackageError(f"{label} must be relative: {value!r}")
    if value.startswith("//") or any(part in {"", ".", ".."} for part in posix.parts):
        raise PackageError(f"{label} is not normalized: {value!r}")
    for part in posix.parts:
        if part.endswith((".", " ")):
            raise PackageError(f"{label} has a Windows-unsafe component: {part!r}")
        basename = part.split(".", 1)[0].upper()
        if basename in WINDOWS_RESERVED:
            raise PackageError(f"{label} uses a Windows-reserved name: {part!r}")
    normalized = posix.as_posix()
    if normalized != value:
        raise PackageError(f"{label} is not normalized: {value!r}")
    return normalized


def load_json(path: Path, label: str) -> dict:
    try:
        raw = read_regular_source(path, label, MAX_JSON_BYTES)
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackageError(f"cannot read {label} at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PackageError(f"{label} must contain a JSON object")
    return data


def is_linklike(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & REPARSE_POINT
    )


def reject_untrusted_writable_ancestors(path: Path, label: str) -> None:
    """Reject cross-user rename races on POSIX; same-user writers are not a boundary."""
    if os.name == "nt" or not hasattr(os, "geteuid"):
        return
    current = Path(os.path.abspath(path))
    while not current.exists():
        if current.parent == current:
            break
        current = current.parent
    while True:
        if is_linklike(current):
            raise ConflictError(f"{label} traverses a symlink: {current}")
        try:
            info = current.stat()
        except OSError as exc:
            raise InstallIOError(f"cannot inspect {label} ancestor {current}: {exc}") from exc
        if stat.S_ISDIR(info.st_mode):
            writable_by_others = bool(info.st_mode & (stat.S_IWGRP | stat.S_IWOTH))
            sticky = bool(info.st_mode & stat.S_ISVTX)
            if writable_by_others and not sticky:
                raise ConflictError(
                    f"{label} has a group/world-writable non-sticky ancestor: {current}"
                )
            if info.st_uid not in {0, os.geteuid()} and bool(info.st_mode & stat.S_IWUSR):
                raise ConflictError(
                    f"{label} has an ancestor controlled by another local account: {current}"
                )
        if current.parent == current:
            break
        current = current.parent


def require_regular_source(path: Path, label: str) -> None:
    if is_linklike(path):
        raise PackageError(f"{label} must not be a symlink or reparse point: {path}")
    try:
        info = path.stat()
    except OSError as exc:
        raise PackageError(f"cannot inspect {label} at {path}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise PackageError(f"{label} is not a regular file: {path}")


def read_regular_source(path: Path, label: str, max_bytes: int | None = None) -> bytes:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise PackageError(f"cannot open {label} without following links at {path}: {exc}") from exc
    chunks: list[bytes] = []
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise PackageError(f"{label} is not a regular file: {path}")
        if max_bytes is not None and info.st_size > max_bytes:
            raise PackageError(f"{label} exceeds the {max_bytes}-byte safety limit: {path}")
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            if max_bytes is not None and sum(map(len, chunks)) > max_bytes:
                raise PackageError(f"{label} exceeds the {max_bytes}-byte safety limit: {path}")
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def ensure_source_components(repo_root: Path, path: Path, label: str) -> None:
    try:
        relative = path.relative_to(repo_root)
    except ValueError as exc:
        raise PackageError(f"{label} escapes the package root: {path}") from exc
    current = repo_root
    for part in relative.parts:
        current = current / part
        if is_linklike(current):
            raise PackageError(f"{label} traverses a symlink or reparse point: {current}")


def walk_regular_files(repo_root: Path, directory: Path) -> Iterable[Path]:
    ensure_source_components(repo_root, directory, "skill source")
    if not directory.is_dir():
        raise PackageError(f"skill source is not a directory: {directory}")
    stack = [directory]
    while stack:
        current = stack.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.name.casefold())
        except OSError as exc:
            raise PackageError(f"cannot read skill source {current}: {exc}") from exc
        for child in children:
            ensure_source_components(repo_root, child, "skill source")
            if is_linklike(child):
                raise PackageError(f"skill source contains a symlink or reparse point: {child}")
            try:
                info = child.stat()
            except OSError as exc:
                raise PackageError(f"cannot inspect skill source {child}: {exc}") from exc
            if stat.S_ISDIR(info.st_mode):
                stack.append(child)
            elif stat.S_ISREG(info.st_mode):
                yield child
            else:
                raise PackageError(f"skill source contains a special file: {child}")


def build_entries(repo_root: Path, manifest: dict) -> list[Entry]:
    if manifest.get("schema_version") != 1:
        raise PackageError(f"unsupported {PACKAGE_MANIFEST} schema_version")
    if manifest.get("pack_id") != PACK_ID:
        raise PackageError("unexpected package id")
    version = manifest.get("version")
    if not isinstance(version, str) or SEMVER.fullmatch(version) is None:
        raise PackageError("package version must be a SemVer-like string")
    entries: list[Entry] = []
    seen: set[tuple[str, str]] = set()

    agents = manifest.get("agents")
    skills = manifest.get("skills")
    if not isinstance(agents, list) or not isinstance(skills, list):
        raise PackageError("package agents and skills must be arrays")

    for index, item in enumerate(agents):
        if not isinstance(item, dict):
            raise PackageError(f"agents[{index}] must be an object")
        source_rel = validate_relative(item.get("source"), f"agents[{index}].source")
        target = validate_relative(item.get("target"), f"agents[{index}].target")
        if "/" in target:
            raise PackageError(f"agent target must be a filename: {target!r}")
        if source_rel != f"agents/{target}":
            raise PackageError(
                f"agent source must be canonically bound to its target: agents/{target}"
            )
        if item.get("name") != PurePosixPath(target).stem:
            raise PackageError(f"agent name must match its target filename: {target!r}")
        source = repo_root.joinpath(*PurePosixPath(source_rel).parts)
        ensure_source_components(repo_root, source, "agent source")
        require_regular_source(source, "agent source")
        content = read_regular_source(source, "agent source", MAX_SOURCE_BYTES)
        try:
            agent_data = tomllib.loads(content.decode("utf-8"))
        except (UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise PackageError(f"agent source is not valid UTF-8 TOML: {source}: {exc}") from exc
        if agent_data.get("name") != item["name"]:
            raise PackageError(f"agent TOML name does not match manifest name: {source}")
        if any(
            not isinstance(agent_data.get(key), str) or not agent_data[key].strip()
            for key in ("name", "description", "developer_instructions")
        ):
            raise PackageError(f"agent TOML is missing required non-empty fields: {source}")
        entry = Entry("agents", target, source, sha256_bytes(content), content)
        folded = (entry.root, entry.relative.casefold())
        if folded in seen:
            raise PackageError(f"case-insensitive destination collision: {target}")
        seen.add(folded)
        entries.append(entry)

    for index, item in enumerate(skills):
        if not isinstance(item, dict):
            raise PackageError(f"skills[{index}] must be an object")
        name = validate_relative(item.get("name"), f"skills[{index}].name")
        if "/" in name:
            raise PackageError(f"skill name must be one directory component: {name!r}")
        source_rel = validate_relative(item.get("source"), f"skills[{index}].source")
        if source_rel != f"skills/{name}":
            raise PackageError(f"skill source must be canonically bound to its name: skills/{name}")
        source_dir = repo_root.joinpath(*PurePosixPath(source_rel).parts)
        child_names: set[str] = set()
        for source in walk_regular_files(repo_root, source_dir):
            child = source.relative_to(source_dir).as_posix()
            child_names.add(child)
            relative = validate_relative(f"{name}/{child}", "skill target")
            content = read_regular_source(source, "skill source", MAX_SOURCE_BYTES)
            entry = Entry("skills", relative, source, sha256_bytes(content), content)
            folded = (entry.root, entry.relative.casefold())
            if folded in seen:
                raise PackageError(f"case-insensitive destination collision: {relative}")
            seen.add(folded)
            entries.append(entry)
        if "SKILL.md" not in child_names:
            raise PackageError(f"skill source is missing SKILL.md: {source_dir}")

    if not entries:
        raise PackageError("package contains no installable files")
    return sorted(entries, key=lambda item: (item.root, item.relative.casefold()))


def load_ownership(repo_root: Path) -> Ownership:
    data = load_json(repo_root / "ownership.json", "ownership registry")
    if data.get("schema_version") != 1 or data.get("pack_id") != PACK_ID:
        raise PackageError("invalid ownership registry identity or schema")
    result: dict[str, set[str]] = {}
    for root, current_key, history_key in (
        ("agents", "agents", "historical_agents"),
        ("skills", "skill_files", "historical_skill_files"),
    ):
        values: list[str] = []
        for key in (current_key, history_key):
            raw = data.get(key)
            if not isinstance(raw, list):
                raise PackageError(f"ownership registry {key} must be an array")
            for index, value in enumerate(raw):
                normalized = validate_relative(value, f"ownership.{key}[{index}]")
                if root == "agents" and "/" in normalized:
                    raise PackageError(f"ownership name must be one component: {value!r}")
                if root == "skills" and "/" not in normalized:
                    raise PackageError(f"skill ownership must name an exact file below a skill directory: {value!r}")
                values.append(normalized)
        folded = [value.casefold() for value in values]
        if len(folded) != len(set(folded)):
            raise PackageError(f"ownership registry has duplicate {root} names")
        result[root] = set(values)
    historical_hashes: dict[tuple[str, str], set[str]] = {}
    raw_hashes = data.get("historical_hashes")
    if not isinstance(raw_hashes, dict):
        raise PackageError("ownership registry historical_hashes must be an object")
    for combined, digests in raw_hashes.items():
        normalized = validate_relative(combined, "ownership historical hash path")
        parts = PurePosixPath(normalized).parts
        if len(parts) < 2 or parts[0] not in {"agents", "skills"}:
            raise PackageError(f"historical hash path must start with agents/ or skills/: {combined!r}")
        root, relative = parts[0], PurePosixPath(*parts[1:]).as_posix()
        if relative not in result[root]:
            raise PackageError(f"historical hash path is not in the ownership registry: {combined!r}")
        if not isinstance(digests, list) or not digests:
            raise PackageError(f"historical hashes for {combined!r} must be a non-empty array")
        accepted: set[str] = set()
        for digest in digests:
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise PackageError(f"invalid historical SHA-256 for {combined!r}")
            accepted.add(digest)
        historical_hashes[(root, relative)] = accepted
    return Ownership(result, historical_hashes)


def destination_is_owned(root: str, relative: str, ownership: Ownership) -> bool:
    normalized = validate_relative(relative, "installed state path")
    if root == "agents":
        return "/" not in normalized and normalized in ownership.paths["agents"]
    if root == "skills":
        return normalized in ownership.paths["skills"]
    return False


def accepted_state_hashes(entries: list[Entry], ownership: Ownership) -> dict[tuple[str, str], set[str]]:
    result = {key: set(values) for key, values in ownership.historical_hashes.items()}
    for entry in entries:
        result.setdefault(entry.key, set()).add(entry.digest)
    return result


def resolve_layout(scope: str, project_dir: str | None) -> Layout:
    if scope == "project":
        project = Path(project_dir or os.getcwd()).expanduser()
        if not project.is_absolute():
            project = Path.cwd() / project
        try:
            project = project.resolve(strict=True)
        except OSError as exc:
            raise PackageError(f"project directory cannot be resolved: {exc}") from exc
        if not project.is_dir():
            raise PackageError(f"project directory is not a directory: {project}")
        return Layout(
            roots={"agents": project / ".codex" / "agents", "skills": project / ".agents" / "skills"},
            anchors={"agents": project, "skills": project},
            state_dir=project / ".cwc",
        )

    raw_codex_home = os.environ.get("CODEX_HOME")
    if raw_codex_home:
        candidate = Path(raw_codex_home).expanduser()
        if not candidate.is_absolute():
            raise PackageError("CODEX_HOME must be an absolute path when set")
        codex_home = candidate.resolve(strict=False)
    else:
        codex_home = (Path.home() / ".codex").resolve(strict=False)
    home = Path.home().resolve(strict=False)
    return Layout(
        roots={"agents": codex_home / "agents", "skills": home / ".agents" / "skills"},
        anchors={"agents": codex_home, "skills": home},
        state_dir=codex_home / ".cwc",
    )


def contained_path(root: Path, anchor: Path, relative: str) -> Path:
    relative = validate_relative(relative, "destination path")
    root_abs = Path(os.path.abspath(root))
    anchor_abs = Path(os.path.abspath(anchor))
    target = root_abs.joinpath(*PurePosixPath(relative).parts)
    try:
        root_abs.relative_to(anchor_abs)
        target.relative_to(root_abs)
    except ValueError as exc:
        raise PackageError(f"destination escapes its allowed root: {target}") from exc

    current = anchor_abs
    for part in root_abs.relative_to(anchor_abs).parts + PurePosixPath(relative).parts:
        current = current / part
        if is_linklike(current):
            raise ConflictError(f"destination traverses a symlink or reparse point: {current}")
    reject_untrusted_writable_ancestors(target.parent, "destination")
    return target


def inspect_destination(path: Path) -> str | None:
    if not path.exists() and not is_linklike(path):
        return None
    if is_linklike(path):
        raise ConflictError(f"destination is a symlink or reparse point: {path}")
    try:
        info = path.stat()
    except OSError as exc:
        raise InstallIOError(f"cannot inspect destination {path}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ConflictError(f"destination is not a regular file: {path}")
    return sha256_file(path)


def verify_action_target(action: Action, layout: Layout) -> tuple[Path, str | None]:
    target = contained_path(
        layout.roots[action.root], layout.anchors[action.root], action.relative
    )
    current = inspect_destination(target)
    if action.expect_absent:
        if current is not None:
            raise ConflictError(f"destination changed after preflight: expected absence at {target}")
    elif current != action.expected_digest:
        raise ConflictError(
            f"destination changed after preflight: expected {action.expected_digest}, found {current} at {target}"
        )
    return target, current


def state_path(layout: Layout) -> Path:
    return layout.state_dir / "codex-workflow-crew-state.json"


def validate_state_dir(layout: Layout) -> Path:
    anchor_abs = Path(os.path.abspath(layout.anchors["agents"]))
    directory = Path(os.path.abspath(layout.state_dir))
    try:
        relative = directory.relative_to(anchor_abs)
    except ValueError as exc:
        raise PackageError(f"install state directory escapes its allowed root: {directory}") from exc
    current = anchor_abs
    for part in relative.parts:
        current = current / part
        if is_linklike(current):
            raise ConflictError(f"install state traverses a symlink or reparse point: {current}")
    reject_untrusted_writable_ancestors(directory, "install state")
    return directory


def read_state(
    layout: Layout,
    ownership: Ownership,
    trusted_hashes: dict[tuple[str, str], set[str]],
) -> dict | None:
    validate_state_dir(layout)
    path = state_path(layout)
    if not path.exists() and not is_linklike(path):
        return None
    if is_linklike(path):
        raise PackageError(f"install state must not be a symlink or reparse point: {path}")
    try:
        raw_state = read_regular_source(path, "install state", MAX_JSON_BYTES)
        data = json.loads(raw_state.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackageError(f"cannot read install state at {path}: {exc}") from exc
    if is_linklike(path):
        raise PackageError(f"install state changed to a symlink or reparse point: {path}")
    if not isinstance(data, dict):
        raise PackageError("install state must contain a JSON object")
    if data.get("schema_version") != 1 or data.get("pack_id") not in {PACK_ID, *LEGACY_PACK_IDS}:
        raise PackageError("install state has an invalid identity or schema")
    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list):
        raise PackageError("install state entries must be an array")
    seen: set[tuple[str, str]] = set()
    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            raise PackageError(f"install state entry {index} must be an object")
        root = entry.get("root")
        relative = validate_relative(entry.get("relative"), f"state.entries[{index}].relative")
        digest = entry.get("sha256")
        if root not in {"agents", "skills"}:
            raise PackageError(f"install state entry {index} has an invalid root")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise PackageError(f"install state entry {index} has an invalid SHA-256")
        if not destination_is_owned(root, relative, ownership):
            raise PackageError(f"install state claims an unowned path: {root}/{relative}")
        if digest not in trusted_hashes.get((root, relative), set()):
            raise PackageError(
                f"install state claims an unrecognized package hash: {root}/{relative}"
            )
        key = (root, relative.casefold())
        if key in seen:
            raise PackageError(f"install state contains a duplicate path: {root}/{relative}")
        seen.add(key)
    data["_state_file_sha256"] = sha256_bytes(raw_state)
    return data


def state_entries(state: dict | None) -> dict[tuple[str, str], dict]:
    if state is None:
        return {}
    return {(item["root"], item["relative"]): item for item in state["entries"]}


def preflight_install(
    entries: list[Entry],
    old_state: dict | None,
    layout: Layout,
    ownership: Ownership,
    force: bool,
) -> list[Action]:
    actions: list[Action] = []
    old = state_entries(old_state)
    current = {entry.key: entry for entry in entries}

    old_skill_names = {
        PurePosixPath(relative).parts[0] for root, relative in old if root == "skills"
    }
    for skill_name in sorted({PurePosixPath(e.relative).parts[0] for e in entries if e.root == "skills"}):
        skill_root = contained_path(layout.roots["skills"], layout.anchors["skills"], skill_name)
        if skill_root.exists() or is_linklike(skill_root):
            if is_linklike(skill_root) or not skill_root.is_dir():
                raise ConflictError(f"skill destination is not a safe directory: {skill_root}")
            if skill_name not in old_skill_names and not force:
                raise ConflictError(
                    f"skill directory already exists and is not owned by this installation: {skill_root}; use --force to merge exact package files"
                )

    for entry in entries:
        target = contained_path(layout.roots[entry.root], layout.anchors[entry.root], entry.relative)
        installed_digest = inspect_destination(target)
        prior = old.get(entry.key)
        if installed_digest is None:
            actions.append(
                Action("CREATE", entry.root, entry.relative, entry.source, expect_absent=True)
            )
        elif installed_digest == entry.digest:
            actions.append(
                Action(
                    "UNCHANGED",
                    entry.root,
                    entry.relative,
                    entry.source,
                    expected_digest=installed_digest,
                )
            )
        elif prior and installed_digest == prior["sha256"]:
            actions.append(
                Action(
                    "UPDATE",
                    entry.root,
                    entry.relative,
                    entry.source,
                    expected_digest=installed_digest,
                )
            )
        elif force:
            actions.append(
                Action(
                    "UPDATE",
                    entry.root,
                    entry.relative,
                    entry.source,
                    forced=True,
                    expected_digest=installed_digest,
                )
            )
        else:
            raise ConflictError(
                f"refusing to overwrite unowned or modified file: {target}; use --force to back up and replace this exact file"
            )

    for key, prior in old.items():
        if key in current:
            continue
        root, relative = key
        if not destination_is_owned(root, relative, ownership):
            raise PackageError(f"retired path is not in the ownership registry: {root}/{relative}")
        target = contained_path(layout.roots[root], layout.anchors[root], relative)
        installed_digest = inspect_destination(target)
        if installed_digest is None:
            actions.append(Action("MISSING", root, relative, expect_absent=True))
        elif installed_digest == prior["sha256"]:
            actions.append(Action("REMOVE", root, relative, expected_digest=installed_digest))
        elif force:
            actions.append(
                Action("REMOVE", root, relative, forced=True, expected_digest=installed_digest)
            )
        else:
            raise ConflictError(f"retired installed file was modified: {target}; use --force to back up and remove it")
    return actions


def preflight_uninstall(
    old_state: dict | None,
    layout: Layout,
    force: bool,
) -> list[Action]:
    if old_state is None:
        return []
    actions: list[Action] = []
    for prior in old_state["entries"]:
        root, relative = prior["root"], prior["relative"]
        target = contained_path(layout.roots[root], layout.anchors[root], relative)
        installed_digest = inspect_destination(target)
        if installed_digest is None:
            actions.append(Action("MISSING", root, relative, expect_absent=True))
        elif installed_digest == prior["sha256"]:
            actions.append(Action("REMOVE", root, relative, expected_digest=installed_digest))
        elif force:
            actions.append(
                Action("REMOVE", root, relative, forced=True, expected_digest=installed_digest)
            )
        else:
            raise ConflictError(f"installed file was modified: {target}; uninstall aborted; use --force to back up and remove it")
    return actions


def format_action(action: Action, layout: Layout) -> str:
    suffix = " (forced; backup required)" if action.forced else ""
    target = contained_path(layout.roots[action.root], layout.anchors[action.root], action.relative)
    return f"{action.verb:9} {target}{suffix}"


def atomic_write(
    path: Path,
    data: bytes,
    mode: int = 0o644,
    safety_check: Callable[[], None] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = None
    temporary: Path | None = None
    try:
        handle = tempfile.NamedTemporaryFile(prefix=f".{path.name}.", dir=path.parent, delete=False)
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        handle = None
        if os.name != "nt":
            os.chmod(temporary, mode)
        if safety_check is not None:
            safety_check()
        os.replace(temporary, path)
    except OSError as exc:
        raise InstallIOError(f"atomic write failed for {path}: {exc}") from exc
    finally:
        if handle is not None:
            handle.close()
        if temporary is not None and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


def acquire_lock(layout: Layout) -> tuple[int, Path]:
    state_dir = validate_state_dir(layout)
    try:
        state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        validate_state_dir(layout)
        lock = state_dir / "codex-workflow-crew.lock"
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.write(descriptor, f"pid={os.getpid()} time={int(time.time())}\n".encode())
        os.fsync(descriptor)
        return descriptor, lock
    except FileExistsError as exc:
        raise ConflictError(
            f"another install may be running, or a prior run crashed: {layout.state_dir / 'codex-workflow-crew.lock'}; verify no installer is active, then remove that exact lock file"
        ) from exc
    except OSError as exc:
        raise InstallIOError(f"cannot acquire install lock: {exc}") from exc


def release_lock(descriptor: int, lock: Path) -> None:
    try:
        os.close(descriptor)
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            eprint(f"warning: could not remove install lock {lock}: {exc}")


def create_backup_root(layout: Layout) -> Path:
    state_dir = validate_state_dir(layout)
    base = state_dir / "backups"
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    validate_state_dir(layout)
    try:
        created = Path(tempfile.mkdtemp(prefix="transaction-", dir=base))
    except OSError as exc:
        raise InstallIOError(f"cannot create exclusive backup transaction directory: {exc}") from exc
    if is_linklike(created):
        raise ConflictError(f"backup transaction directory is link-like: {created}")
    return created


def persistent_backup_path(layout: Layout, backup_root: Path, root: str, relative: str) -> Path:
    state_dir = validate_state_dir(layout)
    root_backup = backup_root / root
    target = root_backup.joinpath(*PurePosixPath(validate_relative(relative, "backup path")).parts)
    try:
        backup_root.relative_to(state_dir / "backups")
        target.relative_to(root_backup)
    except ValueError as exc:
        raise PackageError(f"backup path escapes backup root: {target}") from exc
    current = state_dir
    for part in target.relative_to(state_dir).parts:
        current = current / part
        if is_linklike(current):
            raise ConflictError(f"backup destination traverses a symlink or reparse point: {current}")
    return target


def exclusive_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags, mode)
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    except FileExistsError as exc:
        raise ConflictError(f"refusing to overwrite an existing backup file: {path}") from exc
    except OSError as exc:
        raise InstallIOError(f"cannot create backup file {path}: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def verify_state_unchanged(layout: Layout, expected_digest: str | None) -> None:
    validate_state_dir(layout)
    current = inspect_destination(state_path(layout))
    if current != expected_digest:
        raise ConflictError("install state changed during the operation; no state mutation was performed")


def require_current_digest(path: Path, expected_digest: str | None, message: str) -> None:
    if inspect_destination(path) != expected_digest:
        raise ConflictError(f"{message}: {path}")


def apply_install(
    entries: list[Entry],
    actions: list[Action],
    manifest: dict,
    layout: Layout,
    old_state: dict | None,
) -> None:
    changed: list[tuple[Action, bytes | None, int, str | None]] = []
    entry_map = {entry.key: entry for entry in entries}
    backup_root = create_backup_root(layout) if any(action.forced for action in actions) else None
    try:
        for action in actions:
            if action.verb not in {"CREATE", "UPDATE", "REMOVE"}:
                continue
            target, current_digest = verify_action_target(action, layout)
            old_bytes = target.read_bytes() if current_digest is not None else None
            if old_bytes is not None and sha256_bytes(old_bytes) != current_digest:
                raise ConflictError(f"destination changed while it was being read: {target}")
            old_mode = stat.S_IMODE(target.stat().st_mode) if current_digest is not None else 0o644
            written_digest = entry_map[action.key].digest if action.verb in {"CREATE", "UPDATE"} else None
            if action.forced and old_bytes is not None:
                assert backup_root is not None
                backup = persistent_backup_path(layout, backup_root, action.root, action.relative)
                exclusive_write(backup, old_bytes, old_mode)
                print(f"BACKUP    {target} -> {backup}")
            verify_action_target(action, layout)
            if action.verb in {"CREATE", "UPDATE"}:
                entry = entry_map[action.key]
                atomic_write(
                    target,
                    entry.content,
                    safety_check=lambda a=action: verify_action_target(a, layout),
                )
            else:
                verify_action_target(action, layout)
                target.unlink()
            changed.append((action, old_bytes, old_mode, written_digest))

        new_state = {
            "schema_version": 1,
            "pack_id": manifest["pack_id"],
            "pack_version": manifest["version"],
            "entries": [
                {"root": entry.root, "relative": entry.relative, "sha256": entry.digest}
                for entry in entries
            ],
        }
        expected_state_digest = (
            old_state.get("_state_file_sha256") if old_state is not None else None
        )
        verify_state_unchanged(layout, expected_state_digest)
        atomic_write(
            state_path(layout),
            (json.dumps(new_state, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            0o600,
            safety_check=lambda: verify_state_unchanged(layout, expected_state_digest),
        )
    except Exception as exc:
        rollback_errors: list[str] = []
        for action, old_bytes, old_mode, written_digest in reversed(changed):
            try:
                target = contained_path(
                    layout.roots[action.root], layout.anchors[action.root], action.relative
                )
                current = inspect_destination(target)
                if current != written_digest:
                    raise ConflictError(
                        f"rollback target changed concurrently; preserved current content at {target}"
                    )
                if old_bytes is None:
                    if current is not None:
                        target.unlink()
                else:
                    atomic_write(
                        target,
                        old_bytes,
                        old_mode,
                        safety_check=lambda p=target, d=current: require_current_digest(
                            p, d, "rollback target changed concurrently"
                        ),
                    )
            except Exception as rollback_exc:  # best-effort recovery report
                rollback_errors.append(f"{target}: {rollback_exc}")
        if rollback_errors:
            raise InstallIOError(
                f"install failed ({exc}) and rollback was incomplete: {'; '.join(rollback_errors)}"
            ) from exc
        if isinstance(exc, (PackageError, ConflictError, InstallIOError)):
            raise
        raise InstallIOError(f"install failed and was rolled back: {exc}") from exc


def apply_uninstall(actions: list[Action], layout: Layout, old_state: dict) -> None:
    changed: list[tuple[Action, bytes, int]] = []
    backup_root = create_backup_root(layout) if any(action.forced for action in actions) else None
    try:
        for action in actions:
            if action.verb != "REMOVE":
                continue
            target, current_digest = verify_action_target(action, layout)
            if current_digest is None:
                continue
            old_bytes = target.read_bytes()
            if sha256_bytes(old_bytes) != current_digest:
                raise ConflictError(f"destination changed while it was being read: {target}")
            old_mode = stat.S_IMODE(target.stat().st_mode)
            if action.forced:
                assert backup_root is not None
                backup = persistent_backup_path(layout, backup_root, action.root, action.relative)
                exclusive_write(backup, old_bytes, old_mode)
                print(f"BACKUP    {target} -> {backup}")
            verify_action_target(action, layout)
            target.unlink()
            changed.append((action, old_bytes, old_mode))
        expected_state_digest = old_state["_state_file_sha256"]
        verify_state_unchanged(layout, expected_state_digest)
        try:
            state_path(layout).unlink()
        except FileNotFoundError:
            pass
    except Exception as exc:
        rollback_errors: list[str] = []
        for action, old_bytes, old_mode in reversed(changed):
            try:
                target = contained_path(
                    layout.roots[action.root], layout.anchors[action.root], action.relative
                )
                if inspect_destination(target) is not None:
                    raise ConflictError(
                        f"rollback target was recreated concurrently; preserved current content at {target}"
                    )
                atomic_write(
                    target,
                    old_bytes,
                    old_mode,
                    safety_check=lambda p=target: require_current_digest(
                        p, None, "rollback target was recreated concurrently"
                    ),
                )
            except Exception as rollback_exc:
                rollback_errors.append(f"{target}: {rollback_exc}")
        if rollback_errors:
            raise InstallIOError(
                f"uninstall failed ({exc}) and rollback was incomplete: {'; '.join(rollback_errors)}"
            ) from exc
        if isinstance(exc, (PackageError, ConflictError, InstallIOError)):
            raise
        raise InstallIOError(f"uninstall failed and was rolled back: {exc}") from exc


def run(args: argparse.Namespace, repo_root: Path) -> int:
    manifest = load_json(repo_root / PACKAGE_MANIFEST, "package manifest")
    ownership = load_ownership(repo_root)
    entries = build_entries(repo_root, manifest)
    trusted_hashes = accepted_state_hashes(entries, ownership)
    for entry in entries:
        if not destination_is_owned(entry.root, entry.relative, ownership):
            raise PackageError(
                f"package manifest targets a path absent from the exact ownership registry: {entry.root}/{entry.relative}"
            )
    layout = resolve_layout(args.scope, args.project_dir)
    print(f"Scope: {args.scope}")
    if args.scope == "project":
        print(f"Project root: {layout.anchors['agents']}")
    print(f"Agent root: {layout.roots['agents']}")
    print(f"Skill root: {layout.roots['skills']}")

    if os.name == "nt" and not args.dry_run:
        raise PackageError(
            "v0.1 supports validation and dry-run on Windows, but mutating install/uninstall is fail-closed until a handle-relative reparse-safe backend is available"
        )

    if args.dry_run:
        old_state = read_state(layout, ownership, trusted_hashes)
        actions = (
            preflight_uninstall(old_state, layout, args.force)
            if args.uninstall
            else preflight_install(entries, old_state, layout, ownership, args.force)
        )
        for action in actions:
            print(format_action(action, layout))
        print("Dry run complete; no files were changed.")
        return 0

    old_state = read_state(layout, ownership, trusted_hashes)
    if args.uninstall and old_state is None:
        print("Not installed; nothing to remove.")
        return 0
    # Complete a mutation-free preflight first. The same checks are repeated after
    # locking so a concurrent filesystem change cannot invalidate this result.
    if args.uninstall:
        preflight_uninstall(old_state, layout, args.force)
    else:
        preflight_install(entries, old_state, layout, ownership, args.force)

    descriptor, lock = acquire_lock(layout)
    try:
        old_state = read_state(layout, ownership, trusted_hashes)
        if args.uninstall and old_state is None:
            print("Not installed; nothing to remove.")
            return 0
        actions = (
            preflight_uninstall(old_state, layout, args.force)
            if args.uninstall
            else preflight_install(entries, old_state, layout, ownership, args.force)
        )
        for action in actions:
            print(format_action(action, layout))
        if args.uninstall:
            assert old_state is not None
            apply_uninstall(actions, layout, old_state)
            print("Uninstall complete.")
        else:
            apply_install(entries, actions, manifest, layout, old_state)
            print(f"Installed Production Pit Crew for Codex {manifest['version']}.")
        return 0
    finally:
        release_lock(descriptor, lock)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Install or uninstall Production Pit Crew for Codex")
    result.add_argument("--scope", choices=("project", "user"), required=True)
    result.add_argument("--project-dir", help="project root; defaults to the current directory")
    result.add_argument("--dry-run", action="store_true", help="validate and print actions without writing")
    result.add_argument("--force", action="store_true", help="back up and replace only conflicting owned targets")
    result.add_argument("--uninstall", action="store_true", help="remove files recorded by this pack")
    return result


def main(argv: list[str] | None = None) -> int:
    if sys.version_info < (3, 11):
        eprint("Production Pit Crew for Codex requires Python 3.11 or newer.")
        return EXIT_CLI
    try:
        args = parser().parse_args(argv)
        if args.scope == "user" and args.project_dir:
            raise PackageError("--project-dir is only valid with --scope project")
        repo_root = Path(__file__).resolve().parent.parent
        return run(args, repo_root)
    except ConflictError as exc:
        eprint(f"conflict: {exc}")
        return EXIT_CONFLICT
    except PackageError as exc:
        eprint(f"package error: {exc}")
        return EXIT_PACKAGE
    except (InstallIOError, OSError) as exc:
        eprint(f"I/O error: {exc}")
        return EXIT_IO


if __name__ == "__main__":
    raise SystemExit(main())
