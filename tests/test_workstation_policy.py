import tempfile
import unittest
from pathlib import Path

from workstation_agent.policy import (
    PolicyError,
    read_project_file,
    resolve_workspace_path,
    run_approved_check,
    write_project_file,
)


class WorkspacePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_write_and_read_inside_workspace(self):
        write_project_file(self.root, "src/example.txt", "olá")
        self.assertEqual(read_project_file(self.root, "src/example.txt"), "olá")

    def test_blocks_parent_traversal(self):
        with self.assertRaises(PolicyError):
            resolve_workspace_path(self.root, "../outside.txt")

    def test_blocks_absolute_path(self):
        with self.assertRaises(PolicyError):
            resolve_workspace_path(self.root, str(self.root / "file.txt"))

    def test_blocks_env_and_private_key_files(self):
        for name in (".env", ".env.local", "private.pem", "id.key"):
            with self.subTest(name=name), self.assertRaises(PolicyError):
                resolve_workspace_path(self.root, name)

    def test_blocks_git_and_credentials_directories(self):
        for name in (".git/config", "credentials/token.txt"):
            with self.subTest(name=name), self.assertRaises(PolicyError):
                resolve_workspace_path(self.root, name)

    def test_rejects_unknown_commands(self):
        with self.assertRaises(PolicyError):
            run_approved_check(self.root, "powershell-arbitrary")


if __name__ == "__main__":
    unittest.main()
