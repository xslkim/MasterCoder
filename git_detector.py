"""
REQ-17: Git 分支检测器

检测当前目录所在的 Git 分支。
"""

import subprocess
from typing import Optional


class GitDetector:
    """
    Git 分支检测器

    执行 git rev-parse --abbrev-ref HEAD 获取当前分支名
    """

    def get_current_branch(self, directory: str) -> Optional[str]:
        """
        获取指定目录的 Git 分支名

        Args:
            directory: 要检测的目录路径

        Returns:
            分支名（如 "main", "feature-branch"），如果不在 Git 仓库中则返回 None
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                branch = result.stdout.strip()
                return branch if branch else None

            return None

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            # 静默处理失败（不在 Git 仓库中或 Git 命令不可用）
            return None
