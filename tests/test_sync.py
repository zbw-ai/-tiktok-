"""Exercise synchronization against real temporary Git repositories."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT / "scripts" / "sync.py"


class SyncIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tiktok-sync-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "work"
        self.remote = self.base / "remote.git"
        self.repo.mkdir()
        self.env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        self.env.pop("TIKTOK_SYNC_SKIP_PUSH", None)
        self.git("init", "--bare", str(self.remote), cwd=self.base)
        self.git("init", cwd=self.repo)
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.git("config", "user.name", "Sync Test")
        self.git("config", "user.email", "sync@example.invalid")
        self.git("config", "core.hooksPath", ".empty-hooks")
        self.git("remote", "add", "origin", str(self.remote))

    def run_process(self, args, cwd=None, check=True):
        return subprocess.run(
            args, cwd=cwd or self.repo, env=self.env,
            text=True, capture_output=True, check=check,
        )

    def git(self, *args, cwd=None, check=True):
        return self.run_process(["git", *args], cwd=cwd, check=check)

    def sync(self, *args):
        return self.run_process([sys.executable, str(SCRIPT), *args], check=False)

    def write(self, name, value):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def remote_head(self):
        return self.git("rev-parse", "refs/heads/main", cwd=self.remote).stdout.strip()

    def first_sync(self):
        self.write("README.md", "A real project\n")
        result = self.sync("docs: initial content")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return self.git("rev-parse", "HEAD").stdout.strip()

    def test_first_sync_commits_changes_and_respects_gitignore(self):
        self.write(".gitignore", ".env\n")
        self.write(".env", "LOCAL_TEST_ONLY=private\n")
        local_head = self.first_sync()
        self.assertEqual(local_head, self.remote_head())
        tracked = self.git("ls-tree", "--name-only", "HEAD", cwd=self.remote).stdout
        self.assertNotIn(".env", tracked.splitlines())
        self.assertEqual(self.git("status", "--porcelain").stdout, "")
        again = self.sync("docs: no changes")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(local_head, self.remote_head())

    def test_hook_pushes_an_ordinary_commit(self):
        self.first_sync()
        source_hook = PROJECT / ".githooks" / "post-commit"
        self.assertTrue(source_hook.exists(), "Post-commit synchronization hook is missing")
        (self.repo / ".githooks").mkdir()
        (self.repo / "scripts").mkdir()
        shutil.copy2(source_hook, self.repo / ".githooks" / "post-commit")
        shutil.copy2(SCRIPT, self.repo / "scripts" / "sync.py")
        (self.repo / ".githooks" / "post-commit").chmod(0o755)
        self.git("config", "core.hooksPath", ".githooks")
        self.git("add", "--all")
        self.git("commit", "-m", "chore: enable hook")
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.remote_head())

    def test_remote_changes_are_not_overwritten(self):
        self.first_sync()
        other = self.base / "other"
        self.git("clone", "--branch", "main", str(self.remote), str(other), cwd=self.base)
        self.git("config", "user.name", "Other Editor", cwd=other)
        self.git("config", "user.email", "other@example.invalid", cwd=other)
        self.git("config", "core.hooksPath", ".empty-hooks", cwd=other)
        (other / "remote-note.md").write_text("Remote work\n")
        self.git("add", "--all", cwd=other)
        self.git("commit", "-m", "docs: remote work", cwd=other)
        self.git("push", "origin", "main", cwd=other)
        remote_head = self.remote_head()
        self.write("local-note.md", "Local work\n")
        result = self.sync("docs: local work")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("remote has commits", result.stderr.lower())
        self.assertEqual(remote_head, self.remote_head())
        self.assertEqual(self.git("show", "HEAD:local-note.md").stdout, "Local work\n")

    def test_failed_connection_keeps_the_local_commit(self):
        old_head = self.first_sync()
        self.git("remote", "set-url", "origin", str(self.base / "unavailable.git"))
        self.write("retained.md", "Keep this work\n")
        result = self.sync("docs: retained offline")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(old_head, self.git("rev-parse", "HEAD").stdout.strip())
        self.assertEqual(self.git("show", "HEAD:retained.md").stdout, "Keep this work\n")

    def test_detached_head_does_not_stage_or_commit_work(self):
        old_head = self.first_sync()
        self.git("checkout", "--detach", old_head)
        self.write("pending.md", "Still uncommitted\n")
        result = self.sync("docs: should not commit")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("detached", result.stderr.lower())
        self.assertEqual(old_head, self.git("rev-parse", "HEAD").stdout.strip())
        self.assertEqual(self.git("diff", "--cached", "--name-only").stdout, "")

    def test_stash_conflict_is_preserved_without_staging_or_pushing(self):
        self.first_sync()
        asset = self.repo / "asset.bin"
        asset.write_bytes(b"\x00base")
        self.assertEqual(self.sync("test: base asset").returncode, 0)
        asset.write_bytes(b"\x00stashed change")
        self.git("stash", "push")
        asset.write_bytes(b"\x00current change")
        self.assertEqual(self.sync("test: current asset").returncode, 0)
        popped = self.git("stash", "pop", check=False)
        self.assertNotEqual(popped.returncode, 0)
        self.assertFalse((self.repo / ".git" / "MERGE_HEAD").exists())
        conflicts = self.git("ls-files", "--unmerged").stdout
        self.assertTrue(conflicts)
        before_head = self.git("rev-parse", "HEAD").stdout.strip()
        before_bytes = asset.read_bytes()
        result = self.sync("test: must preserve conflict")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unresolved", result.stderr.lower())
        self.assertEqual(self.git("ls-files", "--unmerged").stdout, conflicts)
        self.assertEqual(asset.read_bytes(), before_bytes)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), before_head)
        self.assertEqual(self.remote_head(), before_head)


if __name__ == "__main__":
    unittest.main()
