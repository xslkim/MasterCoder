# MasterCoder 技术架构解析 · 口播文档

> 目标受众：有一定 Python 基础的程序员
> 预计时长：约 15 分钟
> 字数：约 3000 字

---

## 开场

大家好，今天我们来聊一个有意思的项目——MasterCoder。

这个项目想解决的问题很简单，但也很有野心：**能不能让 AI 自动完成从需求分析、写代码、跑测试，一直到提 PR、审查代码、合并代码的整个开发流程？**

不是那种"AI 帮你补全代码"的程度，而是真正意义上把一个需求单子丢进去，然后它全自动走完一条完整的软件交付流水线。

这听起来很美好，但实际做起来有很多坑。今天我就带大家看看这个项目是怎么设计的，以及它在架构上做出了哪些值得学习的决策。

---

## 项目全貌

先看一眼整体结构。MasterCoder 分两层：

**第一层**是面向用户的 AI 编程客户端，代码在 `src/mastercoder/` 下。你可以把它理解成一个命令行版的 AI 编程助手，支持多轮对话、文件操作、执行 shell 命令等基础功能。

**第二层**才是这个项目真正的核心——`src/mastercoder_automation/`，一个基于 CrewAI 构建的多智能体自动化编排引擎。它的目标就是把"写代码这件事"流水线化、自动化。

两层共用同一个 Git 仓库，技术栈上用到了 CrewAI、Pydantic、Typer，LLM 接口走的是 OpenAI 兼容协议，默认对接的是智谱的 GLM 模型。

---

## 核心设计理念：确定性优先

在聊架构细节之前，我想先强调这个项目最重要的设计思想，也是让我觉得这个项目"想清楚了"的地方。

一般人设计 AI 自动化系统，容易掉进一个陷阱：**让 LLM 决定流程走向**。比如让 LLM 判断"这个代码合格吗？"，然后根据它的回答决定是通过还是拒绝。这样做的问题是，LLM 的输出是不确定的，同样的代码今天说通过，明天可能说不通过，系统行为完全不可预测。

MasterCoder 的解法是：**LLM 只负责推理和生成内容，流程控制权永远在代码手里**。

质量门禁（gates）靠的是 `ruff` 和 `pytest`——这些工具的结果是 100% 确定的。状态机靠的是 JSON 文件里的状态字段——每一步成功或失败都写死在代码逻辑里。LLM 做的事情是"生成代码"、"写审查意见"，而不是"决定这个 PR 能不能合"。

这个设计理念贯穿了整个系统，非常值得借鉴。

---

## 状态机：一切的核心

自动化层的核心是一个状态机，每个需求（REQ）有以下几个状态：

```
PENDING → READY → DEVELOPING → REVIEWING → TESTING → DONE
                       ↓
                   FIXING/BLOCKED（失败重试）
```

每个 REQ 在 `state/req-status.json` 里都有一条记录，大概长这样：

```json
{
  "req_id": "REQ-01",
  "title": "实现用户登录功能",
  "blocked_by": ["REQ-00"],
  "state": "READY",
  "retries": 0,
  "max_retries": 3,
  "branch": "feat/req-01-user-login",
  "pr_number": 42,
  "last_error": null
}
```

`blocked_by` 字段实现了依赖管理。如果 REQ-01 依赖 REQ-00，那 REQ-00 没完成之前，REQ-01 就一直是 PENDING 状态，不会启动。Orchestrator 每轮都会检查依赖关系，自动把条件满足的 REQ 从 PENDING 推进到 READY。

这个设计的好处是：**系统随时可以中断，随时可以恢复**。状态全在 JSON 文件里，进程挂了、网络断了，重新启动从文件里读状态继续跑就行。

---

## Orchestrator：编排引擎

`orchestrator.py` 是整个自动化层的大脑，约 430 行代码，干的事情就是推进状态机。

核心方法是 `_advance(req)`，它根据当前 REQ 的状态决定下一步做什么：

- 状态是 `READY`？调用 Dev Agent 开始写代码
- 状态是 `DEVELOPING` 完成后？推进到 `REVIEWING`，调用 Review Agent
- 状态是 `REVIEWING` 通过后？推进到 `TESTING`，调用 QA Agent
- 全部通过？调用 `gh pr merge` 合并，状态置为 `DONE`
- 任何环节失败？重试计数加一，超过上限就标记为 `BLOCKED`

