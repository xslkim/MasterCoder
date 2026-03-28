"""REQ-02：配置系统单元测试

测试覆盖以下场景：
- 无配置文件时使用默认值
- 正常解析配置文件
- 环境变量覆盖配置文件
- JSON 格式非法时报错退出
- 字段值超出范围时使用默认值并打印警告
- API Key 脱敏显示
- 配置优先级：环境变量 > 配置文件 > 默认值
"""

import json
from pathlib import Path

import pytest

from mastercoder.config import Config, get_config


class TestConfigDefaults:
    """测试默认配置值"""

    def test_no_config_file_uses_defaults(self, tmp_path: Path, monkeypatch) -> None:
        """无配置文件时使用默认值"""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # 清除环境变量
        monkeypatch.delenv("MASTERCODER_API_BASE_URL", raising=False)
        monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)
        monkeypatch.delenv("MASTERCODER_MODEL", raising=False)

        config = Config()

        assert config.api_base_url == "https://api.openai.com/v1"
        assert config.api_key == ""
        assert config.model == "gpt-4o"
        assert config.max_tokens == 4096
        assert config.temperature == 0.0
        assert config.auto_approve is False
        assert config.system_prompt == ""

    def test_default_config_values(self) -> None:
        """验证默认配置结构"""
        defaults = Config.DEFAULTS
        assert defaults["api_base_url"] == "https://api.openai.com/v1"
        assert defaults["api_key"] == ""
        assert defaults["model"] == "gpt-4o"
        assert defaults["max_tokens"] == 4096
        assert defaults["temperature"] == 0.0
        assert defaults["auto_approve"] is False
        assert defaults["system_prompt"] == ""


class TestConfigFileParsing:
    """测试配置文件解析"""

    def test_parse_valid_config_file(self, tmp_path: Path, monkeypatch) -> None:
        """正常解析配置文件"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {"api_key": "sk-test123", "model": "deepseek-chat"}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)
        monkeypatch.delenv("MASTERCODER_MODEL", raising=False)

        config = Config()

        assert config.api_key == "sk-test123"
        assert config.model == "deepseek-chat"
        # 其他字段使用默认值
        assert config.max_tokens == 4096
        assert config.temperature == 0.0

    def test_parse_full_config_file(self, tmp_path: Path, monkeypatch) -> None:
        """解析包含所有字段的配置文件"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {
            "api_base_url": "https://custom.api.com/v1",
            "api_key": "sk-fulltest",
            "model": "gpt-3.5-turbo",
            "max_tokens": 2048,
            "temperature": 0.7,
            "auto_approve": True,
            "system_prompt": "You are a helpful assistant",
        }
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)
        monkeypatch.delenv("MASTERCODER_MODEL", raising=False)

        config = Config()

        assert config.api_base_url == "https://custom.api.com/v1"
        assert config.api_key == "sk-fulltest"
        assert config.model == "gpt-3.5-turbo"
        assert config.max_tokens == 2048
        assert config.temperature == 0.7
        assert config.auto_approve is True
        assert config.system_prompt == "You are a helpful assistant"


class TestEnvironmentVariables:
    """测试环境变量覆盖"""

    def test_env_overrides_config_file(self, tmp_path: Path, monkeypatch) -> None:
        """环境变量覆盖配置文件"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {
            "api_key": "sk-filekey",
            "model": "gpt-4",
            "api_base_url": "https://file.api.com/v1",
        }
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("MASTERCODER_API_KEY", "sk-envkey")
        monkeypatch.setenv("MASTERCODER_MODEL", "claude-3")
        monkeypatch.setenv("MASTERCODER_API_BASE_URL", "https://env.api.com/v1")

        config = Config()

        # 环境变量优先级最高
        assert config.api_key == "sk-envkey"
        assert config.model == "claude-3"
        assert config.api_base_url == "https://env.api.com/v1"

    def test_partial_env_override(self, tmp_path: Path, monkeypatch) -> None:
        """部分环境变量覆盖"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {"api_key": "sk-filekey", "model": "gpt-4"}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("MASTERCODER_API_KEY", "sk-envkey")
        monkeypatch.delenv("MASTERCODER_MODEL", raising=False)
        monkeypatch.delenv("MASTERCODER_API_BASE_URL", raising=False)

        config = Config()

        assert config.api_key == "sk-envkey"  # 来自环境变量
        assert config.model == "gpt-4"  # 来自配置文件


