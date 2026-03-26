# MasterCoder - 自动化开发指导手册

> 本文档指导 AI Agent（开发 Agent、Review Agent、测试 Agent）按照标准化自动化流程完成 MasterCoder 项目的开发。
> 所有流程设计为机器可执行，人工仅在最终验收和异常仲裁时介入。

---

## 1. 项目信息

### 1.1 仓库地址

```
https://github.com/xslkim/MasterCoder.git
```

### 1.2 Agent 账号分配

| Agent 角色 | GitHub 账号（邮箱） | 职责 |
|-----------|---------------------|------|
| 开发 Agent | youmiss@163.com | 编码实现 + 单元测试 + 提交代码 |
| Review Agent | gaobiedongtian@163.com | 代码审查 + 静态分析 + 规范检查 |
| 测试 Agent | xiangsilian@gmail.com | 执行验收测试 + 生成测试报告 |

> 每个账号的 Personal Access Token (PAT) 通过环境变量注入 Agent 运行环境，不在文档中明文记录。

### 1.3 Git 认证配置（必须在开发前完成）

GitHub 自 2021 年 8 月起**不再支持密码进行 Git 操作**，必须使用 Personal Access Token (PAT)。以下是三个 Agent 的完整配置流程。

#### 第一步：为每个账号创建 Personal Access Token (PAT)

分别登录三个 GitHub 账号，各自创建一个 PAT：

1. 浏览器登录 GitHub（使用对应邮箱和密码）
2. 进入 `Settings → Developer settings → Personal access tokens → Tokens (classic)`
3. 点击 `Generate new token (classic)`
4. 配置：
   - **Note**: `MasterCoder Agent - <角色名>`（如 `MasterCoder Agent - Dev`）
   - **Expiration**: 建议 90 天或根据项目周期设定
   - **Scopes 权限勾选**：

| Agent 角色 | 需要的 Scopes |
|-----------|---------------|
| 开发 Agent | `repo`（完整仓库访问） |
| Review Agent | `repo` |
| 测试 Agent | `repo` |

5. 点击 `Generate token`，**立即复制保存**（只展示一次）

生成的 PAT 格式类似：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### 第二步：仓库 Owner 邀请 Collaborator

仓库 Owner（xslkim）需要将三个账号添加为仓库协作者：

1. 进入仓库 `https://github.com/xslkim/MasterCoder`
2. `Settings → Collaborators → Add people`
3. 分别输入三个邮箱对应的 GitHub 用户名，邀请加入
4. 权限级别设置：

| Agent 角色 | 推荐权限 |
|-----------|----------|
| 开发 Agent | **Write**（推送分支 + 创建 PR） |
| Review Agent | **Write**（Approve/Reject PR） |
| 测试 Agent | **Write**（Comment on PR） |

5. 三个账号分别登录 GitHub 接受邀请

#### 第三步：Agent 运行环境中配置 Git 认证

每个 Agent 在其运行环境中执行以下配置：

**方案 A：环境变量注入（推荐，最适合自动化）**

```bash
# 每个 Agent 的运行环境设置对应的环境变量
# 开发 Agent 环境
export GIT_AGENT_USERNAME="<开发 Agent 的 GitHub 用户名>"
export GIT_AGENT_TOKEN="ghp_xxxxxxxxxxxxxxx"  # 开发 Agent 的 PAT
export GIT_AGENT_EMAIL="youmiss@163.com"

# Review Agent 环境
export GIT_AGENT_USERNAME="<Review Agent 的 GitHub 用户名>"
export GIT_AGENT_TOKEN="ghp_xxxxxxxxxxxxxxx"  # Review Agent 的 PAT
export GIT_AGENT_EMAIL="gaobiedongtian@163.com"

# 测试 Agent 环境
export GIT_AGENT_USERNAME="<测试 Agent 的 GitHub 用户名>"
export GIT_AGENT_TOKEN="ghp_xxxxxxxxxxxxxxx"  # 测试 Agent 的 PAT
export GIT_AGENT_EMAIL="xiangsilian@gmail.com"
```

Agent 初始化时执行的 Git 配置脚本：

```bash
#!/bin/bash
# agent-git-setup.sh — 每个 Agent 启动时执行一次

# 1. 配置 Git 身份（用于 commit 的 author 信息）
git config user.name "$GIT_AGENT_USERNAME"
git config user.email "$GIT_AGENT_EMAIL"

# 2. 配置 Git 认证（使用 PAT 替代密码）
#    通过 credential helper 存储，避免每次输入
git config credential.helper store
echo "https://${GIT_AGENT_USERNAME}:${GIT_AGENT_TOKEN}@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials

# 3. 配置 GitHub CLI（用于创建 PR、Review 等操作）
echo "$GIT_AGENT_TOKEN" | gh auth login --with-token

# 4. 验证认证是否成功
echo "--- 验证 Git 认证 ---"
git ls-remote https://github.com/xslkim/MasterCoder.git HEAD && echo "Git 认证成功" || echo "Git 认证失败"

echo "--- 验证 GitHub CLI ---"
gh auth status && echo "GitHub CLI 认证成功" || echo "GitHub CLI 认证失败"
```

**方案 B：使用 HTTPS URL 内嵌 Token（简单但不推荐长期使用）**

```bash
# 直接在 remote URL 中嵌入 Token
git remote set-url origin https://<username>:<PAT>@github.com/xslkim/MasterCoder.git
```

#### 第四步：验证各 Agent 的 Git 操作权限

**开发 Agent 验证：**
```bash
# 能克隆仓库
git clone https://github.com/xslkim/MasterCoder.git /tmp/test-clone

# 能创建分支并推送
cd /tmp/test-clone
git checkout -b test/dev-agent-verify
echo "test" > verify.txt
git add verify.txt
git commit -m "test: verify dev agent access"
git push origin test/dev-agent-verify

# 能创建 PR
gh pr create --title "Test: Dev Agent Verify" --body "Verification PR, will be closed" --head test/dev-agent-verify

# 清理：关闭 PR 并删除分支
gh pr close --delete-branch
```

