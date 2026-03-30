"""Git 信息收集模块测试 - REQ-25。"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from mastercoder.git_info import GitInfo, build_prompt, collect_git_info, get_current_branch


class TestCollectGitInfo:
    """测试 Git 信息收集功能。"""

    @patch("mastercoder.git_info.subprocess.run")
    def test_collect_git_info_in_git_repo(self, mock_run: MagicMock) -> None:
        """测试在 Git 仓库中正确收集信息。"""
        # Mock Git 命令返回值
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true"),  # git rev-parse --is-inside-work-tree
            MagicMock(returncode=0, stdout="main"),  # git rev-parse --abbrev-ref HEAD
            MagicMock(returncode=0, stdout="M  src/main.py\n?? new_file.txt"),  # git status --short
            MagicMock(
                returncode=0, stdout="a1b2c3d Fix login bug\ne4f5g6h Add user dashboard"
            ),  # git log --oneline -5
        ]

        git_info = collect_git_info()

        assert git_info is not None
        assert git_info.is_git_repo is True
        assert git_info.branch == "main"
        assert len(git_info.status_lines) == 2
        assert len(git_info.recent_commits) == 2

    @patch("mastercoder.git_info.subprocess.run")
    def test_collect_git_info_not_in_git_repo(self, mock_run: MagicMock) -> None:
        """测试非 Git 目录无报错。"""
        # Mock git rev-parse 失败
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        git_info = collect_git_info()

        assert git_info is not None
        assert git_info.is_git_repo is False
        assert git_info.branch == ""
        assert git_info.status_lines == []
        assert git_info.recent_commits == []

    @patch("mastercoder.git_info.subprocess.run")
    def test_collect_git_info_status_clean(self, mock_run: MagicMock) -> None:
        """测试 Git 状态为 clean 时。"""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true"),  # git rev-parse --is-inside-work-tree
            MagicMock(returncode=0, stdout="main"),  # git rev-parse --abbrev-ref HEAD
            MagicMock(returncode=0, stdout=""),  # git status --short (clean)
            MagicMock(returncode=0, stdout="a1b2c3d Fix bug"),  # git log --oneline -5
        ]

        git_info = collect_git_info()

        assert git_info is not None
        assert git_info.is_clean is True

    @patch("mastercoder.git_info.subprocess.run")
    def test_collect_git_info_status_limit_lines(self, mock_run: MagicMock) -> None:
        """测试 git status 结果限制行数（最多 20 行）。"""
        # 生成 25 行状态
        status_lines = ["M  file{}.py".format(i) for i in range(25)]
        status_output = "\n".join(status_lines)

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true"),  # git rev-parse --is-inside-work-tree
            MagicMock(returncode=0, stdout="main"),  # git rev-parse --abbrev-ref HEAD
            MagicMock(returncode=0, stdout=status_output),  # git status --short
            MagicMock(returncode=0, stdout="a1b2c3d Fix bug"),  # git log --oneline -5
        ]

        git_info = collect_git_info()

        assert git_info is not None
        assert len(git_info.status_lines) == 20  # 限制为 20 行

    @patch("mastercoder.git_info.subprocess.run")
    def test_collect_git_info_commits_limit(self, mock_run: MagicMock) -> None:
        """测试 git log 限制为 5 条。"""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true"),  # git rev-parse --is-inside-work-tree
            MagicMock(returncode=0, stdout="main"),  # git rev-parse --abbrev-ref HEAD
            MagicMock(returncode=0, stdout=""),  # git status --short
            MagicMock(
                returncode=0,
                stdout="a1b2c3d Fix 1\ne4f5g6h Fix 2\ni7j8k9l Fix 3\nm0n1o2p Fix 4\nq3r4s5t Fix 5\nu6v7w8x Fix 6",
            ),  # 6 commits
        ]

        git_info = collect_git_info()

        assert git_info is not None
        assert len(git_info.recent_commits) == 5  # 限制为 5 条

    @patch("mastercoder.git_info.subprocess.run")
    def test_collect_git_info_timeout(self, mock_run: MagicMock) -> None:
        """测试 Git 命令超时不影响程序。"""
        # Mock 超时异常
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=2)

        git_info = collect_git_info()

        # 超时应该被捕获，返回 None 或空 GitInfo
        assert git_info is not None
        assert git_info.is_git_repo is False


class TestGetCurrentBranch:
    """测试实时分支获取功能。"""

    @patch("mastercoder.git_info.subprocess.run")
    def test_get_current_branch_success(self, mock_run: MagicMock) -> None:
        """测试成功获取当前分支。"""
        mock_run.return_value = MagicMock(returncode=0, stdout="feature-branch")

        branch = get_current_branch()

        assert branch == "feature-branch"

    @patch("mastercoder.git_info.subprocess.run")
    def test_get_current_branch_not_git_repo(self, mock_run: MagicMock) -> None:
        """测试非 Git 仓库返回空字符串。"""
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        branch = get_current_branch()

        assert branch == ""

    @patch("mastercoder.git_info.subprocess.run")
    def test_get_current_branch_timeout(self, mock_run: MagicMock) -> None:
        """测试超时返回空字符串。"""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=2)

        branch = get_current_branch()

        assert branch == ""

    @patch("mastercoder.git_info.get_current_branch")
    def test_build_prompt_refreshes_current_branch(self, mock_branch: MagicMock) -> None:
        """测试提示符包含并刷新当前分支。"""
        mock_branch.return_value = "feature-branch"

        prompt = build_prompt(model="gpt-4o", working_dir=Path("/tmp/project"))

        assert "feature-branch" in prompt
        assert "mastercoder [gpt-4o]" in prompt


class TestGitInfoInjection:
    """测试 Git 信息注入到 system 消息。"""

    @patch("mastercoder.git_info.subprocess.run")
    def test_format_git_info_for_system_message(self, mock_run: MagicMock) -> None:
        """测试 Git 信息注入到 system 消息格式正确。"""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true"),  # git rev-parse --is-inside-work-tree
            MagicMock(returncode=0, stdout="main"),  # git rev-parse --abbrev-ref HEAD
            MagicMock(returncode=0, stdout="M  src/main.py\n?? new_file.txt"),  # git status --short
            MagicMock(
                returncode=0, stdout="a1b2c3d Fix login bug\ne4f5g6h Add user dashboard"
            ),  # git log --oneline -5
        ]

        git_info = collect_git_info()
        assert git_info is not None

        formatted = git_info.to_system_message()

        # 验证格式
        assert "Git repository detected:" in formatted
        assert "Branch: main" in formatted
        assert "Recent commits:" in formatted
        assert "a1b2c3d Fix login bug" in formatted
        assert "Status:" in formatted
        assert "M  src/main.py" in formatted

    @patch("mastercoder.git_info.subprocess.run")
    def test_format_git_info_clean_status(self, mock_run: MagicMock) -> None:
        """测试 clean 状态显示。"""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="true"),  # git rev-parse --is-inside-work-tree
            MagicMock(returncode=0, stdout="main"),  # git rev-parse --abbrev-ref HEAD
            MagicMock(returncode=0, stdout=""),  # git status --short (clean)
            MagicMock(returncode=0, stdout="a1b2c3d Fix bug"),  # git log --oneline -5
        ]

        git_info = collect_git_info()
        assert git_info is not None

        formatted = git_info.to_system_message()

        assert "Status: clean" in formatted

    @patch("mastercoder.git_info.subprocess.run")
    def test_format_git_info_not_git_repo(self, mock_run: MagicMock) -> None:
        """测试非 Git 仓库不注入信息。"""
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        git_info = collect_git_info()
        assert git_info is not None

        formatted = git_info.to_system_message()

        # 非 Git 仓库应返回空字符串
        assert formatted == ""


class TestGitInfoDataClass:
    """测试 GitInfo 数据类。"""

    def test_git_info_creation(self) -> None:
        """测试 GitInfo 创建。"""
        git_info = GitInfo(
            is_git_repo=True,
            branch="main",
            status_lines=["M  src/main.py", "?? new_file.txt"],
            recent_commits=["a1b2c3d Fix login bug", "e4f5g6h Add user dashboard"],
        )

        assert git_info.is_git_repo is True
        assert git_info.branch == "main"
        assert len(git_info.status_lines) == 2
        assert len(git_info.recent_commits) == 2
        assert git_info.is_clean is False

    def test_git_info_clean(self) -> None:
        """测试 GitInfo clean 状态。"""
        git_info = GitInfo(
            is_git_repo=True,
            branch="main",
            status_lines=[],
            recent_commits=["a1b2c3d Fix bug"],
        )

        assert git_info.is_clean is True

    def test_git_info_not_git_repo(self) -> None:
        """测试非 Git 仓库的 GitInfo。"""
        git_info = GitInfo(
            is_git_repo=False,
            branch="",
            status_lines=[],
            recent_commits=[],
        )

        assert git_info.is_git_repo is False
        assert git_info.is_clean is True
