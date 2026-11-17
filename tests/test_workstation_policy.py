import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workstation_agent.policy import (
    PolicyError,
    read_project_file,
    resolve_workspace_path,
    run_approved_check,
    write_project_file,
)
from workstation_agent.autonomy import classify_action, max_repair_attempts, repair_may_run


class WorkspacePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_write_and_read_inside_explicitly_authorized_folder(self):
        with patch.dict(os.environ, {"JARVIS_AUTO_EDIT_PATHS": "src"}):
            write_project_file(self.root, "src/example.txt", "olá")
            self.assertEqual(read_project_file(self.root, "src/example.txt"), "olá")

    def test_write_is_blocked_by_default(self):
        with patch.dict(os.environ, {"JARVIS_AUTO_EDIT_PATHS": ""}):
            with self.assertRaises(PolicyError):
                write_project_file(self.root, "src/example.txt", "não autorizado")

    def test_write_is_blocked_outside_authorized_folder(self):
        with patch.dict(os.environ, {"JARVIS_AUTO_EDIT_PATHS": "src"}):
            with self.assertRaises(PolicyError):
                write_project_file(self.root, "tests/example.txt", "não autorizado")

    def test_blocks_parent_traversal(self):
        with self.assertRaises(PolicyError):
            resolve_workspace_path(self.root, "../outside.txt")

    def test_blocks_absolute_path(self):
        with self.assertRaises(PolicyError):
            resolve_workspace_path(self.root, str(self.root / "file.txt"))

    def test_blocks_env_and_private_key_files(self):
        for name in (".env", ".env.local", "private.pem", "id.key", ".jarvis-backups/backup.txt"):
            with self.subTest(name=name), self.assertRaises(PolicyError):
                resolve_workspace_path(self.root, name)

    def test_blocks_git_and_credentials_directories(self):
        for name in (".git/config", "credentials/token.txt"):
            with self.subTest(name=name), self.assertRaises(PolicyError):
                resolve_workspace_path(self.root, name)

    def test_blocks_symlink_that_points_outside_workspace(self):
        outside = Path(self.temp.name).parent / (Path(self.temp.name).name + "-outside")
        outside.mkdir(exist_ok=True)
        try:
            link = self.root / "outside-link"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Criação de symlink não disponível neste executor.")
            with self.assertRaises(PolicyError):
                resolve_workspace_path(self.root, "outside-link/secret.txt")
        finally:
            try:
                outside.rmdir()
            except OSError:
                pass

    def test_rejects_unknown_commands(self):
        with self.assertRaises(PolicyError):
            run_approved_check(self.root, "powershell-arbitrary")


class AutonomyPolicyTests(unittest.TestCase):
    def test_read_only_actions_are_automatic(self):
        self.assertEqual(classify_action("run_check"), "auto")

    def test_write_requires_local_restriction(self):
        self.assertEqual(classify_action("write_file"), "restricted")

    def test_production_and_secret_actions_need_approval(self):
        self.assertEqual(classify_action("deploy"), "approval_required")
        self.assertEqual(classify_action("manage_secrets"), "approval_required")

    def test_repair_disabled_by_default(self):
        with patch.dict(os.environ, {"JARVIS_AUTO_REPAIR_ENABLED": "false"}):
            self.assertFalse(repair_may_run(0))

    def test_repair_attempts_are_capped(self):
        with patch.dict(os.environ, {"JARVIS_AUTO_REPAIR_ENABLED": "true", "JARVIS_AUTO_REPAIR_MAX_ATTEMPTS": "99"}):
            self.assertEqual(max_repair_attempts(), 3)
            self.assertTrue(repair_may_run(2))
            self.assertFalse(repair_may_run(3))


if __name__ == "__main__":
    unittest.main()