**Review Agent 验证：**
```bash
# 能查看 PR
gh pr list

# 能 Approve PR（需要有一个打开的 PR）
# gh pr review <PR_NUMBER> --approve

# 能 Comment
# gh pr comment <PR_NUMBER> --body "Review Agent verified"
```

**测试 Agent 验证：**
```bash
# 能拉取分支
git fetch origin
git checkout <some-branch>

# 能在 PR 中 Comment
# gh pr comment <PR_NUMBER> --body "QA_PASSED"
```

#### Git 操作速查（各 Agent 日常使用）

**开发 Agent 日常操作：**
```bash
# 拉取最新 main 并创建分支
git checkout main && git pull origin main
git checkout -b feat/req-XX-description

# 编码完成后提交
git add src/mastercoder/ tests/
git commit -m "feat(req-XX): implement feature"
git push origin feat/req-XX-description

# 创建 PR（使用 gh CLI）
gh pr create \
  --title "[REQ-XX] 需求简称" \
  --body "## 变更说明\n- ...\n\n## 验收标准\n- ..." \
  --reviewer "<review-agent-username>"
```

**Review Agent 日常操作：**
```bash
# 查看待 Review 的 PR
gh pr list --state open

# 拉取 PR 分支进行本地检查
gh pr checkout <PR_NUMBER>

# 运行质量门禁
ruff check src/ tests/
pytest tests/ -v --cov=mastercoder --cov-fail-under=80

# Approve PR
gh pr review <PR_NUMBER> --approve --body "APPROVED: all checks passed"

# 或 Reject PR
gh pr review <PR_NUMBER> --request-changes --body "REJECTED: <具体问题>"
```

**测试 Agent 日常操作：**
```bash
# 拉取 PR 分支
gh pr checkout <PR_NUMBER>

# 安装并测试
pip install -e ".[dev]"
pytest tests/ -v --junitxml=reports/junit.xml --cov=mastercoder --cov-report=xml:reports/coverage.xml

# 通过 → Comment
gh pr comment <PR_NUMBER> --body "QA_PASSED"

# 失败 → Comment
gh pr comment <PR_NUMBER> --body "QA_FAILED: <失败项列表>"
```

**合并 PR（Review + QA 都通过后）：**
```bash
# 开发 Agent 或仓库 Owner 执行合并
gh pr merge <PR_NUMBER> --squash --delete-branch
```

#### 安全注意事项

- PAT 等同于密码，**绝不可**提交到 Git 仓库
- `.git-credentials` 文件权限必须为 `600`（仅 Owner 可读）
- PAT 应设置合理的过期时间，过期后重新生成
- 建议为每个 Agent 创建独立的 PAT，方便按角色吊销
- `teams.md` 中不应包含明文密码，已更新为安全引用方式

---

## 2. 技术栈（已冻结）

| 维度 | 选型 | 版本要求 |
|------|------|----------|
| **开发语言** | Python | >= 3.11 |
| **包管理** | pip + pyproject.toml | PEP 621 |
| **测试框架** | pytest | >= 8.0 |
| **覆盖率工具** | pytest-cov | >= 5.0 |
| **代码格式化** | ruff format | >= 0.4 |
| **代码检查** | ruff check | >= 0.4 |
| **CLI 参数解析** | click | >= 8.0 |
| **HTTP 客户端** | httpx | >= 0.27（支持 SSE 流式） |
| **语法高亮** | pygments | >= 2.17 |
| **类型检查** | mypy | >= 1.10（可选，不阻断） |

### 2.1 初始依赖配置

```toml
# pyproject.toml
[project]
name = "mastercoder"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0",
    "httpx>=0.27",
    "pygments>=2.17",
]

[project.scripts]
mastercoder = "mastercoder.main:cli"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.4",
]
```

---

## 3. 项目目录结构（完整目标）

以下为项目最终完整目录结构，所有需求的产出物对应关系明确。

**入口点说明：** 程序唯一入口为 `mastercoder.main:cli`（定义在 `main.py` 中）。`cli.py` 是参数解析工具模块，提供 `parse_args()` 等函数，由 `main.py` 导入调用——`cli.py` 本身不定义入口函数。

