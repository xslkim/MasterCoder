from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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


def load_settings() -> Settings:
    key = (os.getenv("OPENAI_API_KEY") or "").strip() or None
    base = (os.getenv("OPENAI_API_BASE_URL") or "").strip().rstrip("/") or None
    return Settings(
        model_name=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        github_repo=os.getenv("GITHUB_REPO", "xslkim/MasterCoder"),
        coverage_min=int(os.getenv("COVERAGE_MIN", "80")),
        state_file=Path(os.getenv("STATE_FILE", "state/req-status.json")),
        repo_root=Path(os.getenv("REPO_ROOT", ".")).resolve(),
        openai_api_key=key,
        openai_api_base_url=base,
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "512")),
    )

