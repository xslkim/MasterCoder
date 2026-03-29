# MasterCoder 全自动开发框架 — 详细教程

本文说明如何在本仓库中，使用 **CrewAI + LLM（OpenAI 兼容，例如智谱 GLM）+ Git/GitHub**，跑通从需求状态到 **改代码、门禁、Pull Request、多账号 Review/QA、合并** 的自动化流水线。

---

## 0. 开跑清单（第一次全自动跑通前逐项确认）

1. **安全**：`.env.sh` 仅本机使用、已加入 `.gitignore`；**勿**把 PAT/API Key 贴进 Issue、聊天或提交进 Git。若曾误传，请到 GitHub / 智谱 **吊销并轮换** 密钥。
2. **软件**：`python3` ≥ 3.10、`git`、`gh` 已安装；在项目根执行 `python3 -m pip install -e ".[dev]"`。
3. **Shell 环境**：在项目根执行 `source .env.sh`，并显式设置：
   - `export REPO_ROOT="$(pwd)"`（必须为你要自动改的 **同一 Git 克隆根目录**）
   - `export GITHUB_REPO="owner/repo"`（与 `origin` 远程仓库一致）
4. **三账号 PAT**：已配置并 **export** `GIT_AGENT_TOKEN_DEV` / `REVIEW` / `TEST`，且 `GIT_AGENT_USERNAME_REVIEW`、`GIT_AGENT_USERNAME_TEST` 为对应账号的 **GitHub login**（严格人审轮询靠 login 匹配）。
5. **LLM**：`OPENAI_API_KEY`、`OPENAI_API_BASE_URL`、`MODEL_NAME`；建议推理模型设 `export LLM_MAX_TOKENS=2048`（可按需调整）。
6. **状态文件**：`cp state/req-status.example.json state/req-status.json` 后编辑；把要跑的 REQ 设为 `READY`，`blocked_by` 与 `docs/requirements.md` 一致。
7. **可选严格真人**：需要「人在 GitHub 上点 Approve / 手写 QA」时：
   - `export AUTOMATION_STRICT_HUMAN_REVIEW=1` 和/或 `export AUTOMATION_STRICT_HUMAN_QA=1`
   - 适当加大 `AUTOMATION_HUMAN_POLL_TIMEOUT_SEC`（默认 3600 秒）
8. **合并权限**：`gh pr merge` 默认使用 `GIT_AGENT_TOKEN_MERGE`，否则使用 **Dev** PAT；该 PAT 必须有权合并（或关闭分支保护上的限制）。
9. **冒烟（强烈建议）**：
   - `python3 scripts/crewai_glm_smoke.py`
   - `python3 scripts/crewai_github_pat_smoke.py`
10. **正式跑（推荐整项目）**：在项目根执行 **`./run-automation.sh`** — 默认 **不跑冒烟**，执行 **`mc-auto run-all`**：循环 `run-once`，直到状态文件里 **没有** `READY`/`FIXING`（或达到 `AUTOMATION_MAX_ROUNDS` / `--max-rounds`）。只推进一条需求：`./run-automation.sh REQ-01`。只跑一轮：`./run-automation.sh --once`。
11. **边界**：一轮 `run-once` 推进 **一个** REQ 的一次「从 Dev 到 merge 的整段尝试」；`run-all` 会多轮调用直到队列空。**Resume**：若某 REQ 停在 `REVIEWING`/`TESTING`/`DEVELOPING` 等非 `READY|FIXING`，当前 `run-all --req-id` 会提示停住（需手工修状态或扩展编排器）。

**风险提醒**：Dev Agent 会在 `REPO_ROOT` 内 **checkout 分支、写文件、`git push`**；请保证工作区无未保存的重要修改，或使用独立克隆专门跑自动化。

---

## 1. 架构速览