```
MasterCoder/
├── docs/
│   ├── product-spec.md
│   ├── requirements.md
│   └── dev-guide.md
├── src/
│   └── mastercoder/                # Python 包目录
│       ├── __init__.py              # 版本号定义
│       ├── main.py                  # 程序入口 + REPL（REQ-01）
│       ├── config.py                # 配置系统（REQ-02, REQ-19）
│       ├── api_client.py            # API 客户端（REQ-03）
│       ├── message_manager.py       # 消息管理器（REQ-04）
│       ├── chat_loop.py             # 对话循环（REQ-05, REQ-14）
│       ├── tools/
│       │   ├── __init__.py          # Tool 基类定义（REQ-06）
│       │   ├── registry.py          # 工具注册器（REQ-06）
│       │   ├── executor.py          # 工具执行引擎（REQ-07）
│       │   ├── read_file.py         # REQ-08
│       │   ├── write_file.py        # REQ-09
│       │   ├── edit_file.py         # REQ-10
│       │   ├── list_files.py        # REQ-11
│       │   ├── search_files.py      # REQ-12
│       │   └── run_command.py       # REQ-13
│       ├── security.py              # 安全与权限（REQ-15）
│       ├── renderer.py              # Markdown 渲染（REQ-16）
│       ├── ui.py                    # 状态栏 + Spinner（REQ-17）
│       ├── commands.py              # 斜杠命令（REQ-18）
│       ├── session.py               # 会话持久化（REQ-20）
│       ├── input_handler.py         # 多行输入（REQ-21）
│       ├── context.py               # @ 文件引用（REQ-22）
│       ├── retry.py                 # 重试机制（REQ-23）
│       ├── cli.py                   # 命令行参数解析工具（REQ-24，被 main.py 调用，不是独立入口）
│       └── git_info.py              # Git 感知（REQ-25）
├── tests/
│   ├── conftest.py                  # pytest fixtures（临时目录、Mock Server 等）
│   ├── test_main.py                 # REQ-01
│   ├── test_config.py               # REQ-02, REQ-19
│   ├── test_api_client.py           # REQ-03
│   ├── test_message_manager.py      # REQ-04
│   ├── test_chat_loop.py            # REQ-05
│   ├── test_integration.py          # REQ-14
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── test_registry.py         # REQ-06
│   │   ├── test_executor.py         # REQ-07
│   │   ├── test_read_file.py        # REQ-08
│   │   ├── test_write_file.py       # REQ-09
│   │   ├── test_edit_file.py        # REQ-10
│   │   ├── test_list_files.py       # REQ-11
│   │   ├── test_search_files.py     # REQ-12
│   │   └── test_run_command.py      # REQ-13
│   ├── test_security.py             # REQ-15
│   ├── test_renderer.py             # REQ-16
│   ├── test_ui.py                   # REQ-17
│   ├── test_commands.py             # REQ-18
│   ├── test_session.py              # REQ-20
│   ├── test_input_handler.py        # REQ-21
│   ├── test_context.py              # REQ-22
│   ├── test_retry.py                # REQ-23
│   ├── test_cli.py                  # REQ-24
│   └── test_git_info.py             # REQ-25
├── pyproject.toml
├── README.md
├── .gitignore
└── MASTERCODER.md                   # 项目指令文件（REQ-19）
```

---

## 4. Phase 1 范围（v0.1.0 交付目标）

Phase 1 聚焦于一个**可闭环运行**的最小可用版本：

| 批次 | 包含需求 | 说明 |
|------|----------|------|
| P1-Batch-1 | REQ-01 → REQ-02 → REQ-03 → REQ-04 → REQ-05 | 基础串行，打地基 |
| P1-Batch-2 | REQ-06 → REQ-07 | 工具框架 + 执行引擎 |
| P1-Batch-3 | REQ-08, REQ-09, REQ-13 | 三个核心工具（可并行） |
| P1-Batch-4 | REQ-15（最小版） | 路径沙箱 + 命令黑名单（不含敏感操作高亮） |
| P1-Batch-5 | REQ-18（最小版） | `/help` `/clear` `/model` `/exit`（不含 `/config`） |

**Phase 1 完成标志：** 用户可启动 mastercoder，与 AI 对话，AI 可读写文件、执行命令，文件操作受沙箱保护，可用斜杠命令控制会话。

Phase 2（REQ-10~12, REQ-14, REQ-16~17, REQ-19~25 及 REQ-15/18 完整版）在 Phase 1 全部合入 main 后开展。

---

## 5. 自动化开发流程（Agent Pipeline）

### 5.1 需求状态机

每个 REQ 在生命周期中经过以下状态，**仅允许按箭头方向迁移**：

```
                    ┌──────────────┐
                    │   PENDING    │  初始状态，前置依赖未满足
                    └──────┬───────┘
                           │ 前置依赖全部 DONE
                           ▼
                    ┌──────────────┐
                    │    READY     │  可以开始开发
                    └──────┬───────┘
                           │ 开发 Agent 领取
                           ▼
                    ┌──────────────┐
             ┌─────│  DEVELOPING  │  开发 Agent 编码中
             │     └──────┬───────┘
             │            │ 提交代码 + 测试通过
             │            ▼
             │     ┌──────────────┐
             │ ┌───│  REVIEWING   │  Review Agent 审查中
             │ │   └──────┬───────┘
             │ │          │ Review 通过
             │ │          ▼
             │ │   ┌──────────────┐
             │ │   │   TESTING    │  测试 Agent 验收中
             │ │   └──────┬───────┘
             │ │          │ 测试全部通过
             │ │          ▼
             │ │   ┌──────────────┐
             │ │   │    DONE      │  合并到 main
             │ │   └──────────────┘
             │ │
             │ │   Review 打回 或 测试失败
             │ └──►┌──────────────┐
             └────►│   FIXING     │  开发 Agent 修复中
                   └──────┬───────┘
                          │ 修复完成
                          ▼
                   回到 REVIEWING（若 Review 打回）
                   回到 TESTING（若测试失败）
```

### 5.2 状态迁移条件

| 迁移 | 触发条件 | 执行者 |
|------|----------|--------|
| PENDING → READY | 该 REQ 的所有 `blockedBy` 依赖状态为 DONE | 自动检测 |
| READY → DEVELOPING | 开发 Agent 领取任务 | 开发 Agent |
| DEVELOPING → REVIEWING | 满足全部提交条件（见 5.3） | 开发 Agent |
| REVIEWING → TESTING | Review Agent 输出 `APPROVED` | Review Agent |
| REVIEWING → FIXING | Review Agent 输出 `REJECTED: <原因>` | Review Agent |
| TESTING → DONE | 测试 Agent 输出 `QA_PASSED` | 测试 Agent |
| TESTING → FIXING | 测试 Agent 输出 `QA_FAILED: <bug列表>` | 测试 Agent |
| FIXING → REVIEWING | 开发 Agent 修复后重新满足提交条件 | 开发 Agent |
| FIXING → TESTING | 开发 Agent 修复后（若从 TESTING 回退）| 开发 Agent |
| DONE → 合并 | 自动合并 PR 到 main | 自动 |

### 5.3 DEVELOPING → REVIEWING 提交条件

