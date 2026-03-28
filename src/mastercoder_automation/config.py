from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# 智谱 GLM Coding API（OpenAI 兼容）：模型与 Base URL 固定，仅需设置环境变量 OPENAI_API_KEY。
DEFAULT_LLM_MODEL_NAME = "glm-5"
DEFAULT_OPENAI_API_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    model_name: str
    github_repo: str
    coverage_min: int
    state_file: Path
    repo_root: Path
    openai_api_key: str | None = None
    openai_api_base_url: str | None = None
    llm_max_tokens: int = 512
    #: Wait for a real GitHub PR review from GIT_AGENT_USERNAME_REVIEW (no LLM verdict for review step).
    strict_human_review: bool = False
    #: Wait for a PR issue comment from GIT_AGENT_USERNAME_TEST starting with QA_PASSED / QA_FAILED.
    strict_human_qa: bool = False
    human_poll_interval_sec: int = 30
    human_poll_timeout_sec: int = 3600


def load_settings() -> Settings:
    key = (os.getenv("OPENAI_API_KEY") or "").strip() or None
    base = DEFAULT_OPENAI_API_BASE_URL.strip().rstrip("/")
    return Settings(
        model_name=DEFAULT_LLM_MODEL_NAME,
        github_repo=os.getenv("GITHUB_REPO", "xslkim/MasterCoder"),
        coverage_min=int(os.getenv("COVERAGE_MIN", "80")),
        state_file=Path(os.getenv("STATE_FILE", "state/req-status.json")),
        repo_root=Path(os.getenv("REPO_ROOT", ".")).resolve(),
        openai_api_key=key,
        openai_api_base_url=base,
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "512")),
        strict_human_review=_env_bool("AUTOMATION_STRICT_HUMAN_REVIEW"),
        strict_human_qa=_env_bool("AUTOMATION_STRICT_HUMAN_QA"),
        human_poll_interval_sec=int(os.getenv("AUTOMATION_HUMAN_POLL_INTERVAL_SEC", "30")),
        human_poll_timeout_sec=int(os.getenv("AUTOMATION_HUMAN_POLL_TIMEOUT_SEC", "3600")),
    )

