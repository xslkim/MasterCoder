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

    @tool("repo_read_requirement")
    def repo_read_requirement(req_id: str) -> str:
        """按 REQ-ID 读取 docs/requirements.md 中对应需求章节。"""
        try:
            return repo_ops.repo_read_requirement_section(root, req_id.strip())
        except Exception as e:
            return f"失败：{e}"

    @tool("repo_write_file")
    def repo_write_file(relative_path: str, content: str) -> str:
        """写入或覆盖仓库文件（UTF-8），自动创建父目录。路径禁止含 ..。"""
        try:
            return repo_ops.repo_write_text(root, relative_path, content)
        except Exception as e:
            return f"失败：{e}"

    @tool("git_status")
    def git_status() -> str:
        """查看简短 git 状态（git status --short）。"""
        try:
            return repo_ops.git_status_short(root)
        except Exception as e:
            return f"失败：{e}"

    @tool("git_changed_files_against_default")
    def git_changed_files_against_default() -> str:
        """查看当前分支相对默认分支（main/master）的变更文件列表。"""
        try:
            files = repo_ops.git_changed_files_against_default(root, ctx.branch)
            return "\n".join(files) if files else "(no changes)"
        except Exception as e:
            return f"失败：{e}"

    @tool("git_commits_ahead_of_default")
    def git_commits_ahead_of_default() -> str:
        """查看当前分支相对默认分支领先的提交数。"""
        try:
            count = repo_ops.git_commits_ahead_of_default(root, ctx.branch)
            return str(count)
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
        repo_read_requirement,
        repo_write_file,
        git_status,
        git_changed_files_against_default,
        git_commits_ahead_of_default,
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
            "你在本地克隆目录中工作，只使用工具，绝不粘贴 API 密钥或 token。按任务步骤顺序执行。"
            "每个 REQ 都必须先根据 docs/requirements.md 为当前需求编写或更新测试，再实现代码。"
            "当没有合适的已有测试时，可以新建聚焦当前需求的 tests/test_*.py。"
            "测试必须来自需求文档里的功能规格、交付物、Review 检查项或验收标准，避免空泛或重复测试。"
            "不要臆造不存在的模块、类名或 API（例如错误的 import）。"
            "禁止修改 mastercoder_automation/gates.py、orchestrator、cli 等流水线核心文件，除非需求文档明确要求。"
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
            "你启动时已经位于正确的功能分支上，无需自行切换分支。\n"
            f"1) 先用 repo_read_requirement，req_id={rid!r}，直接读取 {rid} 的需求章节；只有在需要更多上下文时才用 repo_read_file 阅读整个文档。\n"
            "2) 先在 tests/ 下编写或更新当前 REQ 的测试用例，确保测试断言直接对应需求文档。"
            "没有合适的现有测试时，可以新建一个聚焦当前需求的 tests/test_*.py。\n"
            "3) 再修改 src/ 下实现代码，让第 2 步测试通过；避免改动与当前需求无关的文件。\n"
            "4) git_status，然后 git_changed_files_against_default；确认输出中包含 tests/ 下的测试文件。\n"
            "5) git_stage_all，再 git_commit_msg，说明类似 "
            f"feat({rid.lower()}): 简短描述\n"
            "6) run_local_quality_gates — 若以「失败」开头，修复问题后从第 2 步或第 3 步继续。\n"
            "7) git_commits_ahead_of_default；结果必须大于 0，否则说明还没有形成可推送提交。\n"
            "8) 只有当 tests/ 已改动、质量门禁通过、且领先提交数大于 0 时，才允许 git_push_branch，"
            "再 github_open_pull_request，标题与正文清晰并引用 "
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