开发 Agent 完成编码后，**必须全部满足**以下条件才能提交：

```bash
# 1. 代码格式化检查（不通过则阻断）
ruff format --check src/ tests/

# 2. 代码 lint 检查（不通过则阻断）
ruff check src/ tests/

# 3. 单元测试全部通过（不通过则阻断）
pytest tests/ -v --tb=short

# 4. 覆盖率达标（不通过则阻断）
pytest tests/ --cov=mastercoder --cov-report=term --cov-fail-under=80

# 5. 产出 JUnit XML + Coverage XML（供后续解析）
pytest tests/ -v --junitxml=reports/junit.xml --cov=mastercoder --cov-report=xml:reports/coverage.xml
```

**所有 5 步全部通过后**，开发 Agent 推送代码并创建 PR。

### 5.4 失败回退规则

| 失败场景 | 回退行为 | 最大重试次数 |
|----------|----------|-------------|
| `ruff format --check` 失败 | 执行 `ruff format src/ tests/` 后重新提交 | 1 次（格式化应自动修复） |
| `ruff check` 失败 | 开发 Agent 根据错误信息修复代码 | 3 次 |
| `pytest` 失败 | 开发 Agent 根据失败输出修复代码/测试 | 5 次 |
| 覆盖率不达标 | 开发 Agent 补充测试用例 | 3 次 |
| Review 打回 | 开发 Agent 根据 Review 意见修复 | 3 次 |
| 测试验收失败 | 开发 Agent 根据 Bug 报告修复 | 3 次 |
| 超过最大重试次数 | 标记为 BLOCKED，**人工介入** | - |

---

## 6. Git 分支与提交规范

### 6.1 分支命名

| 分支类型 | 格式 | 示例 |
|----------|------|------|
| 主分支 | `main` | `main` |
| 需求分支 | `feat/req-<编号>-<描述>` | `feat/req-01-project-scaffold` |
| 修复分支 | `fix/req-<编号>-<描述>` | `fix/req-03-stream-parse` |

### 6.2 开发 Agent Git 操作流程

```bash
# 1. 拉取最新 main
git checkout main && git pull origin main

# 2. 创建需求分支
git checkout -b feat/req-XX-description

# 3. 编码完成后，运行质量门禁
ruff format src/ tests/
ruff check src/ tests/
pytest tests/ -v --cov=mastercoder --cov-fail-under=80 --junitxml=reports/junit.xml --cov-report=xml:reports/coverage.xml

# 4. 提交代码（仅提交源码和测试，不提交 reports/）
git add src/ tests/ pyproject.toml
git commit -m "feat(req-XX): <简要描述>"

# 5. 推送并创建 PR
git push origin feat/req-XX-description
gh pr create --title "[REQ-XX] <需求简称>" --body "..."
```

### 6.3 Commit Message 规范

```
<type>(req-<编号>): <简要描述>
```

| type | 含义 |
|------|------|
| `feat` | 新功能实现 |
| `fix` | Bug 修复（含 Review/测试打回后的修复） |
| `test` | 仅测试变更 |
| `refactor` | 重构 |

---

## 7. 质量门禁（Gate）

### 7.1 统一验收命令

所有 Agent 使用同一套命令判定通过/失败：

```bash
# 格式化（自动修复）
ruff format src/ tests/

# Lint（不通过即失败）
ruff check src/ tests/

# 测试 + 覆盖率（不通过即失败）
pytest tests/ -v \
  --tb=short \
  --cov=mastercoder \
  --cov-report=term \
  --cov-report=xml:reports/coverage.xml \
  --cov-fail-under=80 \
  --junitxml=reports/junit.xml

# 判定规则：以上命令的 exit code 全部为 0 → 通过；任一非 0 → 失败
```

### 7.2 产出物（供自动化解析）

| 文件 | 格式 | 用途 |
|------|------|------|
| `reports/junit.xml` | JUnit XML | 测试结果（通过/失败/数量） |
| `reports/coverage.xml` | Cobertura XML | 覆盖率数据 |
| `ruff check` stdout | 文本 | Lint 问题列表 |

### 7.3 Definition of Done（完成定义）

一个 REQ 状态迁移为 DONE，**必须同时满足**：

- [ ] 代码已合入 `main` 分支
- [ ] `ruff format --check` 通过（exit code 0）
- [ ] `ruff check` 通过（exit code 0）
- [ ] `pytest` 全部通过（exit code 0）
- [ ] 覆盖率 >= 80%
- [ ] Review Agent 输出 `APPROVED`
- [ ] 测试 Agent 输出 `QA_PASSED`
- [ ] 无 severity=high 的未关闭 Bug

---

## 8. 各 Agent 操作规范

### 8.1 开发 Agent

**输入：** 需求文档中对应 REQ 的功能规格、参数定义、错误处理、交付物列表

**操作流程：**
1. 检查该 REQ 状态为 READY（所有 blockedBy 为 DONE）
2. 从 `main` 创建分支 `feat/req-XX-description`
3. 按需求文档编写功能代码（放在 `src/mastercoder/` 下对应文件）
4. 按需求文档编写单元测试（放在 `tests/` 下对应文件）
5. 运行质量门禁命令，全部通过后提交
6. 推送分支，创建 PR

**输出：**
- Git 分支 + PR
- `reports/junit.xml`（测试结果）
- `reports/coverage.xml`（覆盖率）

### 8.2 Review Agent

**输入：** PR diff + 需求文档中对应 REQ 的 Review 检查项

**操作流程：**
1. 拉取 PR 分支代码
2. 运行质量门禁命令，验证全部通过
3. 逐项检查需求文档中的 Review 检查项
4. 检查代码安全性（无硬编码密钥、无注入风险）
5. 检查代码与需求的一致性

**输出（二选一）：**
- `APPROVED` — 在 PR 中 approve
- `REJECTED: <逐条列出问题>` — 在 PR 中 request changes

