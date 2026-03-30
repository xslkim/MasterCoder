"""System prompt Git 信息注入测试 - REQ-25。"""

from pathlib import Path

from mastercoder.git_info import GitInfo
from mastercoder.system_prompt import build_system_prompt


class TestSystemPromptGitInjection:
    """测试 Git 信息注入到 system prompt。"""

    def test_build_system_prompt_with_git_info(self, tmp_path: Path) -> None:
        """测试构建包含 Git 信息的 system prompt。"""
        git_info = GitInfo(
            is_git_repo=True,
            branch="main",
            status_lines=["M  src/main.py", "?? new_file.txt"],
            recent_commits=["a1b2c3d Fix login bug", "e4f5g6h Add user dashboard"],
        )

        system_prompt = build_system_prompt(
            working_dir=tmp_path,
            custom_prompt="",
            git_info=git_info,
        )

        # 验证包含 Git 信息
        assert "Git repository detected:" in system_prompt
        assert "Branch: main" in system_prompt
        assert "Recent commits:" in system_prompt
        assert "a1b2c3d Fix login bug" in system_prompt
        assert "Status:" in system_prompt
        assert "M  src/main.py" in system_prompt

    def test_build_system_prompt_git_clean_status(self, tmp_path: Path) -> None:
        """测试 Git 状态为 clean 时的 system prompt。"""
        git_info = GitInfo(
            is_git_repo=True,
            branch="main",
            status_lines=[],
            recent_commits=["a1b2c3d Fix bug"],
        )

        system_prompt = build_system_prompt(
            working_dir=tmp_path,
            custom_prompt="",
            git_info=git_info,
        )

        # 验证包含 clean 状态
        assert "Status: clean" in system_prompt

    def test_build_system_prompt_not_git_repo(self, tmp_path: Path) -> None:
        """测试非 Git 仓库的 system prompt。"""
        git_info = GitInfo(
            is_git_repo=False,
            branch="",
            status_lines=[],
            recent_commits=[],
        )

        system_prompt = build_system_prompt(
            working_dir=tmp_path,
            custom_prompt="",
            git_info=git_info,
        )

        # 验证不包含 Git 信息
        assert "Git repository detected:" not in system_prompt
        assert "Branch:" not in system_prompt

    def test_build_system_prompt_no_git_info(self, tmp_path: Path) -> None:
        """测试未提供 Git 信息时的 system prompt。"""
        system_prompt = build_system_prompt(
            working_dir=tmp_path,
            custom_prompt="",
            git_info=None,
        )

        # 验证不包含 Git 信息
        assert "Git repository detected:" not in system_prompt

    def test_build_system_prompt_with_custom_prompt_and_git(self, tmp_path: Path) -> None:
        """测试包含自定义提示词和 Git 信息的完整 system prompt。"""
        git_info = GitInfo(
            is_git_repo=True,
            branch="feature-branch",
            status_lines=["M  src/utils.py"],
            recent_commits=["a1b2c3d Add feature"],
        )

        system_prompt = build_system_prompt(
            working_dir=tmp_path,
            custom_prompt="Always use TypeScript",
            git_info=git_info,
        )

        # 验证包含所有部分
        assert "You are MasterCoder" in system_prompt
        assert "Git repository detected:" in system_prompt
        assert "Branch: feature-branch" in system_prompt
        assert "Custom instructions:" in system_prompt
        assert "Always use TypeScript" in system_prompt

        # 验证顺序：内置 -> Git -> 自定义
        builtin_idx = system_prompt.index("You are MasterCoder")
        git_idx = system_prompt.index("Git repository detected:")
        custom_idx = system_prompt.index("Custom instructions:")

        assert builtin_idx < git_idx < custom_idx

    def test_build_system_prompt_with_mastercoder_md_and_git(self, tmp_path: Path) -> None:
        """测试包含 MASTERCODER.md 和 Git 信息的完整 system prompt。"""
        # 创建 MASTERCODER.md
        mastercoder_md = tmp_path / "MASTERCODER.md"
        mastercoder_md.write_text("Always use Python type hints")

        git_info = GitInfo(
            is_git_repo=True,
            branch="main",
            status_lines=[],
            recent_commits=["a1b2c3d Initial commit"],
        )

        system_prompt = build_system_prompt(
            working_dir=tmp_path,
            custom_prompt="Keep it simple",
            git_info=git_info,
        )

        # 验证包含所有部分
        assert "You are MasterCoder" in system_prompt
        assert "Project instructions (from MASTERCODER.md):" in system_prompt
        assert "Always use Python type hints" in system_prompt
        assert "Git repository detected:" in system_prompt
        assert "Custom instructions:" in system_prompt
        assert "Keep it simple" in system_prompt

        # 验证顺序：内置 -> MASTERCODER.md -> Git -> 自定义
        builtin_idx = system_prompt.index("You are MasterCoder")
        md_idx = system_prompt.index("Project instructions")
        git_idx = system_prompt.index("Git repository detected:")
        custom_idx = system_prompt.index("Custom instructions:")

        assert builtin_idx < md_idx < git_idx < custom_idx
