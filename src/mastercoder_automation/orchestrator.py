from __future__ import annotations

import os
from dataclasses import dataclass

from .config import Settings
from .crew_agents import qa_decision, review_decision
from .dev_crew import run_dev_implementation_crew
from .gates import run_quality_gates
from .gh_client import GhClient
from .models import PipelineState, ReqRecord, ReqState
from .repo_ops import branch_slug, gh_pr_create_json, git_push_https
from .state_store import StateStore


@dataclass
class Orchestrator:
    settings: Settings
    store: StateStore
    gh: GhClient

    def run_once(self, req_id: str | None = None) -> PipelineState:
        state = self.store.load()
        self._refresh_ready(state)
        target = self._pick_target(state, req_id)
        if target is None:
            self.store.save(state)
            return state
        self._advance(target)
        self.store.save(state)
        return state

    def _refresh_ready(self, state: PipelineState) -> None:
        by_id = {req.req_id: req for req in state.requirements}
        for req in state.requirements:
            if req.state != ReqState.PENDING:
                continue
            if all(by_id[dep].state == ReqState.DONE for dep in req.blocked_by if dep in by_id):
                req.state = ReqState.READY

    def _pick_target(self, state: PipelineState, req_id: str | None) -> ReqRecord | None:
        if req_id:
            for req in state.requirements:
                if req.req_id == req_id:
                    return req
            return None
        for req in state.requirements:
            if req.state in {ReqState.READY, ReqState.FIXING}:
                return req
        return None

    def _advance(self, req: ReqRecord) -> None:
        if req.state in {ReqState.READY, ReqState.FIXING}:
            req.state = ReqState.DEVELOPING
            if not req.branch:
                req.branch = branch_slug(req)
            summary, pr_num = run_dev_implementation_crew(req, self.settings)
            if pr_num is not None:
                req.pr_number = pr_num
            gate = run_quality_gates(self.settings.coverage_min, cwd=self.settings.repo_root)
            if not gate.passed:
                self._retry_or_block(req, gate.output)
                return
            if req.pr_number is None:
                token = (os.environ.get("GIT_AGENT_TOKEN_DEV") or "").strip()
                if not token:
                    self._retry_or_block(req, "no PR from agent and GIT_AGENT_TOKEN_DEV missing")
                    return
                try:
                    git_push_https(
                        self.settings.repo_root,
                        req.branch,
                        token,
                        self.settings.github_repo,
                    )
                    req.pr_number = gh_pr_create_json(
                        self.settings.github_repo,
                        req.branch,
                        f"[{req.req_id}] {req.title}",
                        f"Automated PR for {req.req_id}.\n\n---\n{summary[:6000]}",
                        token,
                    )
                except Exception as e:
                    self._retry_or_block(req, f"push/pr fallback failed: {e}")
                    return
            req.state = ReqState.REVIEWING
            review = review_decision(req, gate.output, self.settings)
            if review.verdict == "REJECTED":
                self._retry_or_block(req, "\n".join(review.reasons))
                return
            req.state = ReqState.TESTING
            qa = qa_decision(req, gate.output, self.settings)
            if qa.verdict == "QA_FAILED":
                self._retry_or_block(req, "\n".join(qa.reasons))
                return
            req.state = ReqState.DONE
            if req.pr_number:
                self.gh.merge_pr(req.pr_number)

    def _retry_or_block(self, req: ReqRecord, reason: str) -> None:
        req.retries += 1
        req.last_error = reason[:2000]
        if req.retries > req.max_retries:
            req.state = ReqState.BLOCKED
        else:
            req.state = ReqState.FIXING