### 8.3 测试 Agent

**输入：** PR 分支 + 需求文档中对应 REQ 的验收标准

**操作流程：**
1. 拉取 PR 分支
2. 安装依赖：`pip install -e ".[dev]"`
3. 运行质量门禁命令，验证全部通过
4. 按验收标准逐项执行测试（可编写额外的验收脚本）
5. 生成测试报告

**输出（二选一）：**
- `QA_PASSED` — 在 PR 中 comment
- `QA_FAILED: <逐条列出失败项和 Bug>` — 在 PR 中 comment

**测试报告格式：**
```json
{
  "req_id": "REQ-XX",
  "timestamp": "2026-03-26T14:30:00Z",
  "unit_tests": {
    "command": "pytest tests/ -v --junitxml=reports/junit.xml",
    "exit_code": 0,
    "passed": 12,
    "failed": 0,
    "errors": 0
  },
  "coverage": {
    "command": "pytest tests/ --cov=mastercoder --cov-report=xml:reports/coverage.xml",
    "line_rate": 0.85
  },
  "acceptance_tests": [
    {"id": "AC-01", "description": "...", "result": "PASS", "notes": ""},
    {"id": "AC-02", "description": "...", "result": "FAIL", "notes": "Bug: ..."}
  ],
  "verdict": "QA_PASSED"
}
```

---

## 9. 需求依赖关系与合并顺序

### 9.1 Phase 1 依赖图

```
REQ-01 ──► REQ-02 ──► REQ-03 ──► REQ-04 ──► REQ-05
                                                │
                                    REQ-06 ──► REQ-07
                                      │
                          ┌───────────┼───────────┐
                          ▼           ▼           ▼
                       REQ-08      REQ-09      REQ-13
                          │           │           │
                          └─────┬─────┘           │
                                ▼                 │
                             REQ-15 ◄─────────────┘
                                │
                             REQ-18
```

### 9.2 严格合并顺序（Phase 1）

Phase 1 中的需求**必须按以下顺序合并到 main**，不可跳跃：

```
1.  REQ-01  项目脚手架
2.  REQ-02  配置系统
3.  REQ-03  API 客户端
4.  REQ-04  消息管理器
5.  REQ-05  基础对话循环
6.  REQ-06  工具定义框架
7.  REQ-07  工具执行引擎
    ──── 以下三个可并行开发，但合并顺序固定 ────
8.  REQ-08  read_file
9.  REQ-09  write_file
10. REQ-13  run_command
    ──── 以上三个全部合并后 ────
11. REQ-15  安全与权限（最小版）
12. REQ-18  斜杠命令（最小版）
```

### 9.3 并行开发的模块边界

以下需求可**并行开发**，但需遵守边界规则：

| 可并行组 | 需求 | 独占文件（不可同时修改） | 共享文件处理规则 |
|----------|------|------------------------|------------------|
| 核心工具组 | REQ-08, REQ-09, REQ-13 | 各自的 `tools/<name>.py` 和 `tests/tools/test_<name>.py` | 不修改 `registry.py`、`executor.py`、`chat_loop.py`（这些由 REQ-14 统一集成） |
| Phase 2 工具组 | REQ-10, REQ-11, REQ-12 | 各自的工具文件 | 同上 |
| UI 增强组 | REQ-16, REQ-17 | 各自的模块文件 | `chat_loop.py` 由各自添加独立的 hook 点，不修改对方的 hook |

**接口先行原则：** 被多个需求依赖的模块（如 `registry.py`、`security.py`），其公开接口在被依赖的 REQ 中定义完毕后冻结。后续 REQ 只调用接口，不修改接口签名。

**合并冲突处理：** 同一并行组的需求，按编号升序合并。后合并的分支需先 rebase 到最新 main 后再提交。

### 9.4 Phase 2 依赖关系修正

| 需求 | 实际依赖 |
|------|----------|
| REQ-10 edit_file | REQ-06 |
| REQ-11 list_files | REQ-06 |
| REQ-12 search_files | REQ-06 |
| REQ-14 工具集成 | REQ-05, REQ-07, REQ-08~13 全部 |
| REQ-15 完整版 | REQ-08~13 全部（补敏感操作高亮） |
| REQ-16 Markdown 渲染 | REQ-05 |
| REQ-17 状态栏与统计 | REQ-05 |
| REQ-18 完整版 | REQ-18 最小版（补 `/config`） |
| REQ-19 项目配置 | REQ-02 |
| REQ-20 会话持久化 | REQ-04, **REQ-18**（/sessions 命令）, **REQ-24**（--resume 参数） |
| REQ-21 多行输入 | REQ-01 |
| REQ-22 手动添加上下文 | REQ-05, REQ-08 |
| REQ-23 错误处理与重试 | REQ-03 |
| REQ-24 命令行参数 | REQ-02 |
| REQ-25 Git 感知 | REQ-17 |

---

## 10. Phase 1 逐需求开发指引

以下为 Phase 1 中每个需求的详细开发指引。

