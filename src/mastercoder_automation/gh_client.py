from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout.strip()


@dataclass
class GhClient:
    repo: str

    def create_pr(self, branch: str, title: str, body: str) -> int:
        out = _run(
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
                "--json",
                "number",
            ]
        )
        payload = json.loads(out)
        return int(payload["number"])

    def approve_pr(self, pr_number: int, body: str) -> None:
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
            ]
        )

    def request_changes(self, pr_number: int, body: str) -> None:
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
            ]
        )

    def comment_pr(self, pr_number: int, body: str) -> None:
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
            ]
        )

    def merge_pr(self, pr_number: int) -> None:
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
            ]
        )

