from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
SPEC = importlib.util.spec_from_file_location("pitcrew_validate", REPO / "scripts" / "validate.py")
assert SPEC and SPEC.loader
VALIDATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATE
SPEC.loader.exec_module(VALIDATE)


class ValidatorTests(unittest.TestCase):
    def copy_repo(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        target = Path(temporary.name) / "repo"
        shutil.copytree(
            REPO,
            target,
            ignore=shutil.ignore_patterns(".git", ".cwc", ".pitcrew", "__pycache__", "*.pyc"),
        )
        return temporary, target

    def test_clean_repository_passes_strict_validation(self) -> None:
        report = VALIDATE.validate_repo(REPO, strict=True)
        self.assertEqual([], report.errors)

    def test_invalid_agent_toml_fails(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        (repo / "agents" / "pitcrew_ui_critic.toml").write_text("name = [\n", encoding="utf-8")
        report = VALIDATE.validate_repo(repo)
        self.assertTrue(any("invalid TOML" in error for error in report.errors))

    def test_missing_manifest_source_fails(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        (repo / "agents" / "pitcrew_ui_critic.toml").unlink()
        report = VALIDATE.validate_repo(repo)
        self.assertTrue(report.errors)

    def test_plugin_version_must_match_package(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        plugin = repo / ".codex-plugin" / "plugin.json"
        plugin.write_text(
            plugin.read_text(encoding="utf-8").replace('"version": "0.1.0"', '"version": "9.9.9"'),
            encoding="utf-8",
        )
        report = VALIDATE.validate_repo(repo)
        self.assertTrue(any("version must match" in error for error in report.errors))

    def test_official_plugin_publication_metadata_is_accepted(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        plugin_path = repo / ".codex-plugin" / "plugin.json"
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
        plugin.update(
            {
                "author": {"name": "Pit Crew maintainers", "url": "https://example.com"},
                "homepage": "https://example.com/production-pit-crew",
                "repository": "https://github.com/example/production-pit-crew",
            }
        )
        plugin_path.write_text(json.dumps(plugin), encoding="utf-8")

        report = VALIDATE.validate_repo(repo)

        self.assertEqual([], report.errors)

    def test_unsupported_plugin_hooks_fail(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        plugin_path = repo / ".codex-plugin" / "plugin.json"
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
        plugin["hooks"] = ["./hooks/session.json"]
        plugin_path.write_text(json.dumps(plugin), encoding="utf-8")

        report = VALIDATE.validate_repo(repo)

        self.assertTrue(any("unsupported keys" in error and "hooks" in error for error in report.errors))

    def test_invalid_plugin_keywords_type_fails(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        plugin_path = repo / ".codex-plugin" / "plugin.json"
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
        plugin["keywords"] = "not-a-list"
        plugin_path.write_text(json.dumps(plugin), encoding="utf-8")

        report = VALIDATE.validate_repo(repo)

        self.assertTrue(any("keywords must be" in error for error in report.errors))

    def test_missing_official_plugin_interface_metadata_fails(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        plugin_path = repo / ".codex-plugin" / "plugin.json"
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
        del plugin["interface"]["capabilities"]
        plugin_path.write_text(json.dumps(plugin), encoding="utf-8")

        report = VALIDATE.validate_repo(repo)

        self.assertTrue(any("interface.capabilities" in error for error in report.errors))

    def test_undeclared_agent_fails_inventory(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        (repo / "agents" / "extra.toml").write_text(
            'name = "extra"\ndescription = "Extra role"\ndeveloper_instructions = "Inspect only."\n',
            encoding="utf-8",
        )
        report = VALIDATE.validate_repo(repo)
        self.assertTrue(any("agent inventory mismatch" in error for error in report.errors))

    def test_bad_skill_frontmatter_fails(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        skill = repo / "skills" / "pitcrew-plan-delivery" / "SKILL.md"
        text = skill.read_text(encoding="utf-8").replace("name: pitcrew-plan-delivery", "name: [pitcrew-plan-delivery]")
        skill.write_text(text, encoding="utf-8")
        report = VALIDATE.validate_repo(repo)
        self.assertTrue(any("must equal directory" in error for error in report.errors))

    def test_broken_local_link_fails(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        readme = repo / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\n[missing](docs/nope.md)\n", encoding="utf-8")
        report = VALIDATE.validate_repo(repo)
        self.assertTrue(any("broken local link" in error for error in report.errors))

    def test_missing_upstream_licence_notice_fails(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        notices = repo / "THIRD_PARTY_NOTICES.md"
        notices.write_text(
            notices.read_text(encoding="utf-8").replace(
                "Copyright (c) 2025 AgentLand Contributors",
                "upstream copyright omitted",
            ),
            encoding="utf-8",
        )

        report = VALIDATE.validate_repo(repo)

        self.assertTrue(any("required legal notice is missing" in error for error in report.errors))

    def test_symlink_in_skill_fails(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        link = repo / "skills" / "pitcrew-plan-delivery" / "references" / "linked.md"
        try:
            link.symlink_to(repo / "README.md")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable")
        report = VALIDATE.validate_repo(repo)
        self.assertTrue(any("symlink" in error.lower() for error in report.errors))

    def test_ignored_pycache_symlink_still_fails_without_writing(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        outside = Path(temporary.name) / "outside-cache"
        outside.mkdir()
        cache = repo / "scripts" / "__pycache__"
        try:
            cache.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable")
        report = VALIDATE.validate_repo(repo)
        self.assertTrue(any("__pycache__" in error and "symlink" in error for error in report.errors))
        self.assertEqual([], list(outside.iterdir()))

    def test_prompt_hygiene_warning_only_fails_strict(self) -> None:
        temporary, repo = self.copy_repo()
        self.addCleanup(temporary.cleanup)
        agent = repo / "agents" / "pitcrew_ui_critic.toml"
        agent.write_text(
            agent.read_text(encoding="utf-8").replace(
                "Permit a clean result.", "Must find at least 3 findings. Permit a clean result."
            ),
            encoding="utf-8",
        )
        relaxed = VALIDATE.validate_repo(repo, strict=False)
        strict = VALIDATE.validate_repo(repo, strict=True)
        self.assertTrue(relaxed.warnings)
        self.assertFalse(relaxed.errors)
        self.assertTrue(any(error.startswith("strict:") for error in strict.errors))


if __name__ == "__main__":
    unittest.main()