### REQ-01：项目脚手架与入口程序

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-01-project-scaffold` |
| 源码文件 | `src/mastercoder/__init__.py`, `src/mastercoder/main.py` |
| 测试文件 | `tests/test_main.py` |
| 配置文件 | `pyproject.toml`, `README.md`, `.gitignore` |
| 前置依赖 | 无 |

**开发 Agent 任务清单：**
1. 创建 `pyproject.toml`（按第 2.1 节配置）
2. 创建 `src/mastercoder/__init__.py`，定义 `__version__ = "0.1.0"`
3. 创建 `src/mastercoder/main.py`：
   - 打印 `MasterCoder v0.1.0\nType /help for available commands, /exit to quit.`
   - REPL 循环：`> ` 提示符 → 读取输入 → 原样回显 → 循环
   - 空行跳过
   - `/exit` 打印 `Goodbye!` 退出（exit code 0）
   - `Ctrl+C` 信号处理，打印 `Goodbye!` 退出（exit code 0）
4. 创建 `.gitignore`（见附录 A）
5. 编写 `tests/test_main.py`：测试欢迎信息、空行跳过、`/exit` 退出
6. 运行质量门禁，通过后提交 PR

**Review Agent 检查项：**
- [ ] 目录结构使用 `src/mastercoder/` 布局
- [ ] `pyproject.toml` 包含 `[project.scripts]` 入口点
- [ ] REPL 循环无阻塞泄漏
- [ ] `Ctrl+C` 信号处理正确

**测试 Agent 验收标准：**
- [ ] AC-01: `pip install -e .` 后执行 `mastercoder`，显示欢迎信息
- [ ] AC-02: 输入 `hello`，回显 `hello`
- [ ] AC-03: 空行回车，无输出
- [ ] AC-04: 输入 `/exit`，程序退出，`echo $?` 为 0
- [ ] AC-05: `Ctrl+C` 退出，`echo $?` 为 0
- [ ] AC-06: `pytest tests/test_main.py` exit code 0

---

### REQ-02：配置系统

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-02-config-system` |
| 源码文件 | `src/mastercoder/config.py` |
| 测试文件 | `tests/test_config.py` |
| 修改文件 | `src/mastercoder/main.py`（启动时加载配置） |
| 前置依赖 | REQ-01 |

**开发 Agent 任务清单：**
1. 定义 `Config` dataclass，7 个字段及默认值（详见需求文档 REQ-02）
2. 实现 `load_config(config_dir=None)` 函数
3. 优先级：环境变量 > 配置文件 > 默认值
4. JSON 非法时 `sys.exit(1)`，字段超范围时警告并使用默认值
5. API Key 脱敏方法 `mask_api_key()`
6. 编写单元测试（使用 `tmp_path` fixture 和 `monkeypatch`）

**Review Agent 检查项：**
- [ ] 优先级实现正确
- [ ] `api_key` 不在用户可见输出中明文展示
- [ ] 使用 `pathlib.Path.home()` 解析路径
- [ ] 字段校验完整

**测试 Agent 验收标准：**
- [ ] AC-01: 无配置文件，程序使用默认值正常启动
- [ ] AC-02: 配置文件 `{"model":"deepseek-chat"}`，启动后模型为 `deepseek-chat`
- [ ] AC-03: `MASTERCODER_API_KEY=sk-env` 覆盖配置文件中的 `api_key`
- [ ] AC-04: 非法 JSON 配置文件，exit code 1
- [ ] AC-05: `{"temperature":5.0}`，打印警告并使用默认值
- [ ] AC-06: `pytest tests/test_config.py` exit code 0

---

### REQ-03：API 客户端

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-03-api-client` |
| 源码文件 | `src/mastercoder/api_client.py` |
| 测试文件 | `tests/test_api_client.py` |
| 前置依赖 | REQ-02 |

**开发 Agent 任务清单：**
1. 使用 `httpx` 实现 `APIClient` 类
2. 支持非流式和流式（SSE）两种模式
3. 流式 tool_calls 跨 delta 拼接
4. HTTP 错误码映射（401/404/429/500+）
5. 120 秒超时
6. 编写单元测试（使用 `httpx.MockTransport` 或 `pytest-httpx`）

**Review Agent 检查项：**
- [ ] `Authorization: Bearer {key}` 无多余空格
- [ ] 流式 SSE 解析处理空行和非标准格式
- [ ] 工具调用参数保持 JSON 字符串不解析
- [ ] 无 API Key 泄漏到日志

**测试 Agent 验收标准：**
- [ ] AC-01: Mock 非流式请求，获取正确 content
- [ ] AC-02: Mock 流式请求，delta 片段逐个回调，最终拼接正确
- [ ] AC-03: Mock 流式 tool_calls 响应，正确解析工具名和参数
- [ ] AC-04: Mock 401 → `Authentication failed` 错误
- [ ] AC-05: Mock 429 → `Rate limit exceeded` 错误
- [ ] AC-06: `pytest tests/test_api_client.py` exit code 0

---

### REQ-04：消息管理器

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-04-message-manager` |
| 源码文件 | `src/mastercoder/message_manager.py` |
| 测试文件 | `tests/test_message_manager.py` |
| 前置依赖 | REQ-03 |

**开发 Agent 任务清单：**
1. `MessageManager` 类：`add_message`、`get_messages`、`clear`、`get_token_estimate`、`prepare_messages`
2. Token 估算：`字符数 / 4`
3. 截断：跳过 system，从最旧非 system 消息开始移除
4. 截断返回副本，不修改原始列表
5. 编写 5 个测试场景的单元测试

**测试 Agent 验收标准：**
- [ ] AC-01: 添加 7 条消息后 `get_messages()` 返回 7 条
- [ ] AC-02: `clear()` 后仅剩 system 消息
- [ ] AC-03: 1000 字符消息 → `get_token_estimate()` 返回 250
- [ ] AC-04: 超出上下文限制时截断正确，system 保留
- [ ] AC-05: 未超出时 `truncated` 为 false
- [ ] AC-06: `pytest tests/test_message_manager.py` exit code 0

---

