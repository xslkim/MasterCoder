#!/usr/bin/env python3
"""Minimal CrewAI smoke test: one Agent, one Task, GLM via OpenAI-compatible API.

Run:
  cd /path/to/MasterCoder
  source .env.sh
  python3 scripts/crewai_glm_smoke.py

Requires: OPENAI_API_KEY, OPENAI_API_BASE_URL, MODEL_NAME (same as .env.sh for 智谱 GLM).
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    # Avoid interactive tracing prompt + stdin issues in headless runs
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

    from crewai import Agent, Crew, LLM, Process, Task

    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    base_url = (os.environ.get("OPENAI_API_BASE_URL") or "").strip().rstrip("/")
    model = (os.environ.get("MODEL_NAME") or "").strip()

    if not api_key:
        print("error: OPENAI_API_KEY is not set (source .env.sh first)", file=sys.stderr)
        return 1
    if not base_url:
        base_url = "https://open.bigmodel.cn/api/paas/v4"
    if not model:
        print("error: MODEL_NAME is not set", file=sys.stderr)
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
