"""配置加载模块 - 支持全局配置文件和环境变量。"""

import json
import os
from pathlib import Path
from typing import Any


class Config:
    """配置类，管理所有配置项。"""

    # 默认值
    DEFAULTS = {
        "api_base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o",
        "max_tokens": 4096,
        "temperature": 0.0,
        "auto_approve": False,
        "system_prompt": "",
    }

    # 环境变量映射
    ENV_MAPPING = {
        "MASTERCODER_API_BASE_URL": "api_base_url",
        "MASTERCODER_API_KEY": "api_key",
        "MASTERCODER_MODEL": "model",
    }

    # 字段范围限制
    RANGES = {
        "max_tokens": (1, 100000),
        "temperature": (0.0, 2.0),
    }

    def __init__(self) -> None:
        """初始化配置，按优先级加载：环境变量 > 配置文件 > 默认值。"""
        # 从默认值开始
        self._config: dict[str, Any] = self.DEFAULTS.copy()

        # 加载全局配置文件
        config_path = self._get_config_path()
        if config_path.exists():
            self._load_config_file(config_path)

        # 环境变量覆盖
        self._load_env_vars()

        # 验证范围
        self._validate_ranges()

    def _get_config_path(self) -> Path:
        """获取全局配置文件路径。"""
        home = Path.home()
        return home / ".mastercoder" / "config.json"

    def _load_config_file(self, config_path: Path) -> None:
        """加载配置文件。

        Args:
            config_path: 配置文件路径

        Raises:
            SystemExit: 配置文件格式非法时退出
        """
        try:
            with open(config_path, encoding="utf-8") as f:
                config_data = json.load(f)
                if isinstance(config_data, dict):
                    self._config.update(config_data)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid config file at {config_path}: {e}")
            raise SystemExit(1)
        except (OSError, IOError):
            # 文件读取错误，使用默认值
            pass

    def _load_env_vars(self) -> None:
        """从环境变量加载配置。"""
        for env_key, config_key in self.ENV_MAPPING.items():
            value = os.getenv(env_key)
            if value is not None:
                self._config[config_key] = value

    def _validate_ranges(self) -> None:
        """验证字段范围，超出范围时使用默认值并打印警告。"""
        for field, (min_val, max_val) in self.RANGES.items():
            value = self._config.get(field)
            if value is not None:
                if not (min_val <= value <= max_val):
                    default = self.DEFAULTS[field]
                    print(f"Warning: {field} value {value} out of range, using default {default}")
                    self._config[field] = default

    def get(self, key: str) -> Any:
        """获取配置项。

        Args:
            key: 配置项名称

        Returns:
            配置项值
        """
        return self._config.get(key, self.DEFAULTS.get(key))

    @property
    def api_base_url(self) -> str:
        """API 端点地址。"""
        return str(self.get("api_base_url"))

    @property
    def api_key(self) -> str:
        """API 密钥。"""
        return str(self.get("api_key"))

    @property
    def model(self) -> str:
        """模型名称。"""
        return str(self.get("model"))

    @property
    def max_tokens(self) -> int:
        """单次回复最大 token 数。"""
        return int(self.get("max_tokens"))

    @property
    def temperature(self) -> float:
        """生成温度。"""
        return float(self.get("temperature"))

    @property
    def auto_approve(self) -> bool:
        """是否自动批准工具调用。"""
        return bool(self.get("auto_approve"))

    @property
    def system_prompt(self) -> str:
        """自定义系统提示词。"""
        return str(self.get("system_prompt"))

    def mask_api_key(self) -> str:
        """脱敏显示 API Key。

        Returns:
            脱敏后的 API Key，格式为 sk-****<后4位>
        """
        key = self.api_key
        if not key:
            return ""
        if len(key) <= 7:
            return "****"
        return f"{key[:3]}****{key[-4:]}"

    def to_dict(self) -> dict[str, Any]:
        """将配置转换为字典。

        Returns:
            配置字典
        """
        return self._config.copy()

    def __repr__(self) -> str:
        """字符串表示。"""
        return f"Config({self.to_dict()})"


# 全局配置实例
_config: Config | None = None


def get_config() -> Config:
    """获取全局配置实例。

    Returns:
        Config 实例
    """
    global _config
    if _config is None:
        _config = Config()
        # 记录配置（脱敏）
        _log_config(_config)
    return _config


def _log_config(config: Config) -> None:
    """记录配置到日志（脱敏显示）。

    Args:
        config: 配置实例
    """
    # 在实际实现中，这里应该写入日志文件
    # 目前仅作为占位，确保 api_key 脱敏
    masked_config = config.to_dict()
    masked_config["api_key"] = config.mask_api_key()
    # 避免打印到用户可见界面，仅用于调试
    # print(f"[DEBUG] Config loaded: {masked_config}")