### REQ-05：基础对话循环

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-05-chat-loop` |
| 源码文件 | `src/mastercoder/chat_loop.py` |
| 测试文件 | `tests/test_chat_loop.py` |
| 修改文件 | `src/mastercoder/main.py`（接入 ChatLoop） |
| 前置依赖 | REQ-04 |

**开发 Agent 任务清单：**
1. 定义内置 system prompt 常量
2. 实现 `ChatLoop` 类串联 Config → MessageManager → APIClient
3. 启动时检查 `api_key` 非空
4. 流式输出逐 delta 打印
5. API 报错 → 红色错误提示，不污染消息列表
6. `Ctrl+C` 中断 → 保存部分回复 → `[Interrupted]`
7. 修改 `main.py` 用 `ChatLoop` 替换回显

**测试 Agent 验收标准：**
- [ ] AC-01: Mock API 正常对话流程
- [ ] AC-02: Mock API 多轮对话消息累积正确
- [ ] AC-03: Mock API 401 → 显示错误后可继续输入
- [ ] AC-04: `api_key` 为空 → 启动报错退出
- [ ] AC-05: `pytest tests/test_chat_loop.py` exit code 0

---

### REQ-06：工具定义与注册框架

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-06-tool-framework` |
| 源码文件 | `src/mastercoder/tools/__init__.py`, `src/mastercoder/tools/registry.py` |
| 测试文件 | `tests/tools/test_registry.py` |
| 前置依赖 | REQ-05 |

**开发 Agent 任务清单：**
1. 在 `tools/__init__.py` 定义 `Tool` 抽象基类（ABC）
2. `ToolRegistry` 类：`register`、`get_tool`、`get_openai_tools_schema`
3. 重复注册抛 `ValueError`
4. 编写 4 个测试场景

**测试 Agent 验收标准：**
- [ ] AC-01: Mock 工具注册后 `get_tool` 可查到
- [ ] AC-02: `get_openai_tools_schema()` 输出符合 OpenAI 格式
- [ ] AC-03: 重复注册抛 `ValueError`
- [ ] AC-04: `get_tool("nonexistent")` 返回 None
- [ ] AC-05: `pytest tests/tools/test_registry.py` exit code 0

---

### REQ-07：工具调用执行引擎

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-07-tool-executor` |
| 源码文件 | `src/mastercoder/tools/executor.py` |
| 测试文件 | `tests/tools/test_executor.py` |
| 前置依赖 | REQ-06 |

**开发 Agent 任务清单：**
1. `ToolExecutor` 类
2. 用户确认流程：`[Y]es / [N]o / [A]lways`
3. 工具执行 + 异常捕获
4. 结果封装为 tool 角色消息
5. 嵌套调用最大深度 20
6. 编写 8 个测试场景

**测试 Agent 验收标准：**
- [ ] AC-01: 工具调用确认 Y → 执行 → 结果返回
- [ ] AC-02: 确认 N → 返回 `Tool call was rejected by user`
- [ ] AC-03: 确认 A → 后续自动执行
- [ ] AC-04: `auto_approve=True` → 直接执行
- [ ] AC-05: 未知工具名 → `Error: Unknown tool`
- [ ] AC-06: 嵌套超 20 → 返回上限错误
- [ ] AC-07: `pytest tests/tools/test_executor.py` exit code 0

---

### REQ-08：read_file 工具

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-08-read-file` |
| 源码文件 | `src/mastercoder/tools/read_file.py` |
| 测试文件 | `tests/tools/test_read_file.py` |
| 前置依赖 | REQ-06 |
| 可并行 | 与 REQ-09、REQ-13 |

**独占文件：** `tools/read_file.py`, `tests/tools/test_read_file.py`
**禁止修改：** `registry.py`, `executor.py`, `chat_loop.py`, `main.py`

**开发 Agent 任务清单：**
1. 实现 `ReadFileTool(Tool)` 子类
2. 路径解析（相对 → 绝对）
3. 先 stat 检查大小（> 1MB 拒绝），再检查二进制（前 8192 字节含 null）
4. UTF-8 读取，返回 `"File: <path>\n\n<content>"`
5. 错误：不存在 / 权限 / 二进制 / 超大

**测试 Agent 验收标准：**
- [ ] AC-01: 读取正常文本文件，返回完整内容
- [ ] AC-02: 相对路径正确解析
- [ ] AC-03: 文件不存在 → `Error: File not found`
- [ ] AC-04: 二进制文件 → `Error: Cannot read binary file`
- [ ] AC-05: 超 1MB → `Error: File too large`
- [ ] AC-06: `pytest tests/tools/test_read_file.py` exit code 0

---

### REQ-09：write_file 工具

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-09-write-file` |
| 源码文件 | `src/mastercoder/tools/write_file.py` |
| 测试文件 | `tests/tools/test_write_file.py` |
| 前置依赖 | REQ-06 |
| 可并行 | 与 REQ-08、REQ-13 |

**独占文件：** `tools/write_file.py`, `tests/tools/test_write_file.py`
**禁止修改：** `registry.py`, `executor.py`, `chat_loop.py`, `main.py`

**开发 Agent 任务清单：**
1. 实现 `WriteFileTool(Tool)` 子类
2. 自动递归创建父目录
3. UTF-8 写入，返回字节数
4. 错误：路径是目录 / 权限不足

**测试 Agent 验收标准：**
- [ ] AC-01: 创建新文件成功
- [ ] AC-02: 父目录不存在时自动创建
- [ ] AC-03: 覆写已有文件
- [ ] AC-04: 路径是目录 → `Error: Path is a directory`
- [ ] AC-05: `pytest tests/tools/test_write_file.py` exit code 0

---

### REQ-13：run_command 工具

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-13-run-command` |
| 源码文件 | `src/mastercoder/tools/run_command.py` |
| 测试文件 | `tests/tools/test_run_command.py` |
| 前置依赖 | REQ-06 |
| 可并行 | 与 REQ-08、REQ-09 |

**独占文件：** `tools/run_command.py`, `tests/tools/test_run_command.py`
**禁止修改：** `registry.py`, `executor.py`, `chat_loop.py`, `main.py`

**开发 Agent 任务清单：**
1. 实现 `RunCommandTool(Tool)` 子类
2. `subprocess.run` + `sh -c`，设置 `cwd`
3. stdout/stderr 分别捕获，各限 50000 字符
4. 超时 SIGKILL 终止进程组
5. 空命令拒绝

