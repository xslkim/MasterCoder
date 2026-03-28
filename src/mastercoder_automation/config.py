from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

# 智谱 GLM Coding API（OpenAI 兼容）：模型与 Base URL 固定，仅需设置环境变量 OPENAI_API_KEY。
DEFAULT_LLM_MODEL_NAME = "glm-5"
DEFAULT_OPENAI_API_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"
# 单次补全上限；过小易导致工具调用/写文件被截断。可用环境变量 LLM_MAX_TOKENS 覆盖。
DEFAULT_LLM_MAX_TOKENS = 4096

_log = logging.getLogger(__name__)


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def _parse_positive_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        v = int(str(raw).strip(), 10)
    except ValueError:
        _log.warning("环境变量 %s=%r 不是合法整数，已回退为默认值 %s", name, raw, default)
        return default
    if v < minimum:
        _log.warning("环境变量 %s=%s 小于下限 %s，已回退为默认值 %s", name, v, minimum, default)
        return default
    return v


def _state_file_path(repo_root: Path) -> Path:
    raw = os.getenv("STATE_FILE", "state/req-status.json")
    p = Path(raw)
    return p if p.is_absolute() else (repo_root / p).resolve()


@dataclass(frozen=True)
class Settings:
    model_name: str
    github_repo: str
    coverage_min: int
    state_file: Path
    repo_root: Path
    openai_api_key: str | None = None
    openai_api_base_url: str | None = None
    llm_max_tokens: int = DEFAULT_LLM_MAX_TOKENS
    #: Wait for a real GitHub PR review from GIT_AGENT_USERNAME_REVIEW (no LLM verdict for review step).
    strict_human_review: bool = False
    #: Wait for a PR issue comment from GIT_AGENT_USERNAME_TEST starting with QA_PASSED / QA_FAILED.
    strict_human_qa: bool = False
    human_poll_interval_sec: int = 30
    human_poll_timeout_sec: int = 3600


def load_settings() -> Settings:
    key = (os.getenv("OPENAI_API_KEY") or "").strip() or None
    base = DEFAULT_OPENAI_API_BASE_URL.strip().rstrip("/")
    repo_root = Path(os.getenv("REPO_ROOT", ".")).resolve()
    return Settings(
        model_name=DEFAULT_LLM_MODEL_NAME,
        github_repo=os.getenv("GITHUB_REPO", "xslkim/MasterCoder"),
        coverage_min=_parse_positive_int("COVERAGE_MIN", 80, minimum=0),
        state_file=_state_file_path(repo_root),
        repo_root=repo_root,
        openai_api_key=key,
        openai_api_base_url=base,
        llm_max_tokens=_parse_positive_int("LLM_MAX_TOKENS", DEFAULT_LLM_MAX_TOKENS, minimum=1),
        strict_human_review=_env_bool("AUTOMATION_STRICT_HUMAN_REVIEW"),
        strict_human_qa=_env_bool("AUTOMATION_STRICT_HUMAN_QA"),
        human_poll_interval_sec=_parse_positive_int("AUTOMATION_HUMAN_POLL_INTERVAL_SEC", 30, minimum=1),
        human_poll_timeout_sec=_parse_positive_int(
            "AUTOMATION_HUMAN_POLL_TIMEOUT_SEC", 3600, minimum=1
        ),
    )
