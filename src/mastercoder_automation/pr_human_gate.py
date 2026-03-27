from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Literal

ReviewPollResult = Literal["APPROVED", "CHANGES_REQUESTED", "PENDING", "TIMEOUT"]
QaPollResult = Literal["QA_PASSED", "QA_FAILED", "PENDING", "TIMEOUT"]


def _env_with_token(token: str) -> dict[str, str]:
    return {**os.environ, "GH_TOKEN": token}


def _run_json(cmd: list[str], token: str) -> object:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=_env_with_token(token),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh failed: {' '.join(cmd)}\n{(proc.stderr or proc.stdout).strip()}")
    return json.loads(proc.stdout)


def latest_review_state_for_login(
    github_repo: str,
    pr_number: int,
    reviewer_login: str,
    token: str,
) -> str | None:
    """Return APPROVED, CHANGES_REQUESTED, COMMENTED, or None if no review from that login."""
    payload = _run_json(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--repo",
            github_repo,
            "--json",
            "reviews",
        ],
        token,
    )
    reviews = payload.get("reviews") or []
    login_l = reviewer_login.lower()
    latest: dict | None = None
    latest_submitted: str | None = None
    for rev in reviews:
        author = (rev.get("author") or {}).get("login") or ""
        if author.lower() != login_l:
            continue
        submitted = rev.get("submittedAt") or ""
        if latest is None or (submitted and submitted > (latest_submitted or "")):
            latest = rev
            latest_submitted = submitted
    if latest is None:
        return None
    return str(latest.get("state") or "").upper() or None


def poll_human_pr_review(
    github_repo: str,
    pr_number: int,
    reviewer_login: str,
    token: str,
    *,
    interval_sec: int,
    timeout_sec: int,
) -> ReviewPollResult:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            state = latest_review_state_for_login(github_repo, pr_number, reviewer_login, token)
        except RuntimeError:
            state = None
        if state == "APPROVED":
            return "APPROVED"
        if state == "CHANGES_REQUESTED":
            return "CHANGES_REQUESTED"
        time.sleep(max(5, interval_sec))
    return "TIMEOUT"


def latest_qa_comment_from_login(
    github_repo: str,
    pr_number: int,
    test_login: str,
    token: str,
) -> QaPollResult | Literal["PENDING"]:
    owner, _, name = github_repo.partition("/")
    if not owner or not name:
        raise ValueError("github_repo must be owner/repo")
    data = _run_json(
        [
            "gh",
            "api",
            f"repos/{owner}/{name}/issues/{pr_number}/comments?per_page=100",
        ],
        token,
    )
    if isinstance(data, list):
        comments = data
    else:
        comments = [data]
    login_l = test_login.lower()
    for c in reversed(comments):
        user = (c.get("user") or {}).get("login") or ""
        if user.lower() != login_l:
            continue
        body = (c.get("body") or "").strip()
        if body.startswith("QA_PASSED"):
            return "QA_PASSED"
        if body.startswith("QA_FAILED"):
            return "QA_FAILED"
    return "PENDING"


def poll_human_pr_qa(
    github_repo: str,
    pr_number: int,
    test_login: str,
    token: str,
    *,
    interval_sec: int,
    timeout_sec: int,
) -> QaPollResult:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            verdict = latest_qa_comment_from_login(
                github_repo, pr_number, test_login, token
            )
        except RuntimeError:
            verdict = "PENDING"
        if verdict in ("QA_PASSED", "QA_FAILED"):
            return verdict
        time.sleep(max(5, interval_sec))
    return "TIMEOUT"