**测试 Agent 验收标准：**
- [ ] AC-01: `echo hello` → exit code 0, stdout `hello`
- [ ] AC-02: 非零 exit code + stderr
- [ ] AC-03: 超时终止
- [ ] AC-04: 输出截断至 50000 字符
- [ ] AC-05: 空命令 → `Error: Command cannot be empty`
- [ ] AC-06: `pytest tests/tools/test_run_command.py` exit code 0

---

### REQ-15：安全与权限（Phase 1 最小版）

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-15-security-minimal` |
| 源码文件 | `src/mastercoder/security.py` |
| 测试文件 | `tests/test_security.py` |
| 修改文件 | `tools/read_file.py`, `tools/write_file.py`, `tools/run_command.py`（添加安全检查调用） |
| 前置依赖 | REQ-08, REQ-09, REQ-13 |

**Phase 1 范围：** 仅实现路径沙箱 + 命令黑名单，**不含**敏感操作高亮提醒（留到 Phase 2 REQ-15 完整版）。

**开发 Agent 任务清单：**
1. `check_path_sandbox(path, working_dir)` — resolve + 前缀检查 + 符号链接检查
2. `check_command_blacklist(command)` — 子串匹配危险模式
3. 沙箱为硬性约束，不可配置放宽
4. 在 read_file, write_file, run_command 的 `execute()` 开头调用检查

**测试 Agent 验收标准：**
- [ ] AC-01: `../../etc/passwd` → `Error: Access denied`
- [ ] AC-02: 指向沙箱外的符号链接 → `Error: Access denied`
- [ ] AC-03: `rm -rf /` → `Error: Command blocked for safety`
- [ ] AC-04: `ls -la` 正常执行不被拦截
- [ ] AC-05: `pytest tests/test_security.py` exit code 0

---

### REQ-18：斜杠命令（Phase 1 最小版）

| 项目 | 内容 |
|------|------|
| 分支 | `feat/req-18-slash-commands-minimal` |
| 源码文件 | `src/mastercoder/commands.py` |
| 测试文件 | `tests/test_commands.py` |
| 修改文件 | `src/mastercoder/main.py`（集成命令解析） |
| 前置依赖 | REQ-15 |

**Phase 1 范围：** 仅实现 `/help`、`/clear`、`/model`、`/exit`。`/config` 留到 Phase 2。

**开发 Agent 任务清单：**
1. `CommandParser` 类，解析 `/` 开头输入
2. 实现 4 个命令
3. 命令名大小写不敏感
4. 未知命令提示
5. 在 REPL 主循环中优先检测

**测试 Agent 验收标准：**
- [ ] AC-01: `/help` 打印命令列表
- [ ] AC-02: `/clear` 清空对话
- [ ] AC-03: `/model deepseek-chat` 切换模型
- [ ] AC-04: `/exit` 退出
- [ ] AC-05: `/unknown` 打印未知命令提示
- [ ] AC-06: `/HELP` 大写正常识别
- [ ] AC-07: `pytest tests/test_commands.py` exit code 0

---

## 11. Phase 1 进度总览

| 顺序 | 需求 | 分支 | 开发 | Review | 测试 | 状态 |
|------|------|------|------|--------|------|------|
| 1 | REQ-01 | `feat/req-01-project-scaffold` | `[ ]` | `[ ]` | `[ ]` | PENDING |
| 2 | REQ-02 | `feat/req-02-config-system` | `[ ]` | `[ ]` | `[ ]` | PENDING |
| 3 | REQ-03 | `feat/req-03-api-client` | `[ ]` | `[ ]` | `[ ]` | PENDING |
| 4 | REQ-04 | `feat/req-04-message-manager` | `[ ]` | `[ ]` | `[ ]` | PENDING |
| 5 | REQ-05 | `feat/req-05-chat-loop` | `[ ]` | `[ ]` | `[ ]` | PENDING |
| 6 | REQ-06 | `feat/req-06-tool-framework` | `[ ]` | `[ ]` | `[ ]` | PENDING |
| 7 | REQ-07 | `feat/req-07-tool-executor` | `[ ]` | `[ ]` | `[ ]` | PENDING |
| 8 | REQ-08 | `feat/req-08-read-file` | `[ ]` | `[ ]` | `[ ]` | PENDING |
| 9 | REQ-09 | `feat/req-09-write-file` | `[ ]` | `[ ]` | `[ ]` | PENDING |
| 10 | REQ-13 | `feat/req-13-run-command` | `[ ]` | `[ ]` | `[ ]` | PENDING |
| 11 | REQ-15 | `feat/req-15-security-minimal` | `[ ]` | `[ ]` | `[ ]` | PENDING |
| 12 | REQ-18 | `feat/req-18-slash-commands-minimal` | `[ ]` | `[ ]` | `[ ]` | PENDING |

---

## 附录 A：.gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
*.egg

# Virtual environment
.venv/
venv/

# IDE
.idea/
.vscode/
*.swp
*.swo

# MasterCoder runtime
.mastercoder/
*.log

# Test artifacts
reports/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db
```

## 附录 B：tests/conftest.py 公共 Fixtures

```python
"""公共测试 fixtures，所有测试文件可直接使用。"""
import pytest
from pathlib import Path


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """创建一个临时项目目录，模拟工作目录。"""
    project = tmp_path / "test_project"
    project.mkdir()
    (project / "README.md").write_text("# Test Project\n")
    (project / "src").mkdir()
    (project / "src" / "main.py").write_text("print('hello')\n")
    return project


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """创建临时配置目录，替代 ~/.mastercoder/。"""
    config_dir = tmp_path / ".mastercoder"
    config_dir.mkdir()
    return config_dir
```