class TestInvalidConfig:
    """测试非法配置处理"""

    def test_invalid_json_exits_with_error(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """JSON 格式非法时报错退出"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_file.write_text("{bad}")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            Config()

        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error: Invalid config file at" in captured.out
        assert str(config_file) in captured.out


class TestFieldValidation:
    """测试字段校验"""

    def test_max_tokens_out_of_range_high(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """max_tokens 超出上限时使用默认值并警告"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {"max_tokens": 200000}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()

        assert config.max_tokens == 4096  # 使用默认值

        captured = capsys.readouterr()
        assert "Warning: max_tokens value 200000 out of range, using default 4096" in captured.out

    def test_max_tokens_out_of_range_low(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """max_tokens 低于下限时使用默认值并警告"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {"max_tokens": 0}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()

        assert config.max_tokens == 4096

        captured = capsys.readouterr()
        assert "Warning: max_tokens value 0 out of range, using default 4096" in captured.out

    def test_temperature_out_of_range_high(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """temperature 超出上限时使用默认值并警告"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {"temperature": 5.0}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()

        assert config.temperature == 0.0

        captured = capsys.readouterr()
        assert "Warning: temperature value 5.0 out of range, using default 0.0" in captured.out

    def test_temperature_out_of_range_low(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """temperature 低于下限时使用默认值并警告"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {"temperature": -0.5}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()

        assert config.temperature == 0.0

        captured = capsys.readouterr()
        assert "Warning: temperature value -0.5 out of range, using default 0.0" in captured.out

    def test_valid_range_boundaries(self, tmp_path: Path, monkeypatch) -> None:
        """测试合法范围的边界值"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {"max_tokens": 1, "temperature": 0.0}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()

        assert config.max_tokens == 1
        assert config.temperature == 0.0

    def test_valid_range_upper_boundaries(self, tmp_path: Path, monkeypatch) -> None:
        """测试合法范围的上限边界值"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {"max_tokens": 100000, "temperature": 2.0}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        config = Config()

        assert config.max_tokens == 100000
        assert config.temperature == 2.0


class TestApiKeyMasking:
    """测试 API Key 脱敏"""

    def test_api_key_masking(self, tmp_path: Path, monkeypatch) -> None:
        """api_key 脱敏显示"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {"api_key": "sk-test1234567890"}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

        config = Config()

        # 检查脱敏方法
        masked = config.mask_api_key()
        assert masked == "sk-****7890"
        assert "test1234567890" not in masked

    def test_api_key_masking_short_key(self, tmp_path: Path, monkeypatch) -> None:
        """短 api_key 的脱敏"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        config_data = {"api_key": "sk-ab"}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

        config = Config()

        masked = config.mask_api_key()
        assert masked == "****"

    def test_api_key_masking_empty_key(self, tmp_path: Path, monkeypatch) -> None:
        """空 api_key 的脱敏"""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

        config = Config()

        masked = config.mask_api_key()
        assert masked == ""


class TestConfigPriority:
    """测试配置优先级"""

    def test_priority_env_over_file_over_default(self, tmp_path: Path, monkeypatch) -> None:
        """验证优先级：环境变量 > 配置文件 > 默认值"""
        config_dir = tmp_path / ".mastercoder"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        # 配置文件中的值
        config_data = {"model": "file-model", "max_tokens": 2048}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("MASTERCODER_MODEL", "env-model")
        # max_tokens 没有环境变量，应该使用配置文件的值
        # api_key 既没有配置文件也没有环境变量，应该使用默认值

        config = Config()

        assert config.model == "env-model"  # 环境变量优先
        assert config.max_tokens == 2048  # 配置文件次之
        assert config.auto_approve is False  # 默认值


class TestGlobalConfig:
    """测试全局配置实例"""

    def test_get_config_singleton(self, tmp_path: Path, monkeypatch) -> None:
        """get_config 返回单例"""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

        # 重置全局配置
        import mastercoder.config

        mastercoder.config._config = None

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2
