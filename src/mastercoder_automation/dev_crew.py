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

    @tool("repo_read_file")
    def repo_read_file(relative_path: str) -> str:
        """读取仓库 UTF-8 文本文件。路径用正斜杠，禁止含 ..。"""
        try:
            return repo_ops.repo_read_text(root, relative_path)
        except Exception as e:
            return f"失败：{e}"

    @tool("repo_write_file")
    def repo_write_file(relative_path: str, content: str) -> str:
        """写入或覆盖仓库文件（UTF-8），自动创建父目录。路径禁止含 ..。"""
        try:
            return repo_ops.repo_write_text(root, relative_path, content)
        except Exception as e:
            return f"失败：{e}"

    @tool("git_update_main")
    def git_update_main() -> str:
        """拉取远端并快进合并默认分支（git fetch；checkout main 或 master；pull --ff-only）。"""
        try:
            return repo_ops.git_checkout_main_pull(root)
        except Exception as e:
            return f"失败：{e}"

    @tool("git_use_feature_branch")
    def git_use_feature_branch(branch_name: str) -> str:
        """创建并切换到功能分支；若已存在则检出。"""
        try:
            return repo_ops.git_create_branch(root, branch_name.strip())
        except Exception as e:
            return f"失败：{e}"

    @tool("git_status")
    def git_status() -> str:
        """查看简短 git 状态（git status --short）。"""
        try:
            return repo_ops.git_status_short(root)
        except Exception as e:
            return f"失败：{e}"

    @tool("git_stage_all")
    def git_stage_all() -> str:
        """暂存全部变更（git add -A）。"""
        try:
            return repo_ops.git_add_all(root)
        except Exception as e:
            return f"失败：{e}"

    @tool("git_commit_msg")
    def git_commit_msg(message: str) -> str:
        """使用给定说明创建提交。"""
        try:
            return repo_ops.git_commit(root, message.strip())
        except Exception as e:
            return f"失败：{e}"

    @tool("run_local_quality_gates")
    def run_local_quality_gates() -> str:
        """运行本地质量门禁（ruff + pytest + 覆盖率）；返回以「通过」或「失败」开头。"""
        gate = run_quality_gates(ctx.settings.coverage_min, cwd=root)
        prefix = "通过" if gate.passed else "失败"
        return f"{prefix}\n{gate.output}"

    @tool("git_push_branch")
    def git_push_branch() -> str:
        """将当前分支推送到 GitHub（GIT_AGENT_TOKEN_DEV）；仅在质量门禁「通过」后调用。"""
        token = (os.environ.get("GIT_AGENT_TOKEN_DEV") or "").strip()
        if not token:
            return "失败：未设置 GIT_AGENT_TOKEN_DEV"
        try:
            return repo_ops.git_push_https(
                root,
                ctx.branch,
                token,
                ctx.settings.github_repo,
            )
        except Exception as e:
            return f"失败：{e}"

    @tool("github_open_pull_request")
    def github_open_pull_request(pr_title: str, pr_body: str) -> str:
        """在 GitHub 上为当前已推送分支创建 Pull Request（GIT_AGENT_TOKEN_DEV）。"""
        token = (os.environ.get("GIT_AGENT_TOKEN_DEV") or "").strip()
        if not token:
            return "失败：未设置 GIT_AGENT_TOKEN_DEV"
        try:
            num = repo_ops.gh_pr_create_json(
                ctx.settings.github_repo,
                ctx.branch,
                pr_title.strip(),
                pr_body.strip(),
                token,
            )
            ctx.last_pr_number = num
            return f"成功 PR #{num}"
        except Exception as e:
            return f"失败：{e}"

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
        role="开发智能体",
        goal="通过真实文件修改与 Git 操作实现需求。",
        backstory=(
            "你在本地克隆目录中工作，只使用工具，绝不粘贴 API 密钥或 token。"
            "按任务步骤顺序执行。"
        ),
        llm=_llm(settings),
        tools=tools,
        verbose=False,
        allow_delegation=False,
    )
    task = Task(
        description=(
            f"需求：{rid} — {req.title}\n\n"
            f"仓库根目录：{settings.repo_root}\n"
            f"分支名必须完全一致：{branch}\n\n"
            "1) git_update_main\n"
            f"2) git_use_feature_branch，branch_name={branch!r}\n"
            "3) 实现：如需可 repo_read_file 读取 docs/requirements.md；"
            "在 src/ 与 tests/ 下用 repo_write_file 修改代码。\n"
            "4) git_status，再 git_stage_all，再 git_commit_msg，说明类似 "
            f"feat({rid.lower()}): 简短描述\n"
            "5) run_local_quality_gates — 若以「失败」开头，修复问题后从第 3 步重复。\n"
            "6) 当「通过」时：git_push_branch，再 github_open_pull_request，标题与正文清晰并引用 "
            f"{rid}。\n"
            "最终回答：简短说明改动与 PR 结果（成功 PR #… 或 失败）。"
        ),
        expected_output="简短摘要与 PR 状态。",
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
