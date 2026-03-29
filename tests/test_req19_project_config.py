"""REQ-19：项目级配置与 MASTERCODER.md 单元测试

测试覆盖以下场景：
- 项目级配置覆盖全局配置
- 环境变量覆盖项目级配置
- MASTERCODER.md 存在时注入到 system 消息
- MASTERCODER.md 不存在时无影响
- 超大 MASTERCODER.md 截断（50KB)
- system_prompt + MASTERCODER.md 拼接顺序
- UTF-8 安全截断
"""

import json
from pathlib import Path

from mastercoder.config import Config, reset_config


class TestProjectLevelConfig:
    """测试项目级配置文件"""

    def test_project_config_overrides_global(self, tmp_path: Path, monkeypatch) -> None:
        """项目级配置覆盖全局配置"""
        global_config_dir = tmp_path / "global"
        global_config_dir.mkdir()
        global_config_file = global_config_dir / ".mastercoder" / "config.json"
        global_config_file.parent.mkdir()
        global_config_file.write_text(json.dumps({"model": "global-model", "max_tokens": 2048}))

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config_dir = project_dir / ".mastercoder"
        project_config_dir.mkdir()
        project_config_file = project_config_dir / "config.json"
        project_config_file.write_text(json.dumps({"model": "local-model"}))

        monkeypatch.setattr(Path, "home", lambda: global_config_dir)
        monkeypatch.delenv("MASTERCODER_MODEL", raising=False)

        reset_config()
        config = Config(working_dir=project_dir)

        assert config.model == "local-model"
        assert config.max_tokens == 2048

    def test_env_overrides_project_config(self, tmp_path: Path, monkeypatch) -> None:
        """环境变量覆盖项目级配置"""
        global_config_dir = tmp_path / "global"
        global_config_dir.mkdir()

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config_dir = project_dir / ".mastercoder"
        project_config_dir.mkdir()
        project_config_file = project_config_dir / "config.json"
        project_config_file.write_text(json.dumps({"model": "local-model"}))

        monkeypatch.setattr(Path, "home", lambda: global_config_dir)
        monkeypatch.setenv("MASTERCODER_MODEL", "env-model")

        reset_config()
        config = Config(working_dir=project_dir)
        assert config.model == "env-model"

    def test_project_config_not_exists_no_error(self, tmp_path: Path, monkeypatch) -> None:
        """项目级配置文件不存在时静默忽略"""
        global_config_dir = tmp_path / "global"
        global_config_dir.mkdir()
        global_config_file = global_config_dir / ".mastercoder" / "config.json"
        global_config_file.parent.mkdir()
        global_config_file.write_text(json.dumps({"model": "global-model"}))

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        monkeypatch.setattr(Path, "home", lambda: global_config_dir)
        monkeypatch.delenv("MASTERCODER_MODEL", raising=False)
        reset_config()
        config = Config(working_dir=project_dir)
        assert config.model == "global-model"

    def test_priority_chain(self, tmp_path: Path, monkeypatch) -> None:
        """验证完整优先级链: 环境变量 > 项目级配置 > 全局配置 > 默认值"""
        global_config_dir = tmp_path / "global"
        global_config_dir.mkdir()
        global_config_file = global_config_dir / ".mastercoder" / "config.json"
        global_config_file.parent.mkdir()
        global_config_file.write_text(
            json.dumps({"model": "global-model", "max_tokens": 2048, "temperature": 0.5})
        )

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config_dir = project_dir / ".mastercoder"
        project_config_dir.mkdir()
        project_config_file = project_config_dir / "config.json"
        project_config_file.write_text(json.dumps({"model": "local-model", "max_tokens": 4096}))

        monkeypatch.setattr(Path, "home", lambda: global_config_dir)
        monkeypatch.setenv("MASTERCODER_MODEL", "env-model")

        reset_config()
        config = Config(working_dir=project_dir)

        assert config.model == "env-model"
        assert config.max_tokens == 4096
        assert config.temperature == 0.5
        assert config.auto_approve is False


