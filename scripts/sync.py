#!/usr/bin/env python3
"""Commit a completed update and push the current branch without rewriting history."""

import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys


def git(*args, check=True, capture=False, env=None):
    return subprocess.run(
        ["git", *args], check=check, text=True,
        capture_output=capture, env=env,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", nargs="?", help="Commit message for this completed update")
    parser.add_argument("--push-only", action="store_true", help="Push existing commits only")
    args = parser.parse_args()

    root = git("rev-parse", "--show-toplevel", capture=True).stdout.strip()
    os.chdir(root)
    branch_result = git("symbolic-ref", "--quiet", "--short", "HEAD", check=False, capture=True)
    if branch_result.returncode:
        raise RuntimeError("Detached HEAD: switch to a branch before synchronizing.")
    branch = branch_result.stdout.strip()
    for operation in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"):
        path = git("rev-parse", "--git-path", operation, capture=True).stdout.strip()
        if Path(path).exists():
            raise RuntimeError("An unfinished Git operation exists; resolve it before synchronizing.")
    if git("ls-files", "--unmerged", capture=True).stdout:
        raise RuntimeError("Unresolved index conflicts exist; resolve them before synchronizing.")
    git("remote", "get-url", "origin", capture=True)

    lock = Path(git("rev-parse", "--git-path", "tiktok-sync.lock", capture=True).stdout.strip())
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise RuntimeError("Another sync is running, or its lock needs inspection: " + str(lock)) from exc

    try:
        if not args.push_only:
            git("add", "--all", "--", ".")
            changed = git("diff", "--cached", "--quiet", check=False)
            if changed.returncode not in (0, 1):
                raise RuntimeError("Could not inspect staged changes.")
            if changed.returncode == 1:
                git("diff", "--cached", "--check")
                commit_env = dict(os.environ, TIKTOK_SYNC_SKIP_PUSH="1")
                message = args.message or "chore: sync project update " + datetime.now().isoformat(timespec="seconds")
                git("commit", "-m", message, env=commit_env)

        head = git("rev-parse", "HEAD", capture=True).stdout.strip()
        git("fetch", "--prune", "origin")
        remote_ref = "refs/remotes/origin/" + branch
        exists = git("show-ref", "--verify", "--quiet", remote_ref, check=False)
        if exists.returncode == 0:
            ancestor = git("merge-base", "--is-ancestor", remote_ref, "HEAD", check=False)
            if ancestor.returncode:
                raise RuntimeError(
                    "The remote has commits missing locally. Local work is retained; "
                    "review and integrate the remote changes before retrying. No force push was attempted."
                )
        elif exists.returncode != 1:
            raise RuntimeError("Could not inspect the remote tracking branch.")

        git("push", "--set-upstream", "origin", "HEAD:refs/heads/" + branch)
        remote = git("ls-remote", "--exit-code", "origin", "refs/heads/" + branch, capture=True).stdout.split()
        if not remote or remote[0] != head:
            raise RuntimeError("The remote tip could not be confirmed. Check status before retrying.")
        print("Synced " + branch + " to origin: " + head)
    finally:
        lock.rmdir()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print("Sync failed: " + str(exc), file=sys.stderr)
        print("Local files and any completed commits remain available.", file=sys.stderr)
        sys.exit(1)
