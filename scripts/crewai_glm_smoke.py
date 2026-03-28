#!/usr/bin/env python3
"""Minimal CrewAI smoke test: one Agent, one Task, GLM via OpenAI-compatible API.

Run:
  cd /path/to/MasterCoder
  source .env.sh
  python3 scripts/crewai_glm_smoke.py

Requires: OPENAI_API_KEY (model and base URL match ``mastercoder_automation.config`` defaults).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
_src = _root / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from mastercoder_automation.config import (  # noqa: E402
    DEFAULT_LLM_MODEL_NAME,
    DEFAULT_OPENAI_API_BASE_URL,
)


def main() -> int:
    # Avoid interactive tracing prompt + stdin issues in headless runs
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

    from crewai import Agent, Crew, LLM, Process, Task

    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    base_url = DEFAULT_OPENAI_API_BASE_URL.rstrip("/")
    model = DEFAULT_LLM_MODEL_NAME

    if not api_key:
        print("error: OPENAI_API_KEY is not set (source .env.sh first)", file=sys.stderr)
        return 1

    llm = LLM(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0,
        max_tokens=256,
    )

    agent = Agent(
        role="SmokeTester",
        goal="Prove the LLM is reachable from CrewAI.",
        backstory="You answer short verification prompts literally.",
        llm=llm,
        verbose=False,
    )
    task = Task(
        description='Reply with exactly one word: "pong". No other text.',
        expected_output='The single word "pong".',
        agent=agent,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        tracing=False,
    )
    result = crew.kickoff()
    print("\n--- crew.kickoff() result ---\n", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