重试机制是独立的。每个 REQ 有自己的 `retries` 和 `max_retries` 字段，互相不影响，一个 REQ 卡住不会拖垮整个队列。

从 CLI 角度看，有两个主命令：

```bash
mc-auto run-once   # 推进一个 REQ 一步，适合调试
mc-auto run-all    # 循环推进直到所有队列空
```

---

## Dev Agent：AI 写代码的过程

Dev Agent 是整个系统里最复杂的部分，代码在 `dev_crew.py`，基于 CrewAI 框架构建。

Dev Agent 有一套精心设计的工具链，每个工具对应一个具体操作：

**文件操作类：**
- `repo_read_file(path)` — 读取仓库里的文件
- `repo_write_file(path, content)` — 写入文件
- `repo_read_requirement(req_id)` — 按 REQ-ID 读取需求文档

**Git 操作类：**
- `git_status()` — 查看当前改动
- `git_stage_all()` — 暂存所有变更
- `git_commit_msg(message)` — 提交
- `git_push_branch()` — 推送到 GitHub

**质量门禁类：**
- `run_local_quality_gates()` — 运行 ruff + pytest + coverage

**GitHub 操作类：**
- `github_open_pull_request(title, body)` — 创建 PR

Dev Agent 的工作流程大概是这样的：先读需求文档，理解要做什么；然后**先写测试**，再写实现代码（TDD 风格）；写完调用 `run_local_quality_gates()` 跑门禁；通过了就 push 并创建 PR；没通过就根据错误信息修改，最多重试几次。

这里有一个细节值得注意：**测试文件必须有变更**。Orchestrator 在拿到 PR 前会检查 `tests/` 目录下有没有新增或修改的文件，没有的话直接打回，这是强制执行 TDD 的一种方式。

---

## 门禁系统（Gates）

`gates.py` 只有 61 行，但它是整个系统质量保障的关键。

门禁按顺序执行三步：

1. **`ruff format`** — 代码格式化，自动修正
2. **`ruff check`** — 静态检查，发现潜在问题
3. **`pytest`** — 跑单元测试，要求覆盖率达标

覆盖率下限默认 50%，可以通过环境变量 `COVERAGE_MIN` 调高。每次测试都会生成 `reports/coverage.xml` 和 `reports/junit.xml`，方便后续分析。

任何一步失败，`gates.py` 返回 `GateResult(passed=False, output="...错误日志...")`，错误日志会反馈给 Dev Agent，让它根据信息修复。

这个设计的好处是：**门禁结果是 100% 客观的**，不依赖 LLM 判断，Dev Agent 要么通过要么不通过，没有模糊地带。

---

## 多账号体系与权限隔离

这个项目有一个很实用的设计：用不同的 GitHub 账号扮演不同角色。

| 角色 | 职责 |
|------|------|
| Dev | 写代码、push 分支、创建 PR |
| Review | 审查代码（可以是 LLM 也可以是真人）|
| Test | QA 决策（可以是 LLM 也可以是真人）|
| Merge | 合并 PR（可选，缺失时用 Dev 账号）|

每个角色有独立的 GitHub PAT（个人访问令牌），通过环境变量配置：

```bash
GIT_AGENT_TOKEN_DEV=ghp_xxx
GIT_AGENT_USERNAME_DEV=dev-bot
GIT_AGENT_TOKEN_REVIEW=ghp_yyy
GIT_AGENT_USERNAME_REVIEW=review-bot
```

这个设计的价值在于：在 GitHub 上，PR 的创建者和审批者是两个不同的账号，这符合真实团队的权限规范，而且可以用来做权限审计——谁创建的、谁审批的、谁合并的，全链路清晰。

更进一步，系统支持"严格真人模式"：

```bash
AUTOMATION_STRICT_HUMAN_REVIEW=1   # Review 步骤等真人点 Approve
AUTOMATION_STRICT_HUMAN_QA=1       # QA 步骤等真人评论 QA_PASSED
```

开启后，系统会轮询 GitHub，直到检测到真人操作才继续往下走。这让系统可以在"全自动"和"半人工监督"之间灵活切换，适应不同团队对 AI 的信任程度。

