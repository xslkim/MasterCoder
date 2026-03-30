"""Git repository awareness helpers for REQ-25."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Git 命令超时（秒）
GIT_TIMEOUT = 2

# git status 最大行数
MAX_STATUS_LINES = 20

# git log 最大提交数
MAX_COMMITS = 5


@dataclass
class GitInfo:
    """Git 仓库信息数据类。"""

    is_git_repo: bool
    branch: str
    status_lines: list[str]
    recent_commits: list[str]

    @property
    def is_clean(self) -> bool:
        """判断仓库状态是否为 clean（无未提交修改）。"""
        return len(self.status_lines) == 0

    def to_system_message(self) -> str:
        """将 Git 信息格式化为 system 消息。

        Returns:
            格式化的 Git 信息字符串，非 Git 仓库返回空字符串
        """
        if not self.is_git_repo:
            return ""

        lines = [
            "---",
            "Git repository detected:",
            f"Branch: {self.branch}",
            "",
            "Recent commits:",
        ]

        # 添加最近提交
        for commit in self.recent_commits:
            lines.append(commit)

        lines.append("")

        # 添加状态
        if self.is_clean:
            lines.append("Status: clean")
        else:
            lines.append("Status:")
            for status_line in self.status_lines:
                lines.append(status_line)

        return "\n".join(lines)


def run_git_command(args: list[str], timeout: int = GIT_TIMEOUT) -> Optional[str]:
    """执行 Git 命令并返回输出。

    Args:
        args: Git 命令参数列表
        timeout: 超时时间（秒）

    Returns:
        命令输出（stdout），失败返回 None
    """

    try:
        result = subprocess.run(
            ["git"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def collect_git_info() -> GitInfo:
    """收集 Git 仓库信息。

    执行一次性的 Git 信息收集：
    - 检测是否为 Git 仓库
    - 获取当前分支名
    - 获取仓库状态摘要（最多 20 行）
    - 获取最近 5 条 commit 信息

    Returns:
        GitInfo 实例
    """
    # 检测是否为 Git 仓库
    is_inside = run_git_command(["rev-parse", "--is-inside-work-tree"])
    if is_inside != "true":
        return GitInfo(
            is_git_repo=False,
            branch="",
            status_lines=[],
            recent_commits=[],
        )

    # 获取当前分支名
    branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"]) or ""

    # 获取仓库状态摘要
    status_output = run_git_command(["status", "--short"])
    status_lines = []
    if status_output:
        all_lines = status_output.split("\n")
        # 限制为最多 20 行
        status_lines = all_lines[:MAX_STATUS_LINES]

    # 获取最近 5 条 commit
    log_output = run_git_command(["log", "--oneline", "-5"])
    recent_commits = []
    if log_output:
        recent_commits = log_output.split("\n")[:MAX_COMMITS]

    return GitInfo(
        is_git_repo=True,
        branch=branch,
        status_lines=status_lines,
        recent_commits=recent_commits,
    )


def get_current_branch() -> str:
    """获取当前 Git 分支名（实时刷新）。

    用于提示符中的分支显示，每次显示提示符时调用。

    Returns:
        当前分支名，失败返回空字符串
    """
    branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    return branch if branch else ""


def build_prompt(model: str = "gpt-4o", working_dir: Path | None = None) -> str:
    """Build the interactive prompt with the current directory and Git branch."""
    current_dir = working_dir or Path.cwd()
    home = Path.home()
    try:
        short_path = Path("~") / current_dir.relative_to(home)
    except ValueError:
        short_path = current_dir

    branch = get_current_branch()
    if branch:
        return f"mastercoder [{model}] {short_path} ({branch}) > "
    return f"mastercoder [{model}] {short_path} > "


# 全局 Git 信息实例（启动时收集一次）
_git_info: Optional[GitInfo] = None


def get_git_info() -> GitInfo:
    """获取全局 Git 信息实例（启动时收集一次）。

    Returns:
        GitInfo 实例
    """
    global _git_info
    if _git_info is None:
        _git_info = collect_git_info()
    return _git_info


def reset_git_info() -> None:
    """重置全局 Git 信息实例（用于测试）。"""
    global _git_info
    _git_info = None
