# MasterCoder 全自动开发框架 — 详细教程

本文说明如何在本仓库中，使用 **CrewAI + LLM（OpenAI 兼容，例如智谱 GLM）+ Git/GitHub**，跑通从需求状态到 **改代码、门禁、Pull Request、合并** 的自动化流水线；并诚实列出**当前已具备的能力**与**尚未完全对标文档（三独立 GitHub 账号）的部分**。

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
        ├── REVIEWING: review_decision() — CrewAI + LLM，基于门禁输出给 APPROVED/REJECTED
        │
        ├── TESTING: qa_decision() — CrewAI + LLM，给 QA_PASSED/QA_FAILED
        │
        └── DONE: gh pr merge（GhClient，依赖本机/C CI 的 gh 认证）
```

**设计要点（与 `docs/dev-guide.md` 对齐的部分）**

- 客观门槛：`ruff` + `pytest` + 覆盖率下限（默认 80%）。
- 流程阶段名：PENDING → READY → DEVELOPING → REVIEWING → TESTING → DONE / FIXING / BLOCKED。
- Dev 侧鼓励：**门禁 PASS 后再 push 与开 PR**（任务说明 + 编排器二次跑门禁）。

**与 `docs/dev-guide.md` / `docs/teams.md` 的差异（务必读）**

| 文档设想 | 当前代码实现 |
|----------|--------------|
| 开发 / Review / 测试 **三个 GitHub 账号** 分别在 PR 上 Approve、Comment | **合并与 PR 操作主要走配置里的仓库与 Dev PAT**；Review / QA 是 **同一进程内的 LLM 角色**，**不会**自动用 Review/Test 账号登录 `gh` 去点 Approve |
| 多人轮次、人工仲裁 | 单次 `run-once` 会在**一次执行中**尽量把某个 REQ 推到 DONE（若全程成功会直接 `merge`） |

因此：**可以称为「高度自动化的开发流水线」**；若你严格要求 **「必须由第二个账号在 GitHub UI 上 Approve」**，还需要在编排器外接 **PR Webhook / 另一 job** 或扩展 `GhClient` 使用 `GIT_AGENT_TOKEN_REVIEW` 调用 `gh pr review`。

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

可选：Review/Test 的变量仍可用于 **脚本** `scripts/crewai_github_pat_smoke.py` 做连通性测试；**主编排器 `mc-auto` 当前不会用 Review/Test token 做 Approve。**

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
| `src/mastercoder_automation/crew_agents.py` | Review/QA 的 LLM JSON  verdict |
| `src/mastercoder_automation/gh_client.py` | `gh pr merge` 等（需环境认证） |

---

## 9. GitHub Actions（可选）

工作流：`.github/workflows/automation-pipeline.yml`。

**要在 CI 里真正跑通 Dev 改代码 + push + PR，你通常还需要：**

- `secrets.OPENAI_API_KEY`；若用智谱，增加向工作流注入 `OPENAI_API_BASE_URL`（例如 `secrets` 或 `vars`）。
- `secrets` 中存放 **`GIT_AGENT_TOKEN_DEV`**，并在 `Run deterministic orchestrator` 的 `env` 里导出。
- `GITHUB_TOKEN` 默认权限可能不足以 `push` 到同一仓库的新分支或合并 PR；常需调高 workflow **permissions** 或使用 PAT。
- 定时 `cron` 每 30 分钟跑一次，适合「无人值守轮询」；也可用 `workflow_dispatch` 手动带 `req_id`。
- 「提交回写 `state/req-status.json`」的步骤依赖 `git push` 权限；裸 `GITHUB_TOKEN` 在 fork/保护分支场景易失败，需按仓库策略调整。

**结论：Actions 文件是起点模板；上生产前请按你的组织安全策略补全 Secret 与 `permissions`。**（脚本里 `vars.MODEL_NAME ||` 一类表达式在不同 GHA 版本表现不一，建议在 `run:` 里用 shell 默认值：`MODEL_NAME="${MODEL_NAME:-glm-4.7}"`。）

---

## 10. 是否可以「全自动开始软件开发」？——评审结论

### 已具备（可用于自动跑需求）

- Dev：**真实改仓库**（写文件、`git`、本地门禁、push、开 PR），并使用 **Dev PAT**。
- 客观质量：**ruff + pytest + 覆盖率**，且编排器在 **`REPO_ROOT`** 下执行。
- 流程：**单 REQ 从 READY 推进到 DONE**（含 LLM Review/QA 与 **自动 merge** 的代码路径）。
- 状态持久化：**JSON 状态文件**可反复 `run-once`（配合 CI 或本机定时任务即「无人值守」雏形）。

### 仍需你知情或补强（生产级）

1. **Review/Test GitHub 账号**：文档中的「第二个账号 Approve、第三个 Comment」**尚未**接入主编排器；当前 Review/QA 是 **LLM 基于日志的 verdict**。若合规要求真人或第二账号，请扩展 `gh pr review`。
2. **`gh merge` 权限**：本机/CI 必须配置正确，否则会在最后一步失败。
3. **LLM 不确定性**：即使门禁通过，仍应保留团队 Code Review；可把 `merge` 改为「仅开 PR、不自动合并」。
4. **大需求**：单次 Crew 任务可能无法一次完成复杂 REQ；需人工拆分 REQ 或多次 `FIXING` 循环。
5. **GitHub Actions**：需补 Secret、`permissions`、智谱 `BASE_URL`，否则会与本地行为不一致。

**总结**：**从工程上已经具备「自动写代码 + 门禁 + PR +（可选）合并」的主干**；是否算你们内部的「正式上线全自动」，取决于是否必须 **真实多账号 PR 审批** 以及是否 **关闭自动 merge**。建议先用 `--req-id` 在小 REQ 上试跑，再打开定时调度。

---

## 11. 故障排查简表

| 现象 | 可能原因 |
|------|----------|
| Crew 能说话但不改文件 | 未设置 `REPO_ROOT` 或路径不对 |
| `git push` 失败 | `GIT_AGENT_TOKEN_DEV` 缺失、过期或权限不足 |
| `gh pr create` 失败 | 同上；或未安装 `gh` |
| 门禁失败 | `src/`、`tests/` 与 `gates.py` 中路径不一致；需在仓库内补齐测试 |
| Review 一直 REJECTED | LLM 保守；查看 gate 日志；或调高 `LLM_MAX_TOKENS` |
| merge 失败 | `gh auth` 无权限；分支保护规则要求 Review |

---

## 12. 相关文档

- 产品：`docs/product-spec.md`
- 需求与顺序：`docs/requirements.md`
- 团队与账号角色：`docs/teams.md`
- Agent 流程与门禁命令：`docs/dev-guide.md`

---

*文档版本：与仓库内自动化代码同步撰写；随 `src/mastercoder_automation/` 变更请更新本节。*
