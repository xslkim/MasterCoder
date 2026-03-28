"""测试配置系统 - REQ-02。

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


def test_no_config_file_uses_defaults(tmp_path: Path, monkeypatch) -> None:
    """无配置文件时使用默认值。"""
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


def test_normal_config_file_parsing(tmp_path: Path, monkeypatch) -> None:
    """正常解析配置文件。"""
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {
        "api_key": "sk-test123",
        "model": "deepseek-chat",
        "max_tokens": 8192,
        "temperature": 0.7,
        "auto_approve": True,
        "system_prompt": "Custom prompt",
    }

    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)
    monkeypatch.delenv("MASTERCODER_MODEL", raising=False)

    config = Config()

    assert config.api_key == "sk-test123"
    assert config.model == "deepseek-chat"
    assert config.max_tokens == 8192
    assert config.temperature == 0.7
    assert config.auto_approve is True
    assert config.system_prompt == "Custom prompt"


def test_env_vars_override_config_file(tmp_path: Path, monkeypatch) -> None:
    """环境变量覆盖配置文件。"""
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {"api_key": "sk-filekey", "model": "file-model"}

    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("MASTERCODER_API_KEY", "sk-envkey")
    monkeypatch.setenv("MASTERCODER_MODEL", "env-model")

    config = Config()

    assert config.api_key == "sk-envkey"
    assert config.model == "env-model"


def test_invalid_json_exits(tmp_path: Path, monkeypatch, capsys) -> None:
    """JSON 格式非法时报错退出。"""
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_file.write_text("{bad}", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        Config()

    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "Error: Invalid config file at" in captured.out
    assert str(config_file) in captured.out


def test_max_tokens_out_of_range_uses_default(tmp_path: Path, monkeypatch, capsys) -> None:
    """max_tokens 超出范围时使用默认值并打印警告。"""
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {"max_tokens": 200000}  # 超出 100000 上限

    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    config = Config()

    assert config.max_tokens == 4096  # 使用默认值

    captured = capsys.readouterr()
    assert "Warning: max_tokens value 200000 out of range, using default 4096" in captured.out


def test_temperature_out_of_range_uses_default(tmp_path: Path, monkeypatch, capsys) -> None:
    """temperature 超出范围时使用默认值并打印警告。"""
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {"temperature": 5.0}  # 超出 2.0 上限

    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    config = Config()

    assert config.temperature == 0.0  # 使用默认值

    captured = capsys.readouterr()
    assert "Warning: temperature value 5.0 out of range, using default 0.0" in captured.out


def test_api_key_masking(tmp_path: Path, monkeypatch) -> None:
    """API Key 脱敏显示。"""
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {"api_key": "sk-test1234abcd"}
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

    config = Config()

    masked = config.mask_api_key()
    assert masked == "sk-****abcd"
    assert "test1234" not in masked


def test_api_key_masking_short_key(tmp_path: Path, monkeypatch) -> None:
    """API Key 脱敏显示 - 短 key。"""
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {"api_key": "short"}
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

    config = Config()

    masked = config.mask_api_key()
    assert masked == "****"


def test_api_key_masking_empty(tmp_path: Path, monkeypatch) -> None:
    """API Key 脱敏显示 - 空 key。"""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

    config = Config()

    masked = config.mask_api_key()
    assert masked == ""


def test_config_priority_chain(tmp_path: Path, monkeypatch) -> None:
    """配置优先级：环境变量 > 配置文件 > 默认值。"""
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    # 配置文件中的值
    config_data = {"model": "file-model", "max_tokens": 5000}
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("MASTERCODER_MODEL", "env-model")
    # max_tokens 使用配置文件的值

    config = Config()

    # 环境变量覆盖配置文件
    assert config.model == "env-model"
    # 配置文件覆盖默认值
    assert config.max_tokens == 5000
    # 默认值
    assert config.temperature == 0.0


def test_get_config_singleton(tmp_path: Path, monkeypatch) -> None:
    """get_config 返回单例。"""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

    # 重置全局配置
    import mastercoder.config

    mastercoder.config._config = None

    config1 = get_config()
    config2 = get_config()

    assert config1 is config2


def test_config_file_nonexistent(tmp_path: Path, monkeypatch) -> None:
    """配置文件不存在时不报错，使用默认值。"""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("MASTERCODER_API_KEY", raising=False)

    # 不创建配置文件
    config = Config()

    assert config.api_key == ""
    assert config.model == "gpt-4o"


def test_max_tokens_at_boundary(tmp_path: Path, monkeypatch) -> None:
    """max_tokens 在边界值时正常工作。"""
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    # 测试最小值
    config_data = {"max_tokens": 1}
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    config = Config()
    assert config.max_tokens == 1

    # 测试最大值
    config_data = {"max_tokens": 100000}
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    config = Config()
    assert config.max_tokens == 100000


def test_temperature_at_boundary(tmp_path: Path, monkeypatch) -> None:
    """temperature 在边界值时正常工作。"""
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    # 测试最小值
    config_data = {"temperature": 0.0}
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    config = Config()
    assert config.temperature == 0.0

    # 测试最大值
    config_data = {"temperature": 2.0}
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    config = Config()
    assert config.temperature == 2.0