```
state/req-status.json (REQ 状态)
        │
        ▼
 mc-auto run-once  ──► Orchestrator
        │
        ├── DEVELOPING: run_dev_implementation_crew()
        │       └── CrewAI Dev Agent + Tools:
        │             repo 读写 / git / 本地门禁 / push / gh pr create
        │             （使用 GIT_AGENT_TOKEN_DEV）
        │
        ├── 编排器再跑 run_quality_gates(cwd=REPO_ROOT)
        │       └── 失败 → FIXING / BLOCKED（重试有上限）
        │
        ├── REVIEWING（二选一，见下文「多账号 Review」）
        │       • 默认：先做 `review_decision()` 代码审查，再做“测试用例审查”；两者都通过后，才会 `gh pr review`
        │         **使用 GIT_AGENT_TOKEN_REVIEW** 提交 Approve / Request changes
        │       • 严格真人：`AUTOMATION_STRICT_HUMAN_REVIEW=1` → **轮询**直到 `GIT_AGENT_USERNAME_REVIEW`
        │         在 GitHub 上给出 Approve / Request changes；该审查应同时覆盖代码与测试用例
        │
        ├── TESTING（二选一）
        │       • 默认：`qa_decision()`（LLM）→ `gh pr comment` **使用 GIT_AGENT_TOKEN_TEST** 发 QA_PASSED / QA_FAILED
        │       • 严格真人：`AUTOMATION_STRICT_HUMAN_QA=1` → **轮询**直到该登录用户在 PR 下评论以 `QA_PASSED` 或 `QA_FAILED` 开头
        │
        └── DONE: `gh pr merge`（默认使用 `GIT_AGENT_TOKEN_MERGE`，未设置则用 `GIT_AGENT_TOKEN_DEV`）
```

**设计要点（与 `docs/dev-guide.md` 对齐的部分）**

- 客观门槛：`ruff` + `pytest` + 覆盖率下限（默认 80%）。
- 流程阶段名：PENDING → READY → DEVELOPING → REVIEWING → TESTING → DONE / FIXING / BLOCKED。
- 新规则：测试工程师写完测试用例后，必须先经过 Review 工程师审核，REQ 才能进入 `TESTING`。
- Dev 侧鼓励：**门禁 PASS 后再 push 与开 PR**（任务说明 + 编排器二次跑门禁）。

**与 `docs/teams.md` 的对齐方式**

| 角色 | GitHub 身份（PAT） | 行为 |
|------|-------------------|------|
| 开发 | `GIT_AGENT_TOKEN_DEV` | 改代码、push、创建 PR（Crew 工具链） |
| Review | `GIT_AGENT_TOKEN_REVIEW` | **默认**：由 LLM 决定结论后，用该 PAT 执行 `gh pr review`（Approve / Request changes），**GitHub 上显示为 Review 账号** |
| Review（严格真人） | 同上 PAT 轮询（可读 PR 状态） | 设 `AUTOMATION_STRICT_HUMAN_REVIEW=1`：**不调用** LLM 写 review；流水线 **阻塞等待** Review 账号在网页或 `gh` 上操作 |
| 测试 | `GIT_AGENT_TOKEN_TEST` | **默认**：LLM 结论后，用该 PAT 发 PR 评论（`QA_*`） |
| 测试（严格真人） | 轮询 PR Issue 评论 | 设 `AUTOMATION_STRICT_HUMAN_QA=1`：等待 Test 账号发评论，**正文需以 `QA_PASSED` 或 `QA_FAILED` 开头** |
| 合并 | `GIT_AGENT_TOKEN_MERGE` 或 `GIT_AGENT_TOKEN_DEV` | `gh pr merge` |

轮询间隔与超时：`AUTOMATION_HUMAN_POLL_INTERVAL_SEC`（默认 30）、`AUTOMATION_HUMAN_POLL_TIMEOUT_SEC`（默认 3600）。超时将 `REQ` 置为 **BLOCKED**。

---

## 2. 前置条件

### 2.1 软件

- **Python** 3.10+（与 `pyproject.toml` 一致）。
- **Git**。
- **GitHub CLI (`gh`)**（开 PR、合并时会调用）。
- 已安装本仓库：`pip install -e ".[dev]"`（包含 `crewai`、`pytest`、`ruff` 等）。

### 2.2 账号与权限

- **LLM**：任意 **OpenAI 兼容** API（本文假设智谱：`OPENAI_API_BASE_URL` + `OPENAI_API_KEY` + `MODEL_NAME`）。
- **开发自动化**：`GIT_AGENT_TOKEN_DEV`（classic PAT 或 fine-grained，需对目标仓库有 **push、开 PR** 等权限；与团队文档一致建议使用 `repo` 或等价范围）。
- **合并**：执行 `mc-auto` 的环境里，`gh` 需能对该仓库执行 `pr merge`（本机可用 `gh auth login`，CI 需 `GITHUB_TOKEN` 权限足够或使用 PAT）。

