from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from .repo_ops import _pr_number_from_gh_create_stdout


def _run(cmd: list[str], gh_token: str | None = None) -> str:
    env = os.environ.copy()
    if gh_token:
        env["GH_TOKEN"] = gh_token
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"命令失败：{' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout.strip()


@dataclass
class GhClient:
    repo: str

    def create_pr(
        self,
        branch: str,
        title: str,
        body: str,
        *,
        gh_token: str | None = None,
    ) -> int:
        env = os.environ.copy()
        if gh_token:
            env["GH_TOKEN"] = gh_token
        proc = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                self.repo,
                "--head",
                branch,
                "--title",
                title,
                "--body",
                body,
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"命令失败：gh pr create\n{(proc.stderr or proc.stdout or '').strip()}"
            )
        blob = f"{proc.stdout or ''}\n{proc.stderr or ''}".strip()
        return _pr_number_from_gh_create_stdout(blob)

    def approve_pr(
        self,
        pr_number: int,
        body: str,
        *,
        gh_token: str | None = None,
    ) -> None:
        _run(
            [
                "gh",
                "pr",
                "review",
                str(pr_number),
                "--repo",
                self.repo,
                "--approve",
                "--body",
                body,
            ],
            gh_token=gh_token,
        )

    def request_changes(
        self,
        pr_number: int,
        body: str,
        *,
        gh_token: str | None = None,
    ) -> None:
        _run(
            [
                "gh",
                "pr",
                "review",
                str(pr_number),
                "--repo",
                self.repo,
                "--request-changes",
                "--body",
                body,
            ],
            gh_token=gh_token,
        )

    def comment_pr(
        self,
        pr_number: int,
        body: str,
        *,
        gh_token: str | None = None,
    ) -> None:
        _run(
            [
                "gh",
                "pr",
                "comment",
                str(pr_number),
                "--repo",
                self.repo,
                "--body",
                body,
            ],
            gh_token=gh_token,
        )

    def merge_pr(
        self,
        pr_number: int,
        *,
        gh_token: str | None = None,
    ) -> None:
        _run(
            [
                "gh",
                "pr",
                "merge",
                str(pr_number),
                "--repo",
                self.repo,
                "--squash",
                "--delete-branch",
                "--auto",
            ],
            gh_token=gh_token,
        )
