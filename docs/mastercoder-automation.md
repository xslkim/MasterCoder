# mastercoder_automation：CrewAI 自动化交付说明

本文说明仓库中 **`src/mastercoder_automation/`** 的职责、设计原因、依赖关系，以及在一台**全新 Ubuntu** 上如何把 **CrewAI + 本流水线**跑起来。

---

## 1. 它是什么？和「产品代码」的区别

| 路径 | 角色 |
|------|------|
| `src/mastercoder/` | **产品**：面向用户的 MasterCoder 应用（如 CLI `mastercoder`）。 |
| `src/mastercoder_automation/` | **自动化编排**：用 **CrewAI** 驱动「读需求 → 改代码 → 跑门禁 → 推分支 → 开 PR → 审查 → QA → 合并」的工具库；入口命令是 **`mc-auto`**。 |

本目录**不**实现产品功能，而是**在同一 Git 工作区里操作** `mastercoder`、`tests/`、`docs/` 等，并把进度记在 **`state/req-status.json`**。

---

## 2. 为什么要「编排 + CrewAI」这样写？

### 2.1 确定性编排（非 LLM 部分）

- **`Orchestrator`**：按 REQ 状态机推进（`PENDING → READY → … → DONE/BLOCKED`），顺序固定，**不**把分支策略交给模型临场发挥。
- **`gates.py`**：统一跑 `ruff` + `pytest` + 覆盖率阈值；失败则进入 **`FIXING`** 或 **`BLOCKED`**，避免「没测过就合并」。
- **`repo_ops` / `gh_client`**：Git / `gh` 调用集中封装，错误信息可预期；**`gh pr create`** 兼容旧版 CLI（无 `--json` 时解析 PR URL）。

这样 **LLM 只负责「改什么」**，**「何时推、何时合并」由代码保证**。

### 2.2 CrewAI 只用在「需要推理」的环节

| 模块 | 作用 |
|------|------|
| **`dev_crew.py`** | **开发智能体**：通过 **Tool**（读文件、写文件、git、跑门禁、推分支、`gh` 开 PR）完成实现；工具名需 **英文**（OpenAI 兼容 API 对函数名有字符限制）。 |
| **`crew_agents.py`** | **审查 / QA 智能体**（非真人模式）：根据门禁日志输出 **固定 JSON**（`APPROVED`/`REJECTED`/`QA_PASSED`/`QA_FAILED`），便于程序解析。 |

**为何用 Tool 而不是让模型直接 `exec`？**  
工具封装了路径校验（防 `..`）、环境变量中的 Token、可测试的边界，比自由生成 shell 更安全、可重复。

### 2.3 与产品包同仓的原因

- 一条命令 **`pip install -e .`** 同时安装 **`mastercoder`** 与 **`mastercoder-automation`**，本地改自动化与改产品无需拆仓库。
- **`REPO_ROOT`** 指向本仓库根目录，智能体改的就是当前克隆。

---

## 3. 模块一览（按阅读顺序）

| 文件 | 职责 |
|------|------|
| **`cli.py`** | Typer 入口：`init-state`、`run-once`、`run-all`；启动前 **`preflight`** 检查 `git`/`gh`。 |
| **`config.py`** | `load_settings()`：智谱 **GLM** 默认模型与 Base URL、`OPENAI_API_KEY`、`STATE_FILE` 相对 **`REPO_ROOT`** 解析、`COVERAGE_MIN`、`LLM_MAX_TOKENS` 等。 |
| **`preflight.py`** | 检查本机是否存在 `git`、`gh`。 |
| **`models.py`** | Pydantic：`ReqRecord`、`ReqState`、`PipelineState`、`AgentDecision`。 |
| **`state_store.py`** | 读写 `state/req-status.json`。 |
| **`orchestrator.py`** | 状态机推进、门禁通过后调 GitHub 审查/QA、合并；捕获 **`gh` PAT 权限**类错误并写入 `last_error`。 |
| **`dev_crew.py`** | 构建 **CrewAI** 开发 Agent + Task + Tools，执行 `run_dev_implementation_crew`。 |
| **`crew_agents.py`** | `_llm()`、审查/QA 的 LLM 调用与 JSON 解析。 |
| **`gates.py`** | 子进程跑 `ruff` / `pytest`，带超时；失败即门禁不过。 |
| **`repo_ops.py`** | 分支名、读写文件、git、**`gh pr create`**（解析 PR 号）。 |
| **`gh_client.py`** | `gh pr review` / `comment` / `merge` 等（与 `repo_ops` 共享 PR 号解析思路）。 |
| **`pr_human_gate.py`** | 可选：**真人** Review/QA 时轮询 `gh api`。 |

---

## 4. 依赖关系

### 4.1 Python（见 `pyproject.toml`）

| 依赖 | 用途 |
|------|------|
| **crewai ≥ 0.70** | Agent / Crew / Task / LLM / Tool |
| **pydantic ≥ 2.8** | 状态与决策模型校验 |
| **typer** | `mc-auto` CLI |
| **rich** | 终端彩色输出 |