### 2.3 仓库状态

- `state/req-status.json` 存在且与你要跑的 REQ 一致（可从 `state/req-status.example.json` 复制后改）。
- **`REPO_ROOT`** 指向**真正的 Git 工作副本**（默认当前目录；建议在项目根 `export REPO_ROOT=$(pwd)`）。

---

## 3. 环境变量一览

在 `.env.sh` 或 shell 中配置（**勿把密钥提交进 Git**；`.env.sh` 已在 `.gitignore` 中）。

### 3.1 LLM（CrewAI）

| 变量 | 说明 |
|------|------|
| `OPENAI_API_KEY` | 智谱等兼容服务的 API Key |
| `OPENAI_API_BASE_URL` | 例如 `https://open.bigmodel.cn/api/paas/v4` |
| `MODEL_NAME` | 控制台中的模型编码，如 `glm-4.7` |
| `LLM_MAX_TOKENS` | 可选，默认 `512`（推理模型可适当加大） |

### 3.2 编排与仓库

| 变量 | 说明 |
|------|------|
| `GITHUB_REPO` | `owner/repo`，如 `xslkim/MasterCoder` |
| `REPO_ROOT` | 自动化操作的 Git 根目录，默认 `.` 的绝对路径 |
| `STATE_FILE` | 状态文件路径，默认 `state/req-status.json` |
| `COVERAGE_MIN` | 覆盖率阈值，默认 `80` |

### 3.3 Dev Agent（Git 作者 + GitHub 推送/开 PR）

| 变量 | 说明 |
|------|------|
| `GIT_AGENT_TOKEN_DEV` | Dev PAT；用于 `git push`（HTTPS token）与 `gh pr create` |
| `GIT_AGENT_USERNAME_DEV` | 建议为 **GitHub 登录名**（用于 commit `user.name`） |
| `GIT_AGENT_EMAIL_DEV` | Commit `user.email` |

### 3.4 Review / Test 账号（`mc-auto` 主编排器）

| 变量 | 说明 |
|------|------|
| `GIT_AGENT_TOKEN_REVIEW` | **必填**（非严格真人 Review 时）：用 Review 账号代为提交 `gh pr review` |
| `GIT_AGENT_USERNAME_REVIEW` | Review 账号的 **GitHub login**（严格真人模式下用于匹配 `gh pr view` 中的 reviewer） |
| `GIT_AGENT_TOKEN_TEST` | **必填**（非严格真人 QA 时）：用 Test 账号发 PR 评论 |
| `GIT_AGENT_USERNAME_TEST` | Test 账号 **GitHub login**（严格真人 QA 时用于匹配评论作者） |
| `GIT_AGENT_TOKEN_MERGE` | 可选；合并 PR 时优先使用，否则回退到 `GIT_AGENT_TOKEN_DEV` |
| `AUTOMATION_STRICT_HUMAN_REVIEW` | 设 `1` / `true`：仅等待真人（或该账号在任意客户端提交的）Review |
| `AUTOMATION_STRICT_HUMAN_QA` | 设 `1` / `true`：仅等待 Test 账号评论 `QA_PASSED` 或 `QA_FAILED` |
| `AUTOMATION_HUMAN_POLL_INTERVAL_SEC` | 轮询间隔秒数，默认 `30` |
| `AUTOMATION_HUMAN_POLL_TIMEOUT_SEC` | 轮询超时秒数，默认 `3600` |

脚本 `scripts/crewai_github_pat_smoke.py` 仍可用于三 PAT 连通性测试。

---

## 4. 本地安装与初始化

```bash
cd /path/to/MasterCoder
python3 -m pip install -U pip
python3 -m pip install -e ".[dev]"

# 准备环境与状态文件
source .env.sh
export REPO_ROOT="$(pwd)"   # 建议在项目根执行

mc-auto init-state   # 若尚无 state/req-status.json；或手动 copy example 后编辑
```

编辑 `state/req-status.json`：