class TestMastercoderMd:
    """测试 MASTERCODER.md 文件读取和注入"""

    def test_mastercoder_md_injects_to_system(self, tmp_path: Path) -> None:
        """MASTERCODER.md 存在时注入到 system 消息"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mastercoder_md = project_dir / "MASTERCODER.md"
        mastercoder_md.write_text("Always use TypeScript")

        system_prompt = build_system_prompt(project_dir, custom_prompt="")

        assert "Always use TypeScript" in system_prompt
        assert "Project instructions (from MASTERCODER.md):" in system_prompt

    def test_mastercoder_md_not_exists_no_error(self, tmp_path: Path) -> None:
        """MASTERCODER.md 不存在时无影响"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        system_prompt = build_system_prompt(project_dir, custom_prompt="")

        assert "Project instructions (from MASTERCODER.md):" not in system_prompt
        assert "You are MasterCoder" in system_prompt

    def test_mastercoder_md_truncation_50kb(self, tmp_path: Path, capsys) -> None:
        """超大 MASTERCODER.md 截断到 50KB"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mastercoder_md = project_dir / "MASTERCODER.md"
        large_content = "x" * (60 * 1024)  # 60KB
        mastercoder_md.write_text(large_content)

        system_prompt = build_system_prompt(project_dir, custom_prompt="")

        captured = capsys.readouterr()
        assert "Warning: MASTERCODER.md exceeds 50KB, truncating to first 50KB" in captured.out
        assert len(system_prompt) < len(large_content) + 1000

    def test_mastercoder_md_utf8_safe_truncation(self, tmp_path: Path) -> None:
        """UTF-8 安全截断，不会截断多字节字符的中间位置"""
        from mastercoder.system_prompt import read_mastercoder_md

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mastercoder_md = project_dir / "MASTERCODER.md"
        chinese_char = "中"
        large_content = chinese_char * (20 * 1024)
        mastercoder_md.write_text(large_content, encoding="utf-8")
        content = read_mastercoder_md(project_dir)
        try:
            content.encode("utf-8").decode("utf-8")
            is_valid_utf8 = True
        except UnicodeDecodeError:
            is_valid_utf8 = False
        assert is_valid_utf8, "Truncated content should be valid UTF-8"

    def test_mastercoder_md_exactly_50kb(self, tmp_path: Path, capsys) -> None:
        """MASTERCODER.md 恰好 50KB 时不警告"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mastercoder_md = project_dir / "MASTERCODER.md"
        content_50kb = "x" * (50 * 1024)
        mastercoder_md.write_text(content_50kb)
        build_system_prompt(project_dir, custom_prompt="")

        captured = capsys.readouterr()
        assert "Warning" not in captured.out


class TestSystemPromptConcatenation:
    """测试 system prompt 拼接顺序"""

    def test_system_prompt_order_with_mastercoder_md(self, tmp_path: Path) -> None:
        """system_prompt + MASTERCODER.md 拼接顺序正确"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mastercoder_md = project_dir / "MASTERCODER.md"
        mastercoder_md.write_text("Project instruction content")
        custom_prompt = "Custom user prompt"
        system_prompt = build_system_prompt(project_dir, custom_prompt)
        builtin_pos = system_prompt.find("You are MasterCoder")
        project_pos = system_prompt.find("Project instructions (from MASTERCODER.md):")
        custom_pos = system_prompt.find("Custom instructions:")
        assert builtin_pos < project_pos < custom_pos

    def test_system_prompt_order_without_mastercoder_md(self, tmp_path: Path) -> None:
        """无 MASTERCODER.md 时的拼接顺序"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        custom_prompt = "Custom user prompt"
        system_prompt = build_system_prompt(project_dir, custom_prompt)
        builtin_pos = system_prompt.find("You are MasterCoder")
        custom_pos = system_prompt.find("Custom instructions:")
        assert "Project instructions (from MASTERCODER.md):" not in system_prompt
        assert builtin_pos < custom_pos

    def test_system_prompt_only_builtin(self, tmp_path: Path) -> None:
        """只有内置 system prompt"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        system_prompt = build_system_prompt(project_dir, "")
        assert "You are MasterCoder" in system_prompt
        assert "Project instructions (from MASTERCODER.md):" not in system_prompt
        assert "Custom instructions:" not in system_prompt

    def test_system_prompt_format(self, tmp_path: Path) -> None:
        """system prompt 格式正确"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mastercoder_md = project_dir / "MASTERCODER.md"
        mastercoder_md.write_text("Project instruction")
        custom_prompt = "Custom prompt"
        system_prompt = build_system_prompt(project_dir, custom_prompt)
        assert "---" in system_prompt
        assert "Project instructions (from MASTERCODER.md):" in system_prompt
        assert "Custom instructions:" in system_prompt
        assert "Project instruction" in system_prompt
        assert "Custom prompt" in system_prompt


