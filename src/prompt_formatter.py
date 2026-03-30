"""
REQ-17: 提示符格式化器

实现增强版输入提示符，显示模型名、工作目录和 Git 分支信息。
"""

import os
from typing import Optional


class PromptFormatter:
    """
    提示符格式化器

    格式：mastercoder [<模型名>] <工作目录短路径> (<git分支>) >
    """

    def __init__(
        self,
        model_name: str,
        working_dir: str,
        git_branch: Optional[str] = None,
        home_dir: Optional[str] = None,
    ):
        """
        初始化提示符格式化器

        Args:
            model_name: 模型名称（如 gpt-4o）
            working_dir: 当前工作目录
            git_branch: Git 分支名（可选，不在 Git 仓库时为 None）
            home_dir: 用户 home 目录（可选，用于路径缩写）
        """
        self.model_name = model_name
        self.working_dir = working_dir
        self.git_branch = git_branch
        self.home_dir = home_dir or os.path.expanduser("~")

    def _abbreviate_path(self, path: str) -> str:
        """
        缩写路径，将 home 目录替换为 ~

        Args:
            path: 原始路径

        Returns:
            缩写后的路径
        """
        home_path = self.home_dir
        if path.startswith(home_path):
            return "~" + path[len(home_path) :]
        return path

    def format(self) -> str:
        """
        格式化提示符

        Returns:
            格式化后的提示符字符串
        """
        # 缩写工作目录
        short_path = self._abbreviate_path(self.working_dir)

        # 基础格式
        prompt = f"mastercoder [{self.model_name}] {short_path}"

        # 如果有 Git 分支，添加分支信息
        if self.git_branch:
            prompt += f" ({self.git_branch})"

        prompt += " > "

        return prompt
