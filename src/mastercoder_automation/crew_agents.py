from __future__ import annotations

import json
import os

try:
    from crewai import Agent, Crew, LLM, Process, Task
except ImportError:  # pragma: no cover - exercised only without runtime dependency
    Agent = Crew = LLM = Process = Task = None  # type: ignore[assignment]

from .config import Settings
from .models import AgentDecision, ReqRecord


def _llm(settings: Settings) -> LLM:
    if LLM is None:
        raise RuntimeError("crewai is not installed. Run: pip install -e '.[dev]'")
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
    kwargs: dict = {
        "model": settings.model_name,
        "temperature": 0,
        "max_tokens": settings.llm_max_tokens,
    }
    if settings.openai_api_key:
        kwargs["api_key"] = settings.openai_api_key
    if settings.openai_api_base_url:
        kwargs["base_url"] = settings.openai_api_base_url.rstrip("/")
    return LLM(**kwargs)


def _extract_json(text: str) -> AgentDecision:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"LLM output is not valid JSON: {text}")
    payload = json.loads(text[start : end + 1])
    return AgentDecision.model_validate(payload)


def dev_plan(req: ReqRecord, settings: Settings) -> str:
    agent = Agent(
        role="Development Agent",
        goal="Create an implementation plan for the requirement with minimal risk.",
        backstory="You are a senior Python engineer that produces deterministic implementation plans.",
        llm=_llm(settings),
        verbose=False,
    )
    task = Task(
        description=(
            f"Requirement: {req.req_id} - {req.title}\n"
            "Produce a concise implementation checklist: files to change, tests to add, and commit strategy."
        ),
        expected_output="A concise markdown checklist.",
        agent=agent,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        tracing=False,
    )
    return str(crew.kickoff())


def review_decision(req: ReqRecord, gate_output: str, settings: Settings) -> AgentDecision:
    agent = Agent(
        role="Review Agent",
        goal="Produce a strict review verdict from objective gate output.",
        backstory="You review code quality and reject any uncertain or failing changes.",
        llm=_llm(settings),
        verbose=False,
    )
    task = Task(
        description=(
            f"Requirement: {req.req_id} - {req.title}\n"
            "Given gate output below, return JSON only:\n"
            '{"verdict":"APPROVED|REJECTED","reasons":["..."]}\n'
            f"Gate output:\n{gate_output[:10000]}"
        ),
        expected_output='Strict JSON: {"verdict":"APPROVED|REJECTED","reasons":["..."]}',
        agent=agent,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        tracing=False,
    )
    return _extract_json(str(crew.kickoff()))


def qa_decision(req: ReqRecord, gate_output: str, settings: Settings) -> AgentDecision:
    agent = Agent(
        role="QA Agent",
        goal="Produce a strict QA verdict using acceptance and gate evidence.",
        backstory="You are meticulous and only pass requirements that meet acceptance criteria.",
        llm=_llm(settings),
        verbose=False,
    )
    task = Task(
        description=(
            f"Requirement: {req.req_id} - {req.title}\n"
            "Given gate output below, return JSON only:\n"
            '{"verdict":"QA_PASSED|QA_FAILED","reasons":["..."]}\n'
            f"Gate output:\n{gate_output[:10000]}"
        ),
        expected_output='Strict JSON: {"verdict":"QA_PASSED|QA_FAILED","reasons":["..."]}',
        agent=agent,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        tracing=False,
    )
    return _extract_json(str(crew.kickoff()))