- 为当前要交付的 REQ 设 `state: "READY"`（或依赖满足后由编排器从 `PENDING` 抬到 `READY`）。
- `blocked_by` 填入上游 REQ id 列表（与 `docs/requirements.md` 依赖一致）。
- 可留空 `branch`、`pr_number`，由流程填充。

确认 `gh` 能访问仓库（合并步骤需要）：

```bash
gh auth status
```

---

## 5. 冒烟测试（强烈建议在第一次全量跑之前做）

### 5.1 LLM + CrewAI

```bash
source .env.sh
python3 scripts/crewai_glm_smoke.py
```

期望：输出含 `pong`，退出码 0。

### 5.2 三个 PAT 与 GitHub API

```bash
source .env.sh
python3 scripts/crewai_github_pat_smoke.py
```

期望：三行 `DEV/REVIEW/TEST: OK api_login=...`，退出码 0（仅表示 **令牌有效**，不要求 `GIT_AGENT_USERNAME_*` 与 login 一致）。

---

## 6. 运行全链路：`mc-auto run-once`

对**单个** REQ 定向执行（推荐首次使用）：

```bash
cd "$REPO_ROOT"
source /path/to/.env.sh
export REPO_ROOT="$(pwd)"

mc-auto run-once --req-id REQ-01
```

不按 ID、自动挑第一个 `READY`/`FIXING`：

```bash
mc-auto run-once
```

**单次 `run-once` 在一次进程中可能完成：**

1. Dev Crew：拉 main、建分支、`repo_write_file` 等、`git commit`、工具内门禁、push、`gh pr create`（或仅本地提交，由编排器兜底 push/PR）。
2. 编排器再次跑门禁。
3. LLM Review / QA（基于门禁日志）。
4. 若全通过：`gh pr merge`（需权限）。

失败时：`retries` 递增，状态回到 `FIXING`（未超 `max_retries`）或 `BLOCKED`。

---

## 7. 状态文件与 REQ 依赖

- 状态机逻辑见 `src/mastercoder_automation/orchestrator.py`。
- `blocked_by` 中列出的 REQ 全部 `DONE` 后，`PENDING` 才会变 `READY`。
- `docs/requirements.md` **不会**自动同步到 `state/req-status.json`；大规模使用时建议后续加生成脚本或手工维护。

---

## 8. 关键源码入口（自助排查）

| 模块 | 作用 |
|------|------|
| `src/mastercoder_automation/dev_crew.py` | Dev Agent + 工具列表与任务说明 |
| `src/mastercoder_automation/repo_ops.py` | 安全路径、git、push、PR 创建 |
| `src/mastercoder_automation/gates.py` | `ruff` + `pytest` + coverage |
| `src/mastercoder_automation/crew_agents.py` | Review/QA 的 LLM JSON verdict（非严格真人时） |
| `src/mastercoder_automation/pr_human_gate.py` | 严格真人模式下轮询 PR Review / Issue 评论 |
| `src/mastercoder_automation/gh_client.py` | `gh pr review` / `comment` / `merge`（可带各账号 PAT） |

---

## 9. GitHub Actions（可选）

工作流：`.github/workflows/automation-pipeline.yml`。

**要在 CI 里真正跑通 Dev 改代码 + push + PR，你通常还需要：**

- `secrets.OPENAI_API_KEY`；若用智谱，增加向工作流注入 `OPENAI_API_BASE_URL`（例如 `secrets` 或 `vars`）。
- `secrets` 中存放 **`GIT_AGENT_TOKEN_DEV`**，以及 **`GIT_AGENT_TOKEN_REVIEW`**、**`GIT_AGENT_TOKEN_TEST`**（与本地多账号流程一致）；可选 `GIT_AGENT_TOKEN_MERGE`。
- 严格真人 Review/QA 时：在仓库 **Variables** 中设 `AUTOMATION_STRICT_HUMAN_REVIEW`、`AUTOMATION_STRICT_HUMAN_QA`（及 `GIT_AGENT_USERNAME_*`，若未在 vars 中配置）。
- `GITHUB_TOKEN` 默认权限可能不足以 `push` 到同一仓库的新分支或合并 PR；常需调高 workflow **permissions** 或使用 PAT。
- 定时 `cron` 每 30 分钟跑一次，适合「无人值守轮询」；也可用 `workflow_dispatch` 手动带 `req_id`。
- 「提交回写 `state/req-status.json`」的步骤依赖 `git push` 权限；裸 `GITHUB_TOKEN` 在 fork/保护分支场景易失败，需按仓库策略调整。