---

## Worktree 隔离

每个 REQ 的开发工作在独立的 Git Worktree 里进行，这是一个容易被忽视但很重要的设计。

Git Worktree 允许你在同一个仓库里同时 checkout 多个分支到不同目录。MasterCoder 利用这个特性，给每个 REQ 创建一个独立的工作目录：

```
/path/to/repo/                    # 主分支
/path/to/repo-worktree-req-01/    # REQ-01 的独立工作目录
/path/to/repo-worktree-req-02/    # REQ-02 的独立工作目录
```

这样多个 REQ 可以并行开发，互不干扰，也不会污染主分支。

---

## 产品层：AI 编程客户端

说完自动化层，再简单聊一下产品层（`mastercoder/`）。

这一层实现了一个完整的 AI 编程助手，核心是一个多轮对话循环：

1. 用户输入问题或指令
2. 构建系统提示词（包含当前 Git 状态、文件列表等上下文）
3. 调用 LLM，获取流式输出
4. 如果 LLM 调用了工具（读文件、写文件、执行命令），展示给用户确认
5. 用户确认后执行，结果反馈给 LLM
6. 继续对话

系统提示词的构建是个有意思的细节（`system_prompt.py`）。它会自动注入：
- 当前仓库的 git log 和 status
- 当前目录的文件结构
- 项目级别的配置说明

这让 LLM 每次都有足够的上下文，不需要用户手动说"我在哪个分支、有哪些文件"。

**安全层**也做得比较扎实：
- `security/sandbox.py` 做路径隔离，防止 `../` 这样的路径逃逸出工作目录
- `security/commands.py` 维护一个危险命令黑名单（`rm -rf`、`dd` 等），直接拦截

---

## 整体数据流

把整个系统串起来，数据流是这样的：

```
需求文档（docs/）
    ↓
state/req-status.json（状态文件）
    ↓
Orchestrator（状态机推进）
    ↓
Dev Agent（CrewAI + 工具链）
    ├── 读需求 → 写测试 → 写代码
    ├── run_local_quality_gates()
    │       ├── ruff format / check
    │       └── pytest + coverage
    └── git push + gh pr create
    ↓
Review Agent（LLM 审查 或 真人审批）
    ↓
QA Agent（LLM 决策 或 真人评论）
    ↓
gh pr merge
    ↓
state = DONE，保存到 state/req-status.json
```

整个过程是幂等的，每一步都有状态持久化，随时可以中断恢复。

---

## 测试策略

这个项目有 30+ 个测试文件，覆盖了大部分核心模块。

值得一提的是，有几个模块被明确排除在覆盖率检查之外：`dev_crew.py`、`crew_agents.py`、`pr_human_gate.py`。这些模块强依赖真实的 LLM API 和 GitHub 环境，单元测试没法有效 mock，所以用冒烟测试脚本（`scripts/`）代替。

这是一个务实的测试策略——不为了覆盖率数字而写无意义的 mock，而是区分"可以单元测试的部分"和"需要集成测试的部分"，分别处理。

---

## 总结与思考

MasterCoder 最值得学习的地方，我觉得有三点：

**第一，确定性优先。** 不让 LLM 控制流程，用代码控制流程，用工具保证质量。LLM 只做它最擅长的——生成内容和推理。

**第二，状态持久化设计。** JSON 文件做状态机，简单粗暴但有效。系统随时可以中断、恢复、人工干预，不依赖进程常驻。

**第三，人机协作的弹性。** 同一套系统，可以配置成全自动，也可以配置成每一步都等真人确认。这种弹性让它能适应不同的信任场景——你对 AI 有多信任，就给它多少自主权。

当然这个项目也有局限：强依赖 GitHub，换成 GitLab 或 Gitea 就得改不少代码；LLM 接口目前主要对接智谱 GLM，换模型需要调整配置。

但作为一个**展示 AI Agent 与软件工程流程如何结合**的参考实现，它是非常完整的。如果你正在设计类似的 AI 自动化系统，这个项目的架构思路非常值得参考。

好了，今天的分享就到这里。感谢收看，我们下期见。

---

*文档版本：v1.0 | 对应项目提交：19ff773*
