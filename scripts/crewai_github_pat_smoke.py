#!/usr/bin/env python3
"""CrewAI smoke test: three agents each validate a GitHub PAT (Dev / Review / QA).

Uses the same variable names as [.env.sh](.env.sh):
  - GIT_AGENT_USERNAME_DEV, GIT_AGENT_TOKEN_DEV, GIT_AGENT_EMAIL_DEV
  - GIT_AGENT_USERNAME_REVIEW, GIT_AGENT_TOKEN_REVIEW, GIT_AGENT_EMAIL_REVIEW
  - GIT_AGENT_USERNAME_TEST, GIT_AGENT_TOKEN_TEST, GIT_AGENT_EMAIL_TEST

Each agent has exactly one tool that calls GitHub as that PAT (via ``gh api user`` or HTTPS fallback).

Run:
  cd /path/to/MasterCoder
  source .env.sh
  python3 scripts/crewai_github_pat_smoke.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from shutil import which


def _api_user_login(token: str) -> tuple[bool, str]:
    if which("gh"):
        env = {**os.environ, "GH_TOKEN": token}
        proc = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            capture_output=True,
            text=True,
            env=env,
            timeout=45,
            check=False,
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        err = (proc.stderr or proc.stdout or "").strip()
        return False, err[:800]

    req = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return True, str(body.get("login", ""))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:800]
        return False, f"HTTP {e.code}: {detail}"


def _verify_pat(
    label: str,
    token_var: str,
    _username_var: str,
    _email_var: str,
) -> str:
    token = (os.environ.get(token_var) or "").strip()
    if not token:
        return f"{label}: FAIL missing {token_var}"
    ok, payload = _api_user_login(token)
    if not ok:
        return f"{label}: FAIL github_api: {payload}"
    login = payload
    return f"{label}: OK api_login={login}"


def main() -> int:
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

    from crewai import Agent, Crew, LLM, Process, Task
    from crewai.tools import tool

    @tool("Verify Dev agent GitHub credentials")
    def verify_github_dev() -> str:
        """Call GitHub /user as the Dev PAT; returns one status line (no secrets)."""
        return _verify_pat(
            "DEV",
            "GIT_AGENT_TOKEN_DEV",
            "GIT_AGENT_USERNAME_DEV",
            "GIT_AGENT_EMAIL_DEV",
        )

    @tool("Verify Review agent GitHub credentials")
    def verify_github_review() -> str:
        """Call GitHub /user as the Review PAT; returns one status line (no secrets)."""
        return _verify_pat(
            "REVIEW",
            "GIT_AGENT_TOKEN_REVIEW",
            "GIT_AGENT_USERNAME_REVIEW",
            "GIT_AGENT_EMAIL_REVIEW",
        )

    @tool("Verify Test agent GitHub credentials")
    def verify_github_test() -> str:
        """Call GitHub /user as the Test PAT; returns one status line (no secrets)."""
        return _verify_pat(
            "TEST",
            "GIT_AGENT_TOKEN_TEST",
            "GIT_AGENT_USERNAME_TEST",
            "GIT_AGENT_EMAIL_TEST",
        )

    model = (os.environ.get("MODEL_NAME") or "").strip()
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    base_url = (os.environ.get("OPENAI_API_BASE_URL") or "").strip().rstrip("/")
    if not (model and api_key and base_url):
        print(
            "error: need OPENAI_API_KEY, OPENAI_API_BASE_URL, MODEL_NAME "
            "(same as Crew LLM smoke test)",
            file=sys.stderr,
        )
        return 1

    llm = LLM(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0,
        max_tokens=512,
    )

    dev_agent = Agent(
        role="DevGitAgent",
        goal="Call verify_github_dev once and return only its tool output.",
        backstory="You validate the Dev PAT. You never print secrets.",
        llm=llm,
        tools=[verify_github_dev],
        verbose=False,
        allow_delegation=False,
    )
    review_agent = Agent(
        role="ReviewGitAgent",
        goal="Call verify_github_review once and return only its tool output.",
        backstory="You validate the Review PAT. You never print secrets.",
        llm=llm,
        tools=[verify_github_review],
        verbose=False,
        allow_delegation=False,
    )
    test_agent = Agent(
        role="TestGitAgent",
        goal="Call verify_github_test once and return only its tool output.",
        backstory="You validate the Test PAT. You never print secrets.",
        llm=llm,
        tools=[verify_github_test],
        verbose=False,
        allow_delegation=False,
    )

    task_dev = Task(
        description=(
            "Use the verify_github_dev tool exactly once. "
            "Final answer must be the tool output string only, no extra words."
        ),
        expected_output="One line from verify_github_dev.",
        agent=dev_agent,
    )
    task_review = Task(
        description=(
            "Use the verify_github_review tool exactly once. "
            "Final answer must be the tool output string only, no extra words."
        ),
        expected_output="One line from verify_github_review.",
        agent=review_agent,
    )
    task_test = Task(
        description=(
            "Use the verify_github_test tool exactly once. "
            "Final answer must be the tool output string only, no extra words."
        ),
        expected_output="One line from verify_github_test.",
        agent=test_agent,
    )

    crew = Crew(
        agents=[dev_agent, review_agent, test_agent],
        tasks=[task_dev, task_review, task_test],
        process=Process.sequential,
        verbose=False,
        tracing=False,
    )
    result = crew.kickoff()
    print("\n--- crew.kickoff() ---\n", result)

    print("\n--- direct PAT checks (exit code based on these) ---")
    lines = [
        _verify_pat(
            "DEV",
            "GIT_AGENT_TOKEN_DEV",
            "GIT_AGENT_USERNAME_DEV",
            "GIT_AGENT_EMAIL_DEV",
        ),
        _verify_pat(
            "REVIEW",
            "GIT_AGENT_TOKEN_REVIEW",
            "GIT_AGENT_USERNAME_REVIEW",
            "GIT_AGENT_EMAIL_REVIEW",
        ),
        _verify_pat(
            "TEST",
            "GIT_AGENT_TOKEN_TEST",
            "GIT_AGENT_USERNAME_TEST",
            "GIT_AGENT_EMAIL_TEST",
        ),
    ]
    for line in lines:
        print(line)
    if any(
        line.startswith(f"{lbl}: FAIL")
        for line, lbl in zip(lines, ("DEV", "REVIEW", "TEST"), strict=True)
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
