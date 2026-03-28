from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from . import repo_ops
from .config import Settings
from .crew_agents import qa_decision, review_decision
from .dev_crew import run_dev_implementation_crew
from .gates import run_quality_gates
from .gh_client import GhClient
from .models import PipelineState, ReqRecord, ReqState
from .pr_human_gate import poll_human_pr_qa, poll_human_pr_review
from .repo_ops import branch_slug, gh_pr_create_json, git_push_https
from .state_store import StateStore

_log = logging.getLogger(__name__)


def _format_gh_token_permission_hint(operation: str, err: str) -> str:
    """GitHub 常见 PAT 权限错误说明。"""
    low = err.lower()
    hint = ""
    if "resource not accessible" in low or "403" in err or "forbidden" in low:
        hint = (
            " 请检查 PAT：Fine-grained 须对目标仓库开启 Pull requests: Read and write；"
            "Classic PAT 须勾选 repo。该 GitHub 账号须对仓库有写权限。"
        )
    return f"{operation} {err}{hint}"


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
            if req_id is not None:
                raise ValueError(f"未找到 REQ：{req_id!r}（请检查 state 文件中的 req_id）")
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
            missing = [dep for dep in req.blocked_by if dep not in by_id]
            if missing:
                _log.warning(
                    "REQ %s 的 blocked_by 含未知依赖 %s，保持 PENDING",
                    req.req_id,
                    missing,
                )
                continue
            if req.blocked_by and all(by_id[dep].state == ReqState.DONE for dep in req.blocked_by):
                req.state = ReqState.READY
            elif not req.blocked_by:
                # 无依赖的 PENDING 不应出现（初始化应直接 READY）；若出现则视为可推进
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

    def _validate_req_branch(self, req: ReqRecord) -> str | None:
        branch = req.branch or "HEAD"
        try:
            changed_files = repo_ops.git_changed_files_against_default(
                self.settings.repo_root, branch
            )
        except Exception as e:
            return f"无法检查分支变更：{e}"
        if not any(path.startswith("tests/") for path in changed_files):
            return (
                "本轮开发未在 tests/ 下新增或修改测试文件；"
                "每个 REQ 都必须先根据需求文档编写或更新测试用例。"
            )
        try:
            commits_ahead = repo_ops.git_commits_ahead_of_default(self.settings.repo_root, branch)
        except Exception as e:
            return f"无法检查分支提交数量：{e}"
        if commits_ahead <= 0:
            return "功能分支相对默认分支没有新的 commit；请先提交测试与实现，再创建 PR。"
        return None

    def _prepare_req_branch(self, req: ReqRecord) -> str | None:
        if not req.branch:
            req.branch = branch_slug(req)
        try:
            if repo_ops.git_current_branch(self.settings.repo_root) == req.branch:
                return None
            repo_ops.git_checkout_main_pull(self.settings.repo_root)
            repo_ops.git_create_branch(self.settings.repo_root, req.branch)
        except Exception as e:
            return f"准备开发分支失败：{e}"
        return None

    def _can_resume_existing_branch(self, req: ReqRecord) -> bool:
        if not req.branch:
            return False
        try:
            if repo_ops.git_current_branch(self.settings.repo_root) != req.branch:
                return False
        except Exception:
            return False
        return self._validate_req_branch(req) is None

    def _advance(self, req: ReqRecord) -> None:
        if req.state in {ReqState.READY, ReqState.FIXING}:
            req.state = ReqState.DEVELOPING
            if self._can_resume_existing_branch(req):
                summary = (
                    "检测到当前功能分支已包含测试变更和有效提交，跳过开发 Agent，直接继续后续流程。"
                )
            else:
                branch_prep_error = self._prepare_req_branch(req)
                if branch_prep_error:
                    self._retry_or_block(req, branch_prep_error)
                    return
                summary, pr_num = run_dev_implementation_crew(req, self.settings)
                if pr_num is not None:
                    req.pr_number = pr_num
                branch_error = self._validate_req_branch(req)
                if branch_error:
                    self._retry_or_block(req, branch_error)
                    return
            gate = run_quality_gates(self.settings.coverage_min, cwd=self.settings.repo_root)
            if not gate.passed:
                self._retry_or_block(req, gate.output)
                return
            if req.pr_number is None:
                token = (os.environ.get("GIT_AGENT_TOKEN_DEV") or "").strip()
                if not token:
                    self._retry_or_block(req, "智能体未创建 PR，且未设置 GIT_AGENT_TOKEN_DEV")
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
                        f"自动化 PR：{req.req_id}。\n\n---\n{summary[:6000]}",
                        token,
                    )
                except Exception as e:
                    self._retry_or_block(req, f"推送/创建 PR 回退失败：{e}")
                    return
            if req.pr_number is None:
                self._retry_or_block(req, "开发步骤结束后仍未获得 PR 编号")
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
                        "开启 AUTOMATION_STRICT_HUMAN_REVIEW 时必须设置 GIT_AGENT_TOKEN_REVIEW 与 "
                        "GIT_AGENT_USERNAME_REVIEW（审查账号的 GitHub 登录名）",
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
                        f"等待 {review_login} 的 APPROVED/CHANGES_REQUESTED 超时 "
                        f"（{self.settings.human_poll_timeout_sec} 秒）"
                    )
                    return
                if verdict == "CHANGES_REQUESTED":
                    self._retry_or_block(
                        req,
                        f"GitHub 审查来自 {review_login}：CHANGES_REQUESTED",
                    )
                    return
            else:
                if not review_token:
                    self._retry_or_block(
                        req,
                        "需要 GIT_AGENT_TOKEN_REVIEW，以便以审查账号提交 Review",
                    )
                    return
                review = review_decision(req, gate.output, self.settings)
                body = "[审查 Agent — LLM 摘要]\n" + "\n".join(review.reasons)
                try:
                    if review.verdict == "APPROVED":
                        self.gh.approve_pr(req.pr_number, body, gh_token=review_token)
                    else:
                        self.gh.request_changes(req.pr_number, body, gh_token=review_token)
                except RuntimeError as e:
                    self._retry_or_block(
                        req,
                        _format_gh_token_permission_hint(
                            "GitHub 提交 Review（approve/request_changes）", str(e)
                        ),
                    )
                    return
                if review.verdict != "APPROVED":
                    self._retry_or_block(req, "审查未通过：" + "\n".join(review.reasons))
                    return

            req.state = ReqState.TESTING
            if self.settings.strict_human_qa:
                if not test_token or not test_login:
                    self._retry_or_block(
                        req,
                        "开启 AUTOMATION_STRICT_HUMAN_QA 时必须设置 GIT_AGENT_TOKEN_TEST 与 "
                        "GIT_AGENT_USERNAME_TEST（测试账号登录名）；评论须以 QA_PASSED 或 QA_FAILED 开头",
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
                    req.last_error = f"等待 {test_login} 的 QA 评论超时（{self.settings.human_poll_timeout_sec} 秒）"
                    return
                if qa_verdict == "QA_FAILED":
                    self._retry_or_block(
                        req,
                        f"测试账号 {test_login} 在 PR #{req.pr_number} 上评论了 QA_FAILED",
                    )
                    return
            else:
                if not test_token:
                    self._retry_or_block(
                        req,
                        "需要 GIT_AGENT_TOKEN_TEST，以便以测试账号发表 QA 评论",
                    )
                    return
                qa = qa_decision(req, gate.output, self.settings)
                body = f"{qa.verdict}\n\n" + "\n".join(qa.reasons)
                try:
                    self.gh.comment_pr(req.pr_number, body, gh_token=test_token)
                except RuntimeError as e:
                    self._retry_or_block(
                        req,
                        _format_gh_token_permission_hint("GitHub 发表 QA 评论", str(e)),
                    )
                    return
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
                try:
                    self.gh.merge_pr(req.pr_number, gh_token=merge_tok)
                except Exception as e:
                    _log.warning(
                        "合并 PR #%s 失败（可稍后在 GitHub 上手动合并）：%s",
                        req.pr_number,
                        e,
                    )

    def _retry_or_block(self, req: ReqRecord, reason: str) -> None:
        req.retries += 1
        req.last_error = reason[:2000]
        if req.retries > req.max_retries:
            req.state = ReqState.BLOCKED
        else:
            req.state = ReqState.FIXING