开发/测试（`pip install -e ".[dev]"`）：

| 依赖 | 用途 |
|------|------|
| **pytest** | 测试 |
| **ruff** | 格式与静态检查（门禁会跑） |

### 4.2 系统与外部工具

| 依赖 | 用途 |
|------|------|
| **Python ≥ 3.10** | 运行环境 |
| **git** | 克隆、分支、提交、推送 |
| **GitHub CLI `gh`** | 创建 PR、Review、评论、合并（API 与 PAT 通过 `GH_TOKEN` 传入子进程） |
| **智谱 / OpenAI 兼容 API** | 环境变量 **`OPENAI_API_KEY`**（Base URL 与模型名默认写在 `config.py`，可用环境变量覆盖部分项） |

### 4.3 覆盖率配置（`pyproject.toml`）

对 **`mastercoder_automation`** 跑 coverage 时 **omit** 了 `dev_crew.py`、`crew_agents.py`、`pr_human_gate.py`，避免「必须真连 LLM / 真调 `gh api`」才能凑覆盖率；**默认 `COVERAGE_MIN=50`**，严格项目可 **`export COVERAGE_MIN=80`**。

---

## 5. 全新 Ubuntu：从零跑通 CrewAI + 本流水线

以下假设你已 **clone** 本仓库到例如 `~/code/MasterCoder`。

### 5.1 系统包

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl
```

安装 **GitHub CLI**（`gh`）：

```bash
# 官方文档：https://cli.github.com/
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install -y gh
```

验证：

```bash
git --version
gh --version
python3 --version   # 需 >= 3.10
```

### 5.2 Python 依赖（可编辑安装）

```bash
cd ~/code/MasterCoder
python3 -m pip install --user pip setuptools wheel   # 若系统 pip 过旧可先升级
python3 -m pip install -e ".[dev]"
```

确认入口：

```bash
mc-auto --help
```

### 5.3 环境变量（勿提交密钥）

在项目根创建 **`.env.bash`**（或你自用的文件名），至少包含：

- **`OPENAI_API_KEY`**：智谱等兼容 API 的 Key（本仓库默认模型与 Base URL 见 `config.py`）。
- **`GIT_AGENT_TOKEN_DEV` / `GIT_AGENT_USERNAME_DEV` / `GIT_AGENT_EMAIL_DEV`**：开发账号推送、建 PR、`git` 提交身份。
- **`GIT_AGENT_TOKEN_REVIEW` / `GIT_AGENT_USERNAME_REVIEW`**：非真人审查模式下代发 `gh pr review`（PAT 需对仓库有 **Pull requests 写** 等权限；**审查账号不宜与 PR 作者同一账号自审**）。
- **`GIT_AGENT_TOKEN_TEST` / `GIT_AGENT_USERNAME_TEST`**：QA 评论。
- 可选 **`GITHUB_REPO`**、**`REPO_ROOT`**（`run-automation.sh` 会设置）。

示例加载：

```bash
set -a
source ./.env.bash
set +a
export REPO_ROOT="$(pwd)"
```

### 5.4 状态文件与开跑

```bash
cp state/req-status.example.json state/req-status.json
# 编辑 JSON：将要做的 REQ 标为 READY
./run-automation.sh --once --req-id REQ-01
```

或使用：

```bash
mc-auto init-state
mc-auto run-once --req-id REQ-01
```

### 5.5 冒烟（可选）

```bash
python3 scripts/crewai_glm_smoke.py
python3 scripts/crewai_github_pat_smoke.py
```

---

## 6. 常见问题

| 现象 | 可能原因 |
|------|----------|
| `OpenAI function name cannot be empty` | `@tool("...")` 使用了中文名；本仓库已改为 **英文工具名**，中文写在 docstring。 |
| 生成代码被截断 | **`LLM_MAX_TOKENS`** 过小；默认已提高到 **4096**（见 `config.py`）。 |
| `gh pr create` 报 `unknown flag: --json` | 旧版 `gh`；已在 **`repo_ops`** 改为解析 URL。 |
| `Resource not accessible by personal access token` | 对应角色的 **Classic PAT** 勾选 **`repo`**，或 **Fine-grained** 对目标仓库开启 **Pull requests: Read and write**；审查账号需对仓库有写权限。 |
| 覆盖率门禁失败 | 检查 **`COVERAGE_MIN`** 与 `pyproject.toml` 里 **coverage omit**；或先使用默认 **50**。 |

---

## 7. 与 `docs/automation-tutorial.md` 的关系

- **`docs/automation-tutorial.md`**：面向「怎么配环境、怎么跑、排错」的教程。
- **本文**：面向 **`mastercoder_automation` 包结构与设计取舍**；部署步骤以本节 **§5** 与教程中实际操作互相补充。

若你只关心「能跑」，优先跟 **`README.md`** 与 **`run-automation.sh`** 注释；若关心「代码为什么这么拆」，以本文为准。
