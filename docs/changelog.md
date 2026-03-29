# MasterCoder 开发日志

## 2026-03-28 自动化流程重构 & REQ-01~03 完成

### 今日成果

REQ-01（项目脚手架与入口程序）、REQ-02（配置系统）、REQ-03（OpenAI 兼容 API 客户端）
三个需求已全部通过自动化流水线完成开发、代码审查、QA 并合入 main 分支。

GitHub PR 记录：
- REQ-02: PR #4（合并后已关闭）
- REQ-03: PR #5（合并后已关闭）

---

### 流程重构内容

#### 1. 强制「先写测试」的硬约束

之前的自动化流程只靠 Agent prompt 建议先写测试，但 Agent 经常跳过直接写实现代码。
现在改成了流程级硬约束：

- `orchestrator._validate_req_branch()`：开发完成后强制检查分支 diff 中是否包含 `tests/` 下的变更，
  如果没有，直接进入 `FIXING` 状态并附带说明。
- 同时检查功能分支相对默认分支是否有新 commit，零 commit 也打回。

#### 2. 分支准备前置到 Orchestrator

之前「切换默认分支 + 创建功能分支」是作为 Agent 工具提供的，Agent 需要先调用两个工具。
现在改为 Orchestrator 在进入开发前直接执行，Agent 启动时已经在正确的功能分支上。

好处：
- Agent 不再需要处理分支切换的复杂性
- 避免工作区有未提交改动时分支切换失败
- 减少一轮 LLM 工具调用开销

#### 3. 恢复已有分支的捷径

如果功能分支上已经有合格的测试变更和有效提交，`_can_resume_existing_branch()` 会跳过开发 Agent，
直接进入 gates/push/PR 流程。

这解决了「Agent 代码已经写好并 commit 了，但因为某环节（如推送）失败导致状态回退到 FIXING，
重跑时不需要重新开发」的问题。

#### 4. 自动暂存排除状态文件

`git_add_all()` 现在自动排除 `state/req-status.json` 和 `.coverage`，
避免把流水线运行时的状态文件变更带进功能分支的 commit。

#### 5. 默认分支检测修正

`git_checkout_main_pull()` 之前用 try/except 在 main 和 master 之间回退，
如果 main 切换失败（比如工作区脏），会误尝试 master 并给出误导性错误。
现在改为先调用 `default_branch_name()` 确定真实默认分支名，再只操作那个分支。

#### 6. 按 REQ-ID 抽取需求片段

新增 `repo_read_requirement_section()` 和对应的 Agent 工具 `repo_read_requirement`，
可以按 REQ-ID 直接抽取 `docs/requirements.md` 中对应章节，避免 Agent 每次读取整个 1700+ 行文档。

#### 7. CrewAI verbose 模式修复（关键发现）

**CrewAI 的 `verbose=False` 模式下，Agent 完全不执行任何工具调用，直接返回空结果。**

这是一个严重影响自动化流程的问题。在 REQ-01/02 时因为碰巧被 `_can_resume_existing_branch`
跳过了开发 Agent，所以没暴露。REQ-03 是全新的空分支，无法恢复，所以彻底卡死。

修复：`dev_crew.py` 中 Crew 的 `verbose` 改为 `True`。

---

### 状态文件补齐

`state/req-status.json` 和 `state/req-status.example.json` 已从只包含 REQ-01/02 扩展到包含
全部 25 个需求（REQ-01 到 REQ-25），依赖关系按顺序串联。

当前状态：
- REQ-01: `DONE`
- REQ-02: `DONE`
- REQ-03: `DONE`
- REQ-04 到 REQ-25: `PENDING`（按 `blocked_by` 顺序等待）

---

### 文件改动清单

| 文件 | 改动内容 |
|------|---------|
| `src/mastercoder_automation/orchestrator.py` | 新增 `_prepare_req_branch`、`_can_resume_existing_branch`、`_validate_req_branch`；分支准备前置；恢复已有分支捷径 |
| `src/mastercoder_automation/dev_crew.py` | 移除 `git_update_main`/`git_use_feature_branch` 工具（前置到 orchestrator）；新增 `repo_read_requirement`/`git_changed_files_against_default`/`git_commits_ahead_of_default` 工具；`verbose=False` 改 `True`；Task description 重写为先写测试流程 |
| `src/mastercoder_automation/repo_ops.py` | 新增 `default_branch_name`、`git_current_branch`、`git_changed_files_against_default`、`git_commits_ahead_of_default`、`repo_read_requirement_section`；`git_checkout_main_pull` 改为先检测再操作；`git_add_all` 排除状态文件 |
| `state/req-status.json` | REQ-02 清理（retries=0, last_error=null）；REQ-03 设为 READY；补齐 REQ-04~25 |
| `state/req-status.example.json` | 补齐 REQ-03~25 |
| `tests/test_orchestrator.py` | 新增测试：`test_missing_test_changes_goes_to_fixing`、`test_missing_commits_goes_to_fixing`、`test_branch_prepare_failure_goes_to_fixing`、`test_prepare_branch_skips_checkout_when_already_on_target`、`test_resume_existing_branch_skips_dev_agent` |
| `tests/test_repo_ops.py` | 新增测试：`test_default_branch_name_*`、`test_git_current_branch`、`test_git_changed_files_against_default`、`test_git_commits_ahead_of_default`、`test_repo_read_requirement_section_extracts_single_req`、`test_git_checkout_main_pull_uses_detected_default_branch`、`test_git_add_all_excludes_state_and_coverage` |

---

### 已知问题 & 明天待办

1. **LLM 生成的代码质量不稳定**：REQ-03 的测试有部分失败（Agent 生成的 mock/sever 代码不够精确），
   需要在后续 REQ 中观察是否需要更强的 prompt 约束或增加代码模板。

2. **Agent 执行时间较长**：单个 REQ 的开发 Agent 大约需要 2-3 分钟完成所有工具调用，
   其中大部分时间花在 LLM 推理上。如果需要加速，可以考虑减少工具数量或优化 prompt。

3. **测试覆盖率阈值**：当前 `DEFAULT_COVERAGE_MIN = 50`，随着产品代码增多，
   可能需要调整或增加更多自动化测试来维持。

4. **REQ-04 及后续**：下一个待处理的是 REQ-04（对话消息管理器），
   依赖 REQ-03 的 OpenAI 客户端模块。流水线已准备就绪，可以直接 `./run-automation.sh --once REQ-04`。
