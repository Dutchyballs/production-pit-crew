from __future__ import annotations

import datetime
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pitcrew_build_release", REPO / "scripts" / "build_release.py"
)
assert SPEC and SPEC.loader
BUILD_RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD_RELEASE)


class ReleaseArchiveTests(unittest.TestCase):
    def test_current_manifest_versions_match(self) -> None:
        self.assertEqual("0.1.0", BUILD_RELEASE.load_version(REPO))

    def test_archive_creation_forces_utc_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "release.zip"
            with mock.patch.object(BUILD_RELEASE, "run_git") as run_git:
                BUILD_RELEASE.create_archive(
                    REPO,
                    archive,
                    "production-pit-crew-0.1.0/",
                    "candidate-commit",
                )
            self.assertEqual("UTC", run_git.call_args.kwargs["environment"]["TZ"])
            self.assertEqual("archive", run_git.call_args.args[1])

    def test_real_archive_uses_commit_utc_timestamp(self) -> None:
        try:
            commit = BUILD_RELEASE.run_git(REPO, "rev-parse", "HEAD")
            commit_epoch = int(
                BUILD_RELEASE.run_git(REPO, "show", "-s", "--format=%ct", commit)
            )
        except (BUILD_RELEASE.ReleaseError, ValueError) as exc:
            self.skipTest(f"Git worktree is unavailable: {exc}")

        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "release.zip"
            BUILD_RELEASE.create_archive(
                REPO,
                archive,
                "production-pit-crew-0.1.0/",
                commit,
            )
            with zipfile.ZipFile(archive) as bundle:
                actual = bundle.getinfo(
                    "production-pit-crew-0.1.0/README.md"
                ).date_time

        expected_datetime = datetime.datetime.fromtimestamp(
            commit_epoch,
            tz=datetime.timezone.utc,
        )
        expected = (
            expected_datetime.year,
            expected_datetime.month,
            expected_datetime.day,
            expected_datetime.hour,
            expected_datetime.minute,
            expected_datetime.second - expected_datetime.second % 2,
        )
        self.assertEqual(expected, actual)

    def test_archive_inventory_and_crc_are_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "release.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("production-pit-crew-0.1.0/README.md", b"read me\n")
            BUILD_RELEASE.verify_archive(
                archive,
                "production-pit-crew-0.1.0/",
                {"README.md"},
            )

    def test_archive_member_cannot_escape_release_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("production-pit-crew-0.1.0/../outside.txt", b"unsafe\n")
            with self.assertRaises(BUILD_RELEASE.ReleaseError):
                BUILD_RELEASE.verify_archive(
                    archive,
                    "production-pit-crew-0.1.0/",
                    {"outside.txt"},
                )

    def test_archive_inventory_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "incomplete.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("production-pit-crew-0.1.0/README.md", b"read me\n")
            with self.assertRaises(BUILD_RELEASE.ReleaseError):
                BUILD_RELEASE.verify_archive(
                    archive,
                    "production-pit-crew-0.1.0/",
                    {"README.md", "LICENSE"},
                )

    def test_archive_requires_executable_bash_wrapper_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "non-executable.zip"
            member = zipfile.ZipInfo(
                "production-pit-crew-0.1.0/scripts/install.sh"
            )
            member.create_system = 3
            member.external_attr = 0o100644 << 16
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr(member, b"#!/usr/bin/env bash\n")
            with self.assertRaisesRegex(
                BUILD_RELEASE.ReleaseError,
                "executable metadata is missing",
            ):
                BUILD_RELEASE.verify_archive(
                    archive,
                    "production-pit-crew-0.1.0/",
                    {"scripts/install.sh"},
                )

    def test_archive_accepts_executable_bash_wrapper_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "executable.zip"
            member = zipfile.ZipInfo(
                "production-pit-crew-0.1.0/scripts/install.sh"
            )
            member.create_system = 3
            member.external_attr = 0o100755 << 16
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr(member, b"#!/usr/bin/env bash\n")
            BUILD_RELEASE.verify_archive(
                archive,
                "production-pit-crew-0.1.0/",
                {"scripts/install.sh"},
            )


if __name__ == "__main__":
    unittest.main()
