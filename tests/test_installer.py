"""End-to-end tests for the dependency-free Pit Crew installer.

Every test runs the real command-line entry point with an isolated home and an
isolated project.  The suite must never read from or write to the developer's
Codex configuration.
"""

from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest import mock
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "install_core.py"
MANIFEST = json.loads((REPO_ROOT / "pitcrew-package.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import install_core


def package_files() -> dict[tuple[str, str], bytes]:
    """Return the exact destination inventory and bytes declared by the pack."""

    inventory: dict[tuple[str, str], bytes] = {}
    for agent in MANIFEST["agents"]:
        inventory[("agents", agent["target"])] = (
            REPO_ROOT / agent["source"]
        ).read_bytes()
    for skill in MANIFEST["skills"]:
        source_root = REPO_ROOT / skill["source"]
        for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
            relative = source.relative_to(source_root).as_posix()
            inventory[("skills", f"{skill['name']}/{relative}")] = source.read_bytes()
    return inventory


PACKAGE_FILES = package_files()

LEGACY_SKILL_DESCRIPTIONS = {
    "pitcrew-plan-delivery": "Convert a product idea, feature request, specification, or unclear body of work into an evidence-based delivery plan with explicit scope, dependencies, acceptance criteria, risks, and verification. Use before implementation when Codex needs to plan a new project, break down a feature, repair a vague task list, or align work with an existing repository.",
    "pitcrew-design-interface": "Define an implementation-ready product interface contract covering user job, product identity, information hierarchy, interaction model, responsive behavior, states, accessibility, and visual direction. Use before building or materially redesigning a web, desktop, or mobile GUI when Codex must avoid generic AI-generated UI and align design choices with real product needs and an existing codebase.",
    "pitcrew-verify-browser": "Verify a web interface through real browser journeys, targeted screenshots, responsive checks, keyboard use, accessibility checks, console and network evidence, and existing automated tests. Use after UI implementation or during frontend debugging when Codex must report observed behavior honestly, distinguish defects from untested areas, and avoid biased QA or invented findings.",
    "pitcrew-gate-release": "Make an independent evidence-based release decision for a feature, interface, or application by comparing requirements with implementation, verification results, unresolved defects, operational readiness, and rollback safety. Use before release, handoff, merge, or production-readiness claims when Codex must return a fair PASS, HOLD, or BLOCKED decision without default failure or inflated approval.",
}

LEGACY_OPENAI_YAML = {
    "pitcrew-plan-delivery": """interface:
  display_name: CWC Plan Delivery
  short_description: Turn product ideas into build-ready plans
  default_prompt: Use $cwc-plan-delivery to turn this idea into a scoped, testable
    delivery plan.
  icon_small: assets/icon.svg
  icon_large: assets/icon.svg
policy:
  products:
  - chatgpt
  - codex
  - api
  - atlas
  allow_implicit_invocation: true
""",
    "pitcrew-design-interface": """interface:
  display_name: CWC Design Interface
  short_description: Define product-specific UI direction
  default_prompt: Use $cwc-design-interface to define a product-specific, implementation-ready
    interface contract.
  icon_small: assets/icon.svg
  icon_large: assets/icon.svg
policy:
  products:
  - chatgpt
  - codex
  - api
  - atlas
  allow_implicit_invocation: true
""",
    "pitcrew-verify-browser": """interface:
  display_name: CWC Verify Browser
  short_description: Test UI journeys with honest evidence
  default_prompt: Use $cwc-verify-browser to verify this interface across real browser
    journeys and viewports.
  icon_small: assets/icon.svg
  icon_large: assets/icon.svg
policy:
  products:
  - chatgpt
  - codex
  - api
  - atlas
  allow_implicit_invocation: true
""",
    "pitcrew-gate-release": """interface:
  display_name: CWC Gate Release
  short_description: Make evidence-based release decisions
  default_prompt: Use $cwc-gate-release to make an evidence-based pass or hold decision
    for this release.
  icon_small: assets/icon.svg
  icon_large: assets/icon.svg
policy:
  products:
  - chatgpt
  - codex
  - api
  - atlas
  allow_implicit_invocation: true
""",
}


def legacy_preview_files() -> dict[tuple[str, str], bytes]:
    """Reconstruct the complete v0.1 preview inventory and verify its recorded hashes."""

    inventory: dict[tuple[str, str], bytes] = {}
    for agent in MANIFEST["agents"]:
        current = (REPO_ROOT / agent["source"]).read_text(encoding="utf-8")
        legacy_relative = agent["target"].replace("pitcrew_", "cwc_", 1)
        legacy = current.replace("pitcrew_", "cwc_").replace("pitcrew-", "cwc-")
        legacy = legacy.replace(".pitcrew/evidence", ".cwc/evidence")
        inventory[("agents", legacy_relative)] = legacy.encode()
    for skill in MANIFEST["skills"]:
        current_name = skill["name"]
        legacy_name = current_name.replace("pitcrew-", "cwc-", 1)
        source_root = REPO_ROOT / skill["source"]
        for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
            child = source.relative_to(source_root).as_posix()
            if child == "SKILL.md":
                lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
                lines[1] = f"name: {legacy_name}\n"
                lines[2] = f"description: {LEGACY_SKILL_DESCRIPTIONS[current_name]}\n"
                contents = "".join(lines).encode()
            elif child == "agents/openai.yaml":
                contents = LEGACY_OPENAI_YAML[current_name].encode()
            else:
                contents = source.read_bytes()
                if source.suffix.lower() in {".json", ".md", ".svg", ".toml", ".yaml", ".yml"}:
                    contents = contents.replace(b"\r\n", b"\n")
            inventory[("skills", f"{legacy_name}/{child}")] = contents

    ownership = json.loads((REPO_ROOT / "ownership.json").read_text(encoding="utf-8"))
    expected = {
        ("agents", relative) for relative in ownership["historical_agents"]
    } | {
        ("skills", relative) for relative in ownership["historical_skill_files"]
    }
    if set(inventory) != expected:
        raise AssertionError("legacy preview fixture does not match the historical ownership registry")
    for (root, relative), contents in inventory.items():
        digest = hashlib.sha256(contents).hexdigest()
        if digest not in ownership["historical_hashes"].get(f"{root}/{relative}", []):
            raise AssertionError(f"legacy preview hash mismatch: {root}/{relative}")
    return inventory


LEGACY_PREVIEW_FILES = legacy_preview_files()


class PathValidationTests(unittest.TestCase):
    def test_windows_unsafe_relative_names_are_rejected_on_every_host(self) -> None:
        unsafe = (
            "CON.txt",
            "com¹.log",
            "LPT²",
            "folder/trailing. ",
            "folder/has?.md",
            "folder/has*.md",
            "folder/has|pipe.md",
            "folder/control\x1f.md",
            "C:/drive/path.md",
            "folder/stream:name.md",
            "folder\\backslash.md",
        )
        for value in unsafe:
            with self.subTest(value=value):
                with self.assertRaises(install_core.PackageError):
                    install_core.validate_relative(value, "test path")

    def test_normal_portable_relative_name_is_accepted(self) -> None:
        value = "pitcrew-plan-delivery/references/planning-checklist.md"
        self.assertEqual(value, install_core.validate_relative(value, "test path"))


class InstallerTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="pitcrew-installer-test-")
        self.addCleanup(self.tempdir.cleanup)
        self.sandbox = Path(self.tempdir.name)
        self.home = self.sandbox / "isolated home"
        self.codex_home = self.sandbox / "isolated codex home"
        self.home.mkdir()
        self.codex_home.mkdir()

    def isolated_env(self, *, codex_home: str | Path | None = None) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["USERPROFILE"] = str(self.home)
        env["CODEX_HOME"] = str(self.codex_home if codex_home is None else codex_home)
        # Keep Python startup deterministic and avoid importing user-level packages.
        env["PYTHONNOUSERSITE"] = "1"
        env.pop("PYTHONHOME", None)
        return env

    def run_installer(
        self,
        *arguments: str,
        env: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INSTALLER), *arguments],
            cwd=str(cwd or REPO_ROOT),
            env=env or self.isolated_env(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def project_roots(self, project: Path) -> dict[str, Path]:
        return {
            "agents": project / ".codex" / "agents",
            "skills": project / ".agents" / "skills",
        }

    def destination(self, roots: dict[str, Path], key: tuple[str, str]) -> Path:
        root, relative = key
        return roots[root].joinpath(*PurePosixPath(relative).parts)

    def assert_package_installed(self, roots: dict[str, Path]) -> None:
        for key, expected in PACKAGE_FILES.items():
            with self.subTest(destination=key):
                target = self.destination(roots, key)
                self.assertTrue(target.is_file(), f"missing installed file: {target}")
                self.assertEqual(expected, target.read_bytes())

    def assert_no_package_files(self, roots: dict[str, Path]) -> None:
        for key in PACKAGE_FILES:
            with self.subTest(destination=key):
                self.assertFalse(self.destination(roots, key).exists())

    def install_project(self, project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return self.run_installer(
            "--scope",
            "project",
            "--project-dir",
            str(project),
            *extra,
        )

    def test_project_fresh_install_writes_manifest_and_exact_inventory(self) -> None:
        project = self.sandbox / "project"
        project.mkdir()

        result = self.install_project(project)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Installed Production Pit Crew for Codex", result.stdout)
        roots = self.project_roots(project)
        self.assert_package_installed(roots)
        state_path = project / ".cwc" / "codex-workflow-crew-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(1, state["schema_version"])
        self.assertEqual("production-pit-crew", state["pack_id"])
        self.assertEqual(MANIFEST["version"], state["pack_version"])
        self.assertEqual(len(PACKAGE_FILES), len(state["entries"]))
        self.assertEqual(
            set(PACKAGE_FILES),
            {(entry["root"], entry["relative"]) for entry in state["entries"]},
        )
        self.assertFalse((project / ".cwc" / "codex-workflow-crew.lock").exists())

    def test_dry_run_performs_zero_writes(self) -> None:
        project = self.sandbox / "dry run project"
        project.mkdir()
        before = set(project.iterdir())

        result = self.install_project(project, "--dry-run")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Dry run complete; no files were changed.", result.stdout)
        self.assertEqual(before, set(project.iterdir()))
        self.assertFalse((project / ".cwc").exists())
        self.assert_no_package_files(self.project_roots(project))

    def test_identical_reinstall_is_idempotent(self) -> None:
        project = self.sandbox / "idempotent"
        project.mkdir()
        first = self.install_project(project)
        self.assertEqual(0, first.returncode, first.stderr)
        roots = self.project_roots(project)
        mtimes = {
            key: self.destination(roots, key).stat().st_mtime_ns for key in PACKAGE_FILES
        }

        second = self.install_project(project)

        self.assertEqual(0, second.returncode, second.stderr)
        self.assertNotIn("UPDATE", second.stdout)
        self.assertNotIn("CREATE", second.stdout)
        self.assertEqual(len(PACKAGE_FILES), second.stdout.count("UNCHANGED"))
        self.assert_package_installed(roots)
        self.assertEqual(
            mtimes,
            {key: self.destination(roots, key).stat().st_mtime_ns for key in PACKAGE_FILES},
        )

    def test_existing_lock_blocks_mutation_and_preserves_installed_files(self) -> None:
        project = self.sandbox / "locked project"
        project.mkdir()
        first = self.install_project(project)
        self.assertEqual(0, first.returncode, first.stderr)
        roots = self.project_roots(project)
        before = {key: self.destination(roots, key).read_bytes() for key in PACKAGE_FILES}
        lock = project / ".cwc" / "codex-workflow-crew.lock"
        lock.write_bytes(b"pid=someone-else\n")

        result = self.install_project(project)

        self.assertEqual(4, result.returncode, result.stderr)
        self.assertIn("another install may be running", result.stderr)
        self.assertEqual(
            before,
            {key: self.destination(roots, key).read_bytes() for key in PACKAGE_FILES},
        )
        self.assertEqual(b"pid=someone-else\n", lock.read_bytes())
        lock.unlink()

    def test_unowned_conflict_aborts_before_any_package_file_is_written(self) -> None:
        project = self.sandbox / "atomic conflict"
        project.mkdir()
        roots = self.project_roots(project)
        conflict_key = ("agents", MANIFEST["agents"][0]["target"])
        conflict = self.destination(roots, conflict_key)
        conflict.parent.mkdir(parents=True)
        conflict.write_bytes(b"user-owned agent\n")

        result = self.install_project(project)

        self.assertEqual(4, result.returncode)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(b"user-owned agent\n", conflict.read_bytes())
        for key in PACKAGE_FILES:
            if key != conflict_key:
                self.assertFalse(self.destination(roots, key).exists(), key)
        self.assertFalse((project / ".cwc" / "codex-workflow-crew-state.json").exists())
        self.assertFalse((project / ".cwc" / "codex-workflow-crew.lock").exists())

    def test_force_backs_up_conflict_before_replacing_it(self) -> None:
        project = self.sandbox / "forced conflict"
        project.mkdir()
        roots = self.project_roots(project)
        conflict_key = ("agents", MANIFEST["agents"][0]["target"])
        conflict = self.destination(roots, conflict_key)
        conflict.parent.mkdir(parents=True)
        original = b"custom user version\n"
        conflict.write_bytes(original)

        result = self.install_project(project, "--force")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("BACKUP", result.stdout)
        self.assert_package_installed(roots)
        backups = list(
            (project / ".cwc" / "backups").glob(
                f"*/agents/{MANIFEST['agents'][0]['target']}"
            )
        )
        self.assertEqual(1, len(backups), backups)
        self.assertEqual(original, backups[0].read_bytes())

    def test_uninstall_removes_exact_owned_files_and_preserves_user_files(self) -> None:
        project = self.sandbox / "careful uninstall"
        project.mkdir()
        installed = self.install_project(project)
        self.assertEqual(0, installed.returncode, installed.stderr)
        roots = self.project_roots(project)
        unrelated_agent = roots["agents"] / "my_agent.toml"
        unrelated_agent.write_text("name = 'mine'\n", encoding="utf-8")
        added_inside_skill = roots["skills"] / MANIFEST["skills"][0]["name"] / "user-note.txt"
        added_inside_skill.write_text("do not delete\n", encoding="utf-8")
        unrelated_skill = roots["skills"] / "my-skill" / "SKILL.md"
        unrelated_skill.parent.mkdir(parents=True)
        unrelated_skill.write_text("mine\n", encoding="utf-8")

        result = self.install_project(project, "--uninstall")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Uninstall complete.", result.stdout)
        self.assert_no_package_files(roots)
        self.assertEqual("name = 'mine'\n", unrelated_agent.read_text(encoding="utf-8"))
        self.assertEqual("do not delete\n", added_inside_skill.read_text(encoding="utf-8"))
        self.assertEqual("mine\n", unrelated_skill.read_text(encoding="utf-8"))
        self.assertFalse((project / ".cwc" / "codex-workflow-crew-state.json").exists())

    def test_clean_uninstall_can_be_reinstalled_without_force(self) -> None:
        project = self.sandbox / "reinstall after uninstall"
        project.mkdir()
        installed = self.install_project(project)
        self.assertEqual(0, installed.returncode, installed.stderr)

        removed = self.install_project(project, "--uninstall")
        self.assertEqual(0, removed.returncode, removed.stderr)
        roots = self.project_roots(project)
        self.assert_no_package_files(roots)
        for skill in MANIFEST["skills"]:
            self.assertTrue((roots["skills"] / skill["name"]).is_dir())

        reinstalled = self.install_project(project)

        self.assertEqual(0, reinstalled.returncode, reinstalled.stderr)
        self.assert_package_installed(roots)

    def test_modified_installed_file_blocks_the_entire_uninstall(self) -> None:
        project = self.sandbox / "modified install"
        project.mkdir()
        installed = self.install_project(project)
        self.assertEqual(0, installed.returncode, installed.stderr)
        roots = self.project_roots(project)
        modified_key = next(reversed(PACKAGE_FILES))
        modified = self.destination(roots, modified_key)
        modified.write_bytes(b"locally modified\n")

        result = self.install_project(project, "--uninstall")

        self.assertEqual(4, result.returncode)
        self.assertIn("uninstall aborted", result.stderr)
        for key, expected in PACKAGE_FILES.items():
            target = self.destination(roots, key)
            self.assertTrue(target.is_file(), key)
            self.assertEqual(b"locally modified\n" if key == modified_key else expected, target.read_bytes())
        self.assertTrue((project / ".cwc" / "codex-workflow-crew-state.json").is_file())

    def test_tampered_state_path_is_rejected_and_outside_sentinel_survives(self) -> None:
        project = self.sandbox / "tampered state"
        project.mkdir()
        installed = self.install_project(project)
        self.assertEqual(0, installed.returncode, installed.stderr)
        sentinel = self.sandbox / "outside-sentinel.txt"
        sentinel.write_bytes(b"never touch me\n")
        state_path = project / ".cwc" / "codex-workflow-crew-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["entries"][0]["relative"] = "../../outside-sentinel.txt"
        state_path.write_text(json.dumps(state), encoding="utf-8")

        result = self.install_project(project, "--uninstall")

        self.assertEqual(3, result.returncode)
        self.assertIn("state.entries[0].relative", result.stderr)
        self.assertEqual(b"never touch me\n", sentinel.read_bytes())
        self.assert_package_installed(self.project_roots(project))

    def test_tampered_state_cannot_claim_user_file_inside_owned_skill(self) -> None:
        project = self.sandbox / "tampered exact ownership"
        project.mkdir()
        installed = self.install_project(project)
        self.assertEqual(0, installed.returncode, installed.stderr)
        roots = self.project_roots(project)
        user_file = roots["skills"] / MANIFEST["skills"][0]["name"] / "user-added.md"
        user_file.write_bytes(b"belongs to the user\n")
        state_path = project / ".cwc" / "codex-workflow-crew-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["entries"].append(
            {
                "root": "skills",
                "relative": f"{MANIFEST['skills'][0]['name']}/user-added.md",
                "sha256": "0" * 64,
            }
        )
        state_path.write_text(json.dumps(state), encoding="utf-8")

        result = self.install_project(project, "--uninstall", "--force")

        self.assertEqual(3, result.returncode)
        self.assertIn("unowned path", result.stderr)
        self.assertEqual(b"belongs to the user\n", user_file.read_bytes())
        self.assert_package_installed(roots)

    def test_tampered_state_hash_cannot_adopt_content_at_owned_path(self) -> None:
        project = self.sandbox / "forged state hash"
        project.mkdir()
        installed = self.install_project(project)
        self.assertEqual(0, installed.returncode, installed.stderr)
        roots = self.project_roots(project)
        key = ("agents", MANIFEST["agents"][0]["target"])
        target = self.destination(roots, key)
        custom = b"custom agent content\n"
        target.write_bytes(custom)
        state_path = project / ".cwc" / "codex-workflow-crew-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        for entry in state["entries"]:
            if (entry["root"], entry["relative"]) == key:
                import hashlib

                entry["sha256"] = hashlib.sha256(custom).hexdigest()
                break
        state_path.write_text(json.dumps(state), encoding="utf-8")

        result = self.install_project(project, "--uninstall")

        self.assertEqual(3, result.returncode)
        self.assertIn("unrecognized package hash", result.stderr)
        self.assertEqual(custom, target.read_bytes())

    def test_user_scope_uses_codex_home_for_agents_and_home_for_skills(self) -> None:
        result = self.run_installer("--scope", "user")

        self.assertEqual(0, result.returncode, result.stderr)
        roots = {
            "agents": self.codex_home / "agents",
            "skills": self.home / ".agents" / "skills",
        }
        self.assert_package_installed(roots)
        self.assertTrue(
            (self.codex_home / ".cwc" / "codex-workflow-crew-state.json").is_file()
        )
        self.assertFalse((self.home / ".codex" / "agents").exists())

        removed = self.run_installer("--scope", "user", "--uninstall")
        self.assertEqual(0, removed.returncode, removed.stderr)
        self.assert_no_package_files(roots)

    def test_relative_codex_home_is_rejected_without_writes(self) -> None:
        env = self.isolated_env(codex_home="relative-codex-home")
        before = set(self.sandbox.rglob("*"))

        result = self.run_installer("--scope", "user", env=env, cwd=self.sandbox)

        self.assertEqual(3, result.returncode)
        self.assertIn("CODEX_HOME must be an absolute path", result.stderr)
        self.assertEqual(before, set(self.sandbox.rglob("*")))
        self.assertFalse((self.sandbox / "relative-codex-home").exists())

    def test_spaces_and_unicode_in_project_path(self) -> None:
        project = self.sandbox / "Mahi tahi — kaupapa U0001f96d"
        project.mkdir()

        installed = self.install_project(project)
        self.assertEqual(0, installed.returncode, installed.stderr)
        self.assert_package_installed(self.project_roots(project))

        removed = self.install_project(project, "--uninstall")
        self.assertEqual(0, removed.returncode, removed.stderr)
        self.assert_no_package_files(self.project_roots(project))

    def test_destination_symlink_escape_is_rejected_where_supported(self) -> None:
        project = self.sandbox / "symlink project"
        project.mkdir()
        outside = self.sandbox / "outside destination"
        outside.mkdir()
        sentinel = outside / "sentinel.txt"
        sentinel.write_bytes(b"safe\n")
        link = project / ".codex"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlinks are unavailable: {exc}")

        result = self.install_project(project)

        self.assertEqual(4, result.returncode)
        self.assertIn("traverses a symlink or reparse point", result.stderr)
        self.assertEqual(b"safe\n", sentinel.read_bytes())
        self.assertEqual([sentinel], list(outside.iterdir()))
        self.assertFalse((project / ".cwc" / "codex-workflow-crew-state.json").exists())

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_destination_junction_escape_is_rejected_without_symlink_privilege(self) -> None:
        project = self.sandbox / "junction project"
        project.mkdir()
        outside = self.sandbox / "outside junction destination"
        outside.mkdir()
        sentinel = outside / "sentinel.txt"
        sentinel.write_bytes(b"safe\n")
        junction = project / ".codex"
        created = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(outside)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(0, created.returncode, created.stderr or created.stdout)
        self.addCleanup(lambda: junction.exists() and junction.rmdir())

        result = self.install_project(project)

        self.assertEqual(4, result.returncode, result.stderr)
        self.assertIn("reparse point", result.stderr)
        self.assertEqual(b"safe\n", sentinel.read_bytes())
        self.assertEqual([sentinel], list(outside.iterdir()))
        self.assertFalse((project / ".cwc" / "codex-workflow-crew-state.json").exists())

    @unittest.skipUnless(os.name == "nt", "Windows handle-pinning test")
    def test_windows_atomic_write_pins_destination_ancestry_against_swap(self) -> None:
        import windows_fs

        parent = self.sandbox / "pinned ancestry" / "destination"
        parent.mkdir(parents=True)
        target = parent / "result.txt"
        moved = parent.with_name("moved destination")
        swap_attempted = False

        def attempt_ancestry_swap() -> None:
            nonlocal swap_attempted
            swap_attempted = True
            with self.assertRaises(OSError):
                parent.rename(moved)

        windows_fs.atomic_write(target, b"pinned\n", attempt_ancestry_swap)

        self.assertTrue(swap_attempted)
        self.assertEqual(b"pinned\n", target.read_bytes())
        self.assertFalse(moved.exists())

    def test_manifest_cannot_target_path_absent_from_exact_ownership(self) -> None:
        copied_repo = self.sandbox / "modified package"
        shutil.copytree(REPO_ROOT, copied_repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        manifest = json.loads((copied_repo / "pitcrew-package.json").read_text(encoding="utf-8"))
        manifest["agents"][0]["target"] = "injected.toml"
        (copied_repo / "pitcrew-package.json").write_text(json.dumps(manifest), encoding="utf-8")
        project = self.sandbox / "ownership-bound project"
        project.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                str(copied_repo / "scripts" / "install_core.py"),
                "--scope",
                "project",
                "--project-dir",
                str(project),
            ],
            env=self.isolated_env(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(3, result.returncode)
        self.assertIn("canonically bound", result.stderr)
        self.assertFalse((project / ".codex").exists())
        self.assertFalse((project / ".agents").exists())
        self.assertFalse((project / ".cwc").exists())

    @unittest.skipUnless(os.name != "nt", "Bash wrapper test")
    def test_bash_wrapper_rejects_symlinked_invocation(self) -> None:
        link_dir = self.sandbox / "wrapper link"
        link_dir.mkdir()
        link = link_dir / "install.sh"
        link.symlink_to(REPO_ROOT / "scripts" / "install.sh")

        result = subprocess.run(
            ["bash", str(link), "--scope", "project", "--project-dir", str(self.sandbox)],
            env=self.isolated_env(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(2, result.returncode)
        self.assertIn("Refusing symlinked invocation", result.stderr)

    def test_untouched_previous_version_upgrades_with_trusted_historical_hash(self) -> None:
        project = self.sandbox / "upgrade project"
        project.mkdir()
        installed = self.install_project(project)
        self.assertEqual(0, installed.returncode, installed.stderr)

        upgraded_repo = self.sandbox / "upgraded package"
        shutil.copytree(REPO_ROOT, upgraded_repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        manifest_path = upgraded_repo / "pitcrew-package.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = "0.2.0"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        source_rel = manifest["agents"][0]["source"]
        source = upgraded_repo / source_rel
        old_bytes = source.read_bytes()
        source.write_bytes(old_bytes + b"\n# v0.2 test change\n")
        import hashlib

        ownership_path = upgraded_repo / "ownership.json"
        ownership = json.loads(ownership_path.read_text(encoding="utf-8"))
        ownership["historical_hashes"] = {
            f"agents/{manifest['agents'][0]['target']}": [hashlib.sha256(old_bytes).hexdigest()]
        }
        ownership_path.write_text(json.dumps(ownership), encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(upgraded_repo / "scripts" / "install_core.py"),
                "--scope",
                "project",
                "--project-dir",
                str(project),
            ],
            env=self.isolated_env(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("UPDATE", result.stdout)
        target = project / ".codex" / "agents" / manifest["agents"][0]["target"]
        self.assertEqual(source.read_bytes(), target.read_bytes())
        state = json.loads(
            (project / ".cwc" / "codex-workflow-crew-state.json").read_text(encoding="utf-8")
        )
        self.assertEqual("0.2.0", state["pack_version"])

    def test_complete_legacy_preview_migrates_and_uninstalls_cleanly(self) -> None:
        project = self.sandbox / "legacy preview migration"
        project.mkdir()
        roots = self.project_roots(project)
        entries = []
        for (root, relative), contents in LEGACY_PREVIEW_FILES.items():
            target = self.destination(roots, (root, relative))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents)
            entries.append(
                {
                    "root": root,
                    "relative": relative,
                    "sha256": hashlib.sha256(contents).hexdigest(),
                }
            )
        state_path = project / ".cwc" / "codex-workflow-crew-state.json"
        state_path.parent.mkdir()
        state_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "pack_id": "codex-workflow-crew",
                    "pack_version": "0.1.0",
                    "entries": entries,
                }
            ),
            encoding="utf-8",
        )

        result = self.install_project(project)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(len(LEGACY_PREVIEW_FILES), result.stdout.count("REMOVE"))
        for key in LEGACY_PREVIEW_FILES:
            self.assertFalse(self.destination(roots, key).exists())
        self.assert_package_installed(roots)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual("production-pit-crew", state["pack_id"])

        uninstall = self.install_project(project, "--uninstall")

        self.assertEqual(0, uninstall.returncode, uninstall.stderr)
        self.assert_no_package_files(roots)
        self.assertFalse(state_path.exists())

    def test_mid_commit_failure_rolls_back_written_files(self) -> None:
        project = self.sandbox / "rollback project"
        project.mkdir()
        real_atomic_write = install_core.atomic_write
        calls = 0

        def fail_once(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise install_core.InstallIOError("simulated mid-commit failure")
            return real_atomic_write(*args, **kwargs)

        with mock.patch.dict(os.environ, self.isolated_env(), clear=True):
            with mock.patch.object(install_core, "atomic_write", side_effect=fail_once):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    result = install_core.main(
                        ["--scope", "project", "--project-dir", str(project)]
                    )

        self.assertEqual(5, result)
        self.assert_no_package_files(self.project_roots(project))
        self.assertFalse((project / ".cwc" / "codex-workflow-crew-state.json").exists())
        self.assertFalse((project / ".cwc" / "codex-workflow-crew.lock").exists())

    def test_mid_uninstall_failure_restores_removed_files_and_state(self) -> None:
        project = self.sandbox / "uninstall rollback project"
        project.mkdir()
        installed = self.install_project(project)
        self.assertEqual(0, installed.returncode, installed.stderr)
        state_path = project / ".cwc" / "codex-workflow-crew-state.json"
        original_state = state_path.read_bytes()
        real_remove = install_core.remove_regular
        calls = 0

        def fail_once(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise install_core.InstallIOError("simulated uninstall failure")
            return real_remove(*args, **kwargs)

        with mock.patch.dict(os.environ, self.isolated_env(), clear=True):
            with mock.patch.object(install_core, "remove_regular", side_effect=fail_once):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    result = install_core.main(
                        ["--scope", "project", "--project-dir", str(project), "--uninstall"]
                    )

        self.assertEqual(5, result)
        self.assert_package_installed(self.project_roots(project))
        self.assertEqual(original_state, state_path.read_bytes())
        self.assertFalse((project / ".cwc" / "codex-workflow-crew.lock").exists())


if __name__ == "__main__":
    unittest.main()