**结论：Actions 文件是起点模板；上生产前请按你的组织安全策略补全 Secret 与 `permissions`。**（脚本里 `vars.MODEL_NAME ||` 一类表达式在不同 GHA 版本表现不一，建议在 `run:` 里用 shell 默认值：`MODEL_NAME="${MODEL_NAME:-glm-4.7}"`。）

---

## 10. 是否可以「全自动开始软件开发」？——评审结论

### 已具备（可用于自动跑需求）

- Dev：**真实改仓库**（写文件、`git`、本地门禁、push、开 PR），并使用 **Dev PAT**。
- **多账号 Review / QA（默认）**：LLM 仅生成结论文案；**Approve / Request changes、QA 评论**分别通过 **`GIT_AGENT_TOKEN_REVIEW`**、**`GIT_AGENT_TOKEN_TEST`** 调用 `gh`，GitHub 上可见为不同账号。
- **严格真人模式**：可关闭 Review/QA 的 LLM 裁决，改为 **阻塞轮询** GitHub 上真实操作（见 §1、§3.4）。
- 客观质量：**ruff + pytest + 覆盖率**，且编排器在 **`REPO_ROOT`** 下执行。
- 流程：**单 REQ 从 READY 推进到 DONE**（末尾 **自动 merge**；可通过分支策略或去掉 merge 调用来改为仅留 PR）。
- 状态持久化：**JSON 状态文件**可反复 `run-once`。

### 仍需你知情或补强（生产级）

1. **`gh merge` 权限**：合并账号的 PAT（或 `GIT_AGENT_TOKEN_MERGE`）需有足够权限；分支保护若要求「指定 Reviewer」须与严格真人或 Review 账号规则一致。
2. **LLM 不确定性（默认模式）**：Review 文案由模型生成，仅 **执行身份** 为 Review 账号；若需「观点也必须来自人类」，请打开 **`AUTOMATION_STRICT_HUMAN_REVIEW`**（及 QA 同理）。
3. **大需求**：单次 Crew 可能吞不下复杂 REQ；需拆分 REQ 或多轮 `FIXING`。
4. **GitHub Actions**：需补全各 PAT Secret、`permissions`、智谱 `BASE_URL` 等。

**总结**：已支持 **与 `docs/teams.md` 对齐的三 PAT 流程**；再叠加严格环境变量即可收紧为 **人工 Code Review / 人工 QA 闸门**。

---

## 11. 故障排查简表

| 现象 | 可能原因 |
|------|----------|
| Crew 能说话但不改文件 | 未设置 `REPO_ROOT` 或路径不对 |
| `git push` 失败 | `GIT_AGENT_TOKEN_DEV` 缺失、过期或权限不足 |
| `gh pr create` 失败 | 同上；或未安装 `gh` |
| 门禁失败 | `src/`、`tests/` 与 `gates.py` 中路径不一致；需在仓库内补齐测试 |
| Review 一直 REJECTED | LLM 保守；查看 gate 日志；或调高 `LLM_MAX_TOKENS`；或改用人审 `AUTOMATION_STRICT_HUMAN_REVIEW` |
| 严格人审一直卡住 | Review 未在超时内 Approve；或 `GIT_AGENT_USERNAME_REVIEW` 与 GitHub login 不一致 |
| QA 轮询超时 | Test 账号评论未以 `QA_PASSED` / `QA_FAILED` 开头；或 login 配置错误 |
| `GIT_AGENT_TOKEN_REVIEW` 报错 | Secret 缺失/无 `pull_requests: write` 等价权限 |
| merge 失败 | 合并用 PAT 无权限；分支保护规则要求额外 Review |

---

## 12. 相关文档

- 产品：`docs/product-spec.md`
- 需求与顺序：`docs/requirements.md`
- 团队与账号角色：`docs/teams.md`
- Agent 流程与门禁命令：`docs/dev-guide.md`

---

*文档版本：与仓库内自动化代码同步撰写；随 `src/mastercoder_automation/` 变更请更新本节。*
