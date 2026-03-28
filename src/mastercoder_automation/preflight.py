"""流水线运行前检查本机必备命令（避免推到一半才因缺 gh 失败）。"""

from __future__ import annotations

from shutil import which


def check_automation_prerequisites() -> None:
    """创建 PR、Review、Merge 依赖 git 与 GitHub CLI。"""
    missing: list[str] = []
    if which("git") is None:
        missing.append("git")
    if which("gh") is None:
        missing.append("gh（GitHub CLI，见 https://cli.github.com/ ）")
    if missing:
        joined = "、".join(missing)
        raise RuntimeError(
            f"未在 PATH 中找到：{joined}。"
            "请安装并确保终端能直接执行上述命令。"
            "Debian/Ubuntu 示例：sudo apt install git gh"
        )
