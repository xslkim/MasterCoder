from __future__ import annotations

import os
from dataclasses import dataclass, field

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool

from .config import Settings
from .crew_agents import _llm
from .gates import run_quality_gates
from .models import ReqRecord
from . import repo_ops


@dataclass
class DevContext:
    settings: Settings
    req: ReqRecord
    branch: str
    last_pr_number: int | None = field(default=None, init=False)


def build_dev_tools(ctx: DevContext) -> list:
    root = ctx.settings.repo_root

    @tool("Read a text file from the repository")
    def repo_read_file(relative_path: str) -> str:
        """Read UTF-8 file. Use forward slashes; no parent segments."""
        try:
            return repo_ops.repo_read_text(root, relative_path)
        except Exception as e:
            return f"FAIL: {e}"

    @tool("Write or overwrite a text file in the repository")
    def repo_write_file(relative_path: str, content: str) -> str:
        """Write UTF-8 file, creating parent directories. No .. in path."""
        try:
            return repo_ops.repo_write_text(root, relative_path, content)
        except Exception as e:
            return f"FAIL: {e}"

    @tool("Fetch origin and fast-forward the default branch")
    def git_update_main() -> str:
        """git fetch; checkout main or master; pull --ff-only."""
        try:
            return repo_ops.git_checkout_main_pull(root)
        except Exception as e:
            return f"FAIL: {e}"

    @tool("Create and checkout the feature branch")
    def git_use_feature_branch(branch_name: str) -> str:
        """Create branch from current HEAD or checkout if it exists."""
        try:
            return repo_ops.git_create_branch(root, branch_name.strip())
        except Exception as e:
            return f"FAIL: {e}"

    @tool("Show git status in short form")
    def git_status() -> str:
        try:
            return repo_ops.git_status_short(root)
        except Exception as e:
            return f"FAIL: {e}"

    @tool("Stage all changes")
    def git_stage_all() -> str:
        try:
            return repo_ops.git_add_all(root)
        except Exception as e:
            return f"FAIL: {e}"

    @tool("Create a commit")
    def git_commit_msg(message: str) -> str:
        """Commit staged changes with the given message."""
        try:
            return repo_ops.git_commit(root, message.strip())
        except Exception as e:
            return f"FAIL: {e}"

    @tool("Run local quality gates (ruff + pytest + coverage)")
    def run_local_quality_gates() -> str:
        """Returns PASS: ... or FAIL: ... with command output."""
        gate = run_quality_gates(ctx.settings.coverage_min, cwd=root)
        prefix = "PASS" if gate.passed else "FAIL"
        return f"{prefix}\n{gate.output}"

    @tool("Push the current branch to GitHub")
    def git_push_branch() -> str:
        """Uses GIT_AGENT_TOKEN_DEV. Push only after run_local_quality_gates returned PASS."""
        token = (os.environ.get("GIT_AGENT_TOKEN_DEV") or "").strip()
        if not token:
            return "FAIL: GIT_AGENT_TOKEN_DEV not set"
        try:
            return repo_ops.git_push_https(
                root,
                ctx.branch,
                token,
                ctx.settings.github_repo,
            )
        except Exception as e:
            return f"FAIL: {e}"

    @tool("Open a pull request on GitHub")
    def github_open_pull_request(pr_title: str, pr_body: str) -> str:
        """Create PR for the current pushed branch. Uses GIT_AGENT_TOKEN_DEV."""
        token = (os.environ.get("GIT_AGENT_TOKEN_DEV") or "").strip()
        if not token:
            return "FAIL: GIT_AGENT_TOKEN_DEV not set"
        try:
            num = repo_ops.gh_pr_create_json(
                ctx.settings.github_repo,
                ctx.branch,
                pr_title.strip(),
                pr_body.strip(),
                token,
            )
            ctx.last_pr_number = num
            return f"OK PR #{num}"
        except Exception as e:
            return f"FAIL: {e}"

    return [
        repo_read_file,
        repo_write_file,
        git_update_main,
        git_use_feature_branch,
        git_status,
        git_stage_all,
        git_commit_msg,
        run_local_quality_gates,
        git_push_branch,
        github_open_pull_request,
    ]


def run_dev_implementation_crew(req: ReqRecord, settings: Settings) -> tuple[str, int | None]:
    branch = req.branch or repo_ops.branch_slug(req)
    ctx = DevContext(settings=settings, req=req, branch=branch)
    tools = build_dev_tools(ctx)

    rid = req.req_id
    agent = Agent(
        role="Development Agent",
        goal="Implement the requirement with real file edits and Git operations.",
        backstory=(
            "You work in the local clone, use tools only, never paste API keys or tokens. "
            "Follow the task steps in order."
        ),
        llm=_llm(settings),
        tools=tools,
        verbose=False,
        allow_delegation=False,
    )
    task = Task(
        description=(
            f"Requirement: {rid} — {req.title}\n\n"
            f"Repository root: {settings.repo_root}\n"
            f"Use branch name exactly: {branch}\n\n"
            "1) git_update_main\n"
            f"2) git_use_feature_branch with branch_name={branch!r}\n"
            "3) Implement: read docs/requirements.md (repo_read_file) for this REQ if needed; "
            "edit code under src/ and tests/ with repo_write_file as appropriate.\n"
            "4) git_status, then git_stage_all, then git_commit_msg with message like "
            f"feat({rid.lower()}): short description\n"
            "5) run_local_quality_gates — if it starts with FAIL, fix issues and repeat from step 3.\n"
            "6) When PASS: git_push_branch, then github_open_pull_request with a clear title and body "
            f'referencing {rid}.\n'
            "Final answer: one short summary of what you changed and the PR result line (OK PR #… or FAIL)."
        ),
        expected_output="Short summary and PR status.",
        agent=agent,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        tracing=False,
    )
    out = str(crew.kickoff())
    return out, ctx.last_pr_number
