from __future__ import annotations

import os
from dataclasses import dataclass

from .config import Settings
from .crew_agents import qa_decision, review_decision
from .dev_crew import run_dev_implementation_crew
from .gates import run_quality_gates
from .gh_client import GhClient
from .models import PipelineState, ReqRecord, ReqState
from .pr_human_gate import poll_human_pr_qa, poll_human_pr_review
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
            if req.pr_number is None:
                self._retry_or_block(req, "no PR number after develop step")
                return

            req.state = ReqState.REVIEWING
            review_token = (os.environ.get("GIT_AGENT_TOKEN_REVIEW") or "").strip()
            review_login = (os.environ.get("GIT_AGENT_USERNAME_REVIEW") or "").strip()
            test_token = (os.environ.get("GIT_AGENT_TOKEN_TEST") or "").strip()
            test_login = (os.environ.get("GIT_AGENT_USERNAME_TEST") or "").strip()

            if self.settings.strict_human_review:
                if not review_token or not review_login:
                    self._retry_or_block(
                        req,
                        "AUTOMATION_STRICT_HUMAN_REVIEW requires GIT_AGENT_TOKEN_REVIEW and "
                        "GIT_AGENT_USERNAME_REVIEW (GitHub login of reviewer)",
                    )
                    return
                verdict = poll_human_pr_review(
                    self.settings.github_repo,
                    req.pr_number,
                    review_login,
                    review_token,
                    interval_sec=self.settings.human_poll_interval_sec,
                    timeout_sec=self.settings.human_poll_timeout_sec,
                )
                if verdict == "TIMEOUT":
                    req.state = ReqState.BLOCKED
                    req.last_error = (
                        f"Timed out waiting for APPROVED/CHANGES_REQUESTED from {review_login} "
                        f"({self.settings.human_poll_timeout_sec}s)"
                    )
                    return
                if verdict == "CHANGES_REQUESTED":
                    self._retry_or_block(
                        req,
                        f"GitHub review from {review_login}: CHANGES_REQUESTED",
                    )
                    return
            else:
                if not review_token:
                    self._retry_or_block(
                        req,
                        "GIT_AGENT_TOKEN_REVIEW is required to post review as the Review account",
                    )
                    return
                review = review_decision(req, gate.output, self.settings)
                body = "[Review Agent — LLM summary]\n" + "\n".join(review.reasons)
                if review.verdict == "APPROVED":
                    self.gh.approve_pr(req.pr_number, body, gh_token=review_token)
                else:
                    self.gh.request_changes(req.pr_number, body, gh_token=review_token)
                    self._retry_or_block(req, "Review rejected: " + "\n".join(review.reasons))
                    return

            req.state = ReqState.TESTING
            if self.settings.strict_human_qa:
                if not test_token or not test_login:
                    self._retry_or_block(
                        req,
                        "AUTOMATION_STRICT_HUMAN_QA requires GIT_AGENT_TOKEN_TEST and "
                        "GIT_AGENT_USERNAME_TEST (GitHub login); comment must start with "
                        "QA_PASSED or QA_FAILED",
                    )
                    return
                qa_verdict = poll_human_pr_qa(
                    self.settings.github_repo,
                    req.pr_number,
                    test_login,
                    test_token,
                    interval_sec=self.settings.human_poll_interval_sec,
                    timeout_sec=self.settings.human_poll_timeout_sec,
                )
                if qa_verdict == "TIMEOUT":
                    req.state = ReqState.BLOCKED
                    req.last_error = (
                        f"Timed out waiting for QA comment from {test_login} "
                        f"({self.settings.human_poll_timeout_sec}s)"
                    )
                    return
                if qa_verdict == "QA_FAILED":
                    self._retry_or_block(
                        req,
                        f"Test account {test_login} commented QA_FAILED on PR #{req.pr_number}",
                    )
                    return
            else:
                if not test_token:
                    self._retry_or_block(
                        req,
                        "GIT_AGENT_TOKEN_TEST is required to post QA comment as the Test account",
                    )
                    return
                qa = qa_decision(req, gate.output, self.settings)
                body = f"{qa.verdict}\n\n" + "\n".join(qa.reasons)
                self.gh.comment_pr(req.pr_number, body, gh_token=test_token)
                if qa.verdict == "QA_FAILED":
                    self._retry_or_block(req, "\n".join(qa.reasons))
                    return

            req.state = ReqState.DONE
            merge_tok = (
                (os.environ.get("GIT_AGENT_TOKEN_MERGE") or "").strip()
                or (os.environ.get("GIT_AGENT_TOKEN_DEV") or "").strip()
                or None
            )
            if req.pr_number:
                self.gh.merge_pr(req.pr_number, gh_token=merge_tok)

    def _retry_or_block(self, req: ReqRecord, reason: str) -> None:
        req.retries += 1
        req.last_error = reason[:2000]
        if req.retries > req.max_retries:
            req.state = ReqState.BLOCKED
        else:
            req.state = ReqState.FIXING

