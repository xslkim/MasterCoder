from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ReqState(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    DEVELOPING = "DEVELOPING"
    REVIEWING = "REVIEWING"
    TESTING = "TESTING"
    FIXING = "FIXING"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


class ReqRecord(BaseModel):
    req_id: str
    title: str
    blocked_by: list[str] = Field(default_factory=list)
    state: ReqState = ReqState.PENDING
    retries: int = 0
    max_retries: int = 3
    branch: str | None = None
    pr_number: int | None = None
    last_error: str | None = None


class PipelineState(BaseModel):
    requirements: list[ReqRecord]


class AgentDecision(BaseModel):
    verdict: Literal["APPROVED", "REJECTED", "QA_PASSED", "QA_FAILED"]
    reasons: list[str] = Field(default_factory=list)