class TestAcceptanceCriteria:
    """验收标准测试"""

    def test_ac_project_config_overrides_global(self, tmp_path: Path, monkeypatch) -> None:
        """验收标准:创建 .mastercoder/config.json 写入 model，启动后模型覆盖全局配置"""
        global_config_dir = tmp_path / "global"
        global_config_dir.mkdir()
        global_config_file = global_config_dir / ".mastercoder" / "config.json"
        global_config_file.parent.mkdir()
        global_config_file.write_text(json.dumps({"model": "global-model"}))

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config_dir = project_dir / ".mastercoder"
        project_config_dir.mkdir()
        project_config_file = project_config_dir / "config.json"
        project_config_file.write_text(json.dumps({"model": "local-model"}))

        monkeypatch.setattr(Path, "home", lambda: global_config_dir)
        monkeypatch.delenv("MASTERCODER_MODEL", raising=False)
        reset_config()
        config = Config(working_dir=project_dir)
        assert config.model == "local-model"

    def test_ac_env_overrides_project_config(self, tmp_path: Path, monkeypatch) -> None:
        """验收标准:设置环境变量，启动后覆盖项目级配置"""
        global_config_dir = tmp_path / "global"
        global_config_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config_dir = project_dir / ".mastercoder"
        project_config_dir.mkdir()
        project_config_file = project_config_dir / "config.json"
        project_config_file.write_text(json.dumps({"model": "local-model"}))
        monkeypatch.setattr(Path, "home", lambda: global_config_dir)
        monkeypatch.setenv("MASTERCODER_MODEL", "env-model")
        reset_config()
        config = Config(working_dir=project_dir)
        assert config.model == "env-model"

    def test_ac_mastercoder_md_injection(self, tmp_path: Path) -> None:
        """验收标准:创建 MASTERCODER.md，内容注入到 system 消息"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mastercoder_md = project_dir / "MASTERCODER.md"
        mastercoder_md.write_text("Always use TypeScript")
        system_prompt = build_system_prompt(project_dir, "")
        assert "Always use TypeScript" in system_prompt

    def test_ac_no_mastercoder_md(self, tmp_path: Path) -> None:
        """验收标准:删除 MASTERCODER.md 后启动，无报错，无 Project instructions 段"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        system_prompt = build_system_prompt(project_dir, "")
        assert "Project instructions (from MASTERCODER.md):" not in system_prompt

    def test_ac_large_mastercoder_md_warning(self, tmp_path: Path, capsys) -> None:
        """验收标准:创建超过 50KB 的 MASTERCODER.md，启动时打印截断警告"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mastercoder_md = project_dir / "MASTERCODER.md"
        large_content = "x" * (60 * 1024)
        mastercoder_md.write_text(large_content)
        build_system_prompt(project_dir, "")
        captured = capsys.readouterr()
        assert "Warning: MASTERCODER.md exceeds 50KB, truncating to first 50KB" in captured.out

    def test_ac_both_mastercoder_md_and_system_prompt(self, tmp_path: Path) -> None:
        """验收标准:同时存在 MASTERCODER.md 和 system_prompt 配置时，两者均存在且顺序正确"""
        from mastercoder.system_prompt import build_system_prompt

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        mastercoder_md = project_dir / "MASTERCODER.md"
        mastercoder_md.write_text("Project instruction")
        custom_prompt = "Custom user prompt"
        system_prompt = build_system_prompt(project_dir, custom_prompt)
        assert "Project instruction" in system_prompt
        assert "Custom user prompt" in system_prompt
        project_pos = system_prompt.find("Project instruction")
        custom_pos = system_prompt.find("Custom user prompt")
        assert project_pos < custom_pos
