"""
REQ-17: 终端界面 — 状态栏与 Token 统计

测试提示符格式、Git 分支检测、Spinner 动画和 Token 统计功能。
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import subprocess

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prompt_formatter import PromptFormatter
from git_detector import GitDetector
from token_stats import TokenStats
from spinner import Spinner


class TestPromptFormatter:
    """测试提示符格式化"""

    def test_prompt_with_git_branch(self):
        """测试在 Git 仓库中的提示符格式"""
        formatter = PromptFormatter(
            model_name="gpt-4o", working_dir="/home/user/project", git_branch="main"
        )
        prompt = formatter.format()
        assert "mastercoder" in prompt
        assert "gpt-4o" in prompt
        assert "main" in prompt
        assert ">" in prompt

    def test_prompt_without_git_branch(self):
        """测试不在 Git 仓库中的提示符格式"""
        formatter = PromptFormatter(
            model_name="gpt-4o", working_dir="/home/user/project", git_branch=None
        )
        prompt = formatter.format()
        assert "mastercoder" in prompt
        assert "gpt-4o" in prompt
        assert "(" not in prompt  # 不应包含分支括号
        assert ">" in prompt

    def test_home_directory_abbreviation(self):
        """测试 home 目录缩写为 ~"""
        formatter = PromptFormatter(
            model_name="gpt-4o",
            working_dir="/home/user/project",
            home_dir="/home/user",
            git_branch="main",
        )
        prompt = formatter.format()
        assert "~" in prompt
        assert "/home/user" not in prompt


class TestGitDetector:
    """测试 Git 分支检测"""

    def test_detect_branch_in_git_repo(self):
        """测试在 Git 仓库中检测分支"""
        detector = GitDetector()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="feature-branch\n", stderr="")
            branch = detector.get_current_branch("/some/git/repo")
            assert branch == "feature-branch"

    def test_detect_branch_not_in_git_repo(self):
        """测试不在 Git 仓库中时返回 None"""
        detector = GitDetector()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=128, stdout="", stderr="fatal: not a git repository"
            )
            branch = detector.get_current_branch("/tmp/not-git")
            assert branch is None

    def test_git_command_silent_failure(self):
        """测试 Git 命令失败时静默处理（不抛异常）"""
        detector = GitDetector()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                128, "git", stderr="fatal: not a git repository"
            )
            # 不应抛出异常
            branch = detector.get_current_branch("/tmp/not-git")
            assert branch is None


class TestTokenStats:
    """测试 Token 统计"""

    def test_token_stats_initial_state(self):
        """测试初始状态"""
        stats = TokenStats()
        assert stats.get_session_prompt_tokens() == 0
        assert stats.get_session_completion_tokens() == 0

    def test_token_stats_single_round(self):
        """测试单轮对话的 token 统计"""
        stats = TokenStats()
        stats.add_usage(prompt_tokens=100, completion_tokens=50)

        assert stats.get_round_prompt_tokens() == 100
        assert stats.get_round_completion_tokens() == 50
        assert stats.get_session_prompt_tokens() == 100
        assert stats.get_session_completion_tokens() == 50

    def test_token_stats_multiple_rounds(self):
        """测试多轮对话的累计 token 统计"""
        stats = TokenStats()

        # 第一轮
        stats.add_usage(prompt_tokens=100, completion_tokens=50)
        stats.next_round()

        # 第二轮
        stats.add_usage(prompt_tokens=150, completion_tokens=75)

        # 本轮统计
        assert stats.get_round_prompt_tokens() == 150
        assert stats.get_round_completion_tokens() == 75

        # 累计统计
        assert stats.get_session_prompt_tokens() == 250
        assert stats.get_session_completion_tokens() == 125

    def test_token_stats_format(self):
        """测试 token 统计格式化输出"""
        stats = TokenStats()
        stats.add_usage(prompt_tokens=1234, completion_tokens=567)

        formatted = stats.format_stats()
        assert "↑1234" in formatted
        assert "↓567" in formatted
        assert "total" in formatted

    def test_token_stats_overflow_safety(self):
        """测试 token 统计溢出安全（使用 64 位整数）"""
        stats = TokenStats()
        # 添加大数值
        stats.add_usage(prompt_tokens=2**31, completion_tokens=2**31)

        # 应该正确存储和累加
        assert stats.get_session_prompt_tokens() == 2**31
        assert stats.get_session_completion_tokens() == 2**31

    def test_token_stats_estimated_when_no_usage(self):
        """测试无 usage 数据时显示 estimated"""
        stats = TokenStats()
        # 不调用 add_usage

        formatted = stats.format_stats(estimated=True)
        assert "estimated" in formatted.lower()


class TestSpinner:
    """测试 Spinner 动画"""

    def test_spinner_characters(self):
        """测试 spinner 使用 braille 字符序列"""
        spinner = Spinner()
        frames = spinner.get_frames()
        expected_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        assert frames == expected_frames

    def test_spinner_thinking_message(self):
        """测试 Thinking 消息"""
        spinner = Spinner()
        message = spinner.format_message("Thinking")
        assert "Thinking" in message
        assert any(frame in message for frame in spinner.get_frames())

    def test_spinner_running_tool_message(self):
        """测试 Running tool 消息"""
        spinner = Spinner()
        message = spinner.format_message("Running", tool_name="read_file")
        assert "Running" in message
        assert "read_file" in message

    def test_spinner_clear_format(self):
        """测试清除动画的格式（使用 \\r + 空格）"""
        spinner = Spinner()
        clear_seq = spinner.get_clear_sequence()
        assert "\r" in clear_seq


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
