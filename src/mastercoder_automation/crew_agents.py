from __future__ import annotations

import json
import os

try:
    from crewai import Agent, Crew, LLM, Process, Task
except ImportError:  # pragma: no cover - exercised only without runtime dependency
    Agent = Crew = LLM = Process = Task = None  # type: ignore[assignment]

from pydantic import ValidationError

from .config import Settings
from .models import AgentDecision, ReqRecord


def _llm(settings: Settings) -> LLM:
    if LLM is None:
        raise RuntimeError("未安装 crewai，请运行：pip install -e '.[dev]'")
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
        raise ValueError(f"LLM 输出不是合法 JSON：{text[:4000]}")
    snippet = text[start : end + 1]
    try:
        payload = json.loads(snippet)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM JSON 片段无法解析：{snippet[:2000]}") from e
    try:
        return AgentDecision.model_validate(payload)
    except ValidationError as e:
        raise ValueError(f"LLM JSON 字段不符合约定（verdict/reasons）：{e}") from e


def dev_plan(req: ReqRecord, settings: Settings) -> str:
    agent = Agent(
        role="开发智能体",
        goal="为需求制定风险最小的实现计划。",
        backstory="你是资深 Python 工程师，输出确定性的实现清单。",
        llm=_llm(settings),
        verbose=False,
    )
    task = Task(
        description=(
            f"需求：{req.req_id} - {req.title}\n"
            "请输出简洁的实现清单：要改的文件、要加的测试、提交策略。"
        ),
        expected_output="简洁的 Markdown 清单。",
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
        role="审查智能体",
        goal="根据客观门禁输出给出严格的审查结论。",
        backstory="你审查代码质量，对不确定或失败的变更一律拒绝。",
        llm=_llm(settings),
        verbose=False,
    )
    task = Task(
        description=(
            f"需求：{req.req_id} - {req.title}\n"
            "根据下方门禁输出，仅返回 JSON（字段名与取值必须英文如下）：\n"
            '{"verdict":"APPROVED|REJECTED","reasons":["..."]}\n'
            f"门禁输出：\n{gate_output[:10000]}"
        ),
        expected_output='严格 JSON：{"verdict":"APPROVED|REJECTED","reasons":["..."]}',
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
        role="测试智能体",
        goal="结合验收标准与门禁证据给出严格的 QA 结论。",
        backstory="你一丝不苟，仅当验收满足时才通过。",
        llm=_llm(settings),
        verbose=False,
    )
    task = Task(
        description=(
            f"需求：{req.req_id} - {req.title}\n"
            "根据下方门禁输出，仅返回 JSON（字段名与取值必须英文如下）：\n"
            '{"verdict":"QA_PASSED|QA_FAILED","reasons":["..."]}\n'
            f"门禁输出：\n{gate_output[:10000]}"
        ),
        expected_output='严格 JSON：{"verdict":"QA_PASSED|QA_FAILED","reasons":["..."]}',
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
