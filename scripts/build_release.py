#!/usr/bin/env python3
"""Build and verify a checksummed release archive from one clean Git commit."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


PACK_ID = "production-pit-crew"
REQUIRED_EXECUTABLES = {"scripts/install.sh"}


class ReleaseError(RuntimeError):
    pass


def run_git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseError(
            f"git {' '.join(arguments)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def load_version(repo: Path) -> str:
    try:
        package = json.loads((repo / "pitcrew-package.json").read_text(encoding="utf-8"))
        plugin = json.loads(
            (repo / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"cannot read release manifests: {exc}") from exc
    if package.get("pack_id") != PACK_ID or plugin.get("name") != PACK_ID:
        raise ReleaseError("package and plugin identities must match production-pit-crew")
    version = package.get("version")
    if not isinstance(version, str) or not version:
        raise ReleaseError("package version is missing")
    if plugin.get("version") != version:
        raise ReleaseError("package and plugin versions do not match")
    return version


def tracked_files(repo: Path, commit: str) -> set[str]:
    output = run_git(repo, "ls-tree", "-r", "--name-only", commit)
    return {line for line in output.splitlines() if line}


def verify_archive(archive: Path, prefix: str, expected_files: set[str]) -> None:
    try:
        with zipfile.ZipFile(archive) as bundle:
            bad_member = bundle.testzip()
            if bad_member is not None:
                raise ReleaseError(f"archive CRC verification failed at {bad_member}")
            actual_files: set[str] = set()
            for info in bundle.infolist():
                name = info.filename
                if "\\" in name or name.startswith(("/", "\\")):
                    raise ReleaseError(f"archive contains an unsafe member: {name!r}")
                parts = PurePosixPath(name).parts
                if not parts or parts[0] != prefix.rstrip("/") or ".." in parts:
                    raise ReleaseError(f"archive member escapes the release prefix: {name!r}")
                if info.is_dir():
                    continue
                relative = PurePosixPath(*parts[1:]).as_posix()
                if relative.startswith((".git/", ".cwc/", ".pitcrew/", "dist/")):
                    raise ReleaseError(f"archive contains excluded runtime data: {relative}")
                if relative in REQUIRED_EXECUTABLES:
                    unix_mode = (info.external_attr >> 16) & 0xFFFF
                    if info.create_system != 3 or not unix_mode & 0o111:
                        raise ReleaseError(
                            f"archive executable metadata is missing for: {relative}"
                        )
                actual_files.add(relative)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ReleaseError(f"cannot verify release archive {archive}: {exc}") from exc
    if actual_files != expected_files:
        raise ReleaseError(
            "archive inventory mismatch; "
            f"missing={sorted(expected_files - actual_files)}, "
            f"unexpected={sorted(actual_files - expected_files)}"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_extracted_archive(archive: Path, prefix: str) -> None:
    with tempfile.TemporaryDirectory(prefix="pitcrew-release-verify-") as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(root)
        extracted = root / prefix.rstrip("/")
        checks = (
            [sys.executable, "scripts/validate.py", "--strict"],
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        )
        for command in checks:
            result = subprocess.run(command, cwd=extracted, check=False)
            if result.returncode != 0:
                raise ReleaseError(
                    f"extracted archive check failed with exit {result.returncode}: {' '.join(command)}"
                )


def build(repo: Path, output_dir: Path, *, verify_extracted: bool) -> tuple[Path, Path]:
    top_level = Path(run_git(repo, "rev-parse", "--show-toplevel")).resolve()
    if top_level != repo.resolve():
        raise ReleaseError(f"run from the repository root: expected {top_level}, got {repo}")
    dirty = run_git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if dirty:
        raise ReleaseError("release archives require a clean Git working tree")

    version = load_version(repo)
    commit = run_git(repo, "rev-parse", "HEAD")
    prefix = f"{PACK_ID}-{version}/"
    expected_files = tracked_files(repo, commit)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{PACK_ID}-{version}.zip"
    temporary_archive = output_dir / f".{archive.name}.tmp"
    temporary_archive.unlink(missing_ok=True)
    try:
        run_git(
            repo,
            "archive",
            "--format=zip",
            f"--prefix={prefix}",
            f"--output={temporary_archive}",
            commit,
        )
        verify_archive(temporary_archive, prefix, expected_files)
        temporary_archive.replace(archive)
    finally:
        temporary_archive.unlink(missing_ok=True)

    checksum = sha256_file(archive)
    checksums = output_dir / "SHA256SUMS"
    checksums.write_text(f"{checksum}  {archive.name}\n", encoding="ascii", newline="\n")
    if verify_extracted:
        verify_extracted_archive(archive, prefix)
    print(f"Release commit: {commit}")
    print(f"Release archive: {archive}")
    print(f"SHA-256: {checksum}")
    return archive, checksums


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output-dir", type=Path, default=Path("dist"))
    result.add_argument(
        "--verify-extracted",
        action="store_true",
        help="extract the archive and rerun strict validation and the full test suite",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repo = Path(__file__).resolve().parent.parent
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = repo / output_dir
    try:
        build(repo, output_dir, verify_extracted=args.verify_extracted)
        return 0
    except (ReleaseError, OSError) as exc:
        print(f"release error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
