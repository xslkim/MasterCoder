# MasterCoder 深度解析：当 AI Agent 学会了完整的软件工程 · 口播文档

> 目标受众：有 Python 基础的程序员
> 预计时长：约 25-30 分钟
> 字数：约 5000 字

---

## 一、开场：为什么需要这个项目

大家好，今天给大家拆解一个我觉得非常有代表性的 AI 工程化项目——MasterCoder。

先聊背景。现在市面上的 AI 编程工具，大家多少都用过。GitHub Copilot 帮你补全代码，Cursor 帮你在编辑器里对话改代码，Claude Code 能在终端里帮你操作文件和执行命令。这些工具都很好用，但它们解决的是"辅助开发"的问题——核心还是人在开发，AI 在旁边打辅助。

MasterCoder 想做的事情更进一步：**让 AI 独立跑完一条完整的软件交付流水线**。什么意思呢？你只需要写好需求文档，把需求的 ID 丢进去，系统就会自动完成：读需求、创建分支、写测试、写代码、跑 lint 和测试、创建 PR、做 Code Review、做 QA 验收、合并代码——全链路自动化。

听起来很科幻对吧？但 MasterCoder 确实实现了这套完整流程，而且它的架构设计非常值得学习。今天这期内容，我会从"它能做什么"和"它怎么做到的"两个维度来拆解这个项目，既讲功能也讲原理。

---

## 二、项目全景：两个产品，一套体系

MasterCoder 实际上包含两个产品，它们共用一个 Git 仓库，技术栈统一：

### 产品一：AI 编程客户端（mastercoder）

这是一个面向普通开发者的命令行 AI 编程助手，代码在 `src/mastercoder/` 下。你可以把它类比成一个开源版的 Claude Code。

启动方式很简单，在终端输入 `mastercoder`，就进入了一个交互式对话环境。你可以用自然语言跟它聊：

- "帮我写一个用户登录的接口"
- "这个函数有个 bug，帮我看看"
- "@src/config.py 帮我解释一下这个配置文件的结构"

注意最后一条，它支持 `@文件路径` 的语法，直接把文件内容注入到对话上下文里。这个设计借鉴了 Claude Code 的 `CLAUDE.md` 机制——MasterCoder 也有一个 `MASTERCODER.md`，放在项目根目录下，系统会自动读取并作为项目指令注入到每轮对话的系统提示词里。

它内置了六个工具：`read_file`（读文件）、`write_file`（写文件）、`edit_file`（编辑文件）、`list_files`（列目录）、`search_files`（搜索文件内容）、`run_command`（执行 shell 命令）。AI 调用这些工具时，默认会先展示给你看，你确认后才执行。当然你也可以开启自动批准模式，适合信任场景下的批量操作。

配置系统支持三级优先级：环境变量 > 项目级配置 > 全局配置 > 默认值。API 接口走的是 OpenAI 兼容协议，所以理论上你可以对接任何兼容 OpenAI Chat Completions API 的模型，包括 GPT-4o、DeepSeek、智谱 GLM 等等。

### 产品二：自动化交付引擎（mastercoder_automation）

这是整个项目真正的灵魂，代码在 `src/mastercoder_automation/` 下。它基于 CrewAI 多智能体框架构建，实现了从需求到代码合并的全自动化流水线。

命令行入口是 `mc-auto`，通过 Typer 框架实现，使用非常简洁：

```bash
mc-auto run-once --req-id REQ-01    # 推进一个需求一步
mc-auto run-all                      # 循环推进所有需求直到队列为空
mc-auto init-state                   # 初始化状态文件
mc-auto unblock-req REQ-05           # 手动解锁一个卡住的需求
```

或者更简单，用项目自带的启动脚本：

```bash
./run-automation.sh                  # 默认 run-all
./run-automation.sh REQ-01           # 只推进指定需求
./run-automation.sh --smoke          # 先跑冒烟测试再启动
```

这两个产品是互补的关系。客户端是给人用的，自动化引擎是给 AI Agent 用的。它们共享安全模块、Git 操作模块等底层能力。

接下来我们重点拆解自动化引擎的架构。

---

## 三、核心设计理念：确定性优先，LLM 不碰方向盘

在深入技术细节之前，我想先强调这个项目最重要的架构思想。

做 AI 自动化系统最常见的一个坑是什么？**让 LLM 来决定流程走向**。比如让 LLM 判断"这个 PR 的代码质量合格吗？"，然后根据它的回答来决定是合并还是打回。问题是，大语言模型的输出是概率性的——同样的代码今天跑可能说"通过"，明天跑可能说"有安全隐患建议重构"。流程的行为完全不可预测。

MasterCoder 的解法很干净：**把流程控制和内容生成彻底分离**。

流程的推进靠的是代码里写死的状态机逻辑和客观的质量门禁（ruff 格式检查 + pytest 单元测试）——这些工具的输出是 100% 确定的，跑一百次结果都一样。LLM 负责的是"生成代码"、"写审查意见"、"写 QA 评论"这些内容创作的工作。

用一句话总结就是：**AI 负责思考和创造，代码负责判断和执行**。

这个理念贯穿了整个系统设计，是理解后续所有技术决策的基础。

---

## 四、状态机：每个需求的生命周期

自动化引擎的核心数据结构是一个状态机，每个需求（REQ）会经历以下状态：

```
PENDING → READY → DEVELOPING → REVIEWING → TESTING → DONE
                       ↕
                  FIXING / BLOCKED
```

所有需求的状态都保存在 `state/req-status.json` 这个文件里。这是一个非常务实的设计选择——没有用数据库，没有用 Redis，就是一个 JSON 文件。好处是：任何人都能直接打开文件看当前状态，随手改一个字段就能干预流程，进程挂了重启后从文件读状态继续。

每条需求记录大概长这样：

```json
{
  "req_id": "REQ-03",
  "title": "实现 API 客户端",
  "blocked_by": ["REQ-02"],
  "state": "READY",
  "retries": 0,
  "max_retries": 3,
  "branch": "feat/req-03-api-client",
  "pr_number": null,
  "last_error": null
}
```

`blocked_by` 字段实现了需求之间的依赖管理。比如 REQ-03 依赖 REQ-02，那在 REQ-02 变成 DONE 之前，REQ-03 就一直是 PENDING，不会被启动。编排器每轮都会自动检查依赖，把满足条件的 PENDING 需求推进到 READY。

这个状态文件和项目的需求文档是对应的。在 `docs/requirements.md` 里，团队把产品拆成了两个 Phase：Phase 1 是最小可用版本，包含 REQ-01 到 REQ-18 的核心需求；Phase 2 是功能完善版，补齐编辑工具、Markdown 渲染、会话持久化等进阶功能。每个 REQ 都有明确的功能规格、交付物清单、Review 检查项和验收标准。

---

## 五、Orchestrator：编排引擎怎么推进状态

`orchestrator.py` 大约 430 行代码，是整个自动化系统的大脑。它的核心逻辑其实很简单：**根据当前状态，决定下一步做什么**。

核心方法 `_advance(req)` 的伪代码大概是这样的：

```python
def _advance(self, req):
    if req.state == READY or req.state == FIXING:
        # 调用 Dev Agent 写代码
        self._run_development(req)

    elif req.state == DEVELOPING:
        # 再次校验门禁，通过则推进到 REVIEWING
        self._validate_and_review(req)

    elif req.state == REVIEWING:
        # 调用 Review Agent 或等真人审批
        self._run_review(req)

    elif req.state == TESTING:
        # 调用 QA Agent 或等真人评论
        self._run_qa(req)

    # 全部通过 → gh pr merge → DONE
```

失败处理也很清晰：每个 REQ 有独立的 `retries` 计数，每次失败加一，超过 `max_retries` 就标记为 BLOCKED。而且系统能区分"瞬时错误"（网络超时、API 限流）和"实质错误"（代码编译不过），对瞬时错误会放宽重试计数。

从 CLI 的角度，`run-once` 推进一个 REQ 一步，`run-all` 就是在循环里反复调用 `run-once`，直到所有 READY 和 FIXING 状态的 REQ 都处理完。

---

## 六、Dev Agent：AI 怎么写代码

这是整个系统里最复杂也最有意思的部分。Dev Agent 基于 CrewAI 框架构建，代码在 `dev_crew.py`，大约 200 行。

CrewAI 的核心概念是 Agent + Task + Tool。Dev Agent 被赋予了一个"高级开发工程师"的角色，它的任务描述会包含需求文档的内容、当前分支信息等上下文。然后它可以调用一套精心设计的工具链来完成开发工作：

**文件操作工具：**
- `repo_read_file(path)` — 读取仓库文件
- `repo_write_file(path, content)` — 写入文件
- `repo_read_requirement(req_id)` — 根据 REQ-ID 读需求文档

**Git 操作工具：**
- `git_status()` — 查看当前工作区状态
- `git_changed_files_against_default()` — 看改了哪些文件
- `git_commits_ahead_of_default()` — 看领先多少提交
- `git_stage_all()` — 暂存所有变更
- `git_commit_msg(message)` — 提交

**质量与交付工具：**
- `run_local_quality_gates()` — 跑 ruff + pytest + coverage
- `git_push_branch()` — 推送到 GitHub
- `github_open_pull_request(title, body)` — 创建 PR

Dev Agent 的典型工作流程是这样的：

1. 先调用 `repo_read_requirement()` 读取需求文档，理解要做什么
2. 读取相关的现有代码文件，理解当前代码结构
3. **先写测试**，再写实现代码——系统鼓励 TDD 风格
4. 调用 `run_local_quality_gates()` 跑门禁
5. 如果没通过，根据错误信息修改代码，重新跑
6. 通过后，`git_stage_all()` → `git_commit_msg()` → `git_push_branch()` → `github_open_pull_request()`

这里有一个强制性的检查：编排器会验证 `tests/` 目录下是否有新增或修改的文件。如果 Dev Agent 只写了功能代码没写测试，直接打回。这相当于在架构层面强制推行了测试先行的开发实践。

每个 REQ 的开发工作在独立的 Git Worktree 里进行。Git Worktree 允许你在同一个仓库里同时 checkout 多个分支到不同目录，互不干扰。这样既不会污染主分支，也为将来并行处理多个 REQ 留出了空间。

---

## 七、质量门禁：AI 写的代码必须过三关

`gates.py` 只有 61 行，但它是整个系统质量保障的关键。门禁按顺序执行三步：

**第一关：`ruff format`** — 自动格式化代码。这一步不会失败，它会直接修正代码风格问题。

**第二关：`ruff check`** — 静态代码检查。检测未使用的变量、导入问题、潜在的 bug 等。如果有问题，返回具体的错误行号和原因。

**第三关：`pytest`** — 跑单元测试，同时要求覆盖率达标（默认 50%，可以通过 `COVERAGE_MIN` 环境变量调高到 80%）。每次测试都会生成 JUnit XML 和 Coverage XML 报告。

任何一步失败，`gates.py` 返回 `GateResult(passed=False, output="...")`，失败日志会反馈给 Dev Agent，让它根据信息修复。

这就是"确定性优先"在实践中的体现：**门禁结果不依赖 LLM 的判断**。ruff 说有问题就是有问题，pytest 说不通过就是不通过，没有模糊空间。

---

## 八、多角色多账号：模拟真实团队

这是这个项目我觉得最有前瞻性的设计之一。MasterCoder 用不同的 GitHub 账号来扮演不同的团队角色：

| 角色 | 对应环境变量 | 职责 |
|------|-------------|------|
| 开发 Agent | `GIT_AGENT_TOKEN_DEV` | 写代码、push 分支、创建 PR |
| Review Agent | `GIT_AGENT_TOKEN_REVIEW` | 审查代码和测试用例、给 PR 点 Approve 或 Request changes |
| 测试 Agent | `GIT_AGENT_TOKEN_TEST` | QA 验收、在 PR 下评论 QA_PASSED 或 QA_FAILED |
| 合并 Agent | `GIT_AGENT_TOKEN_MERGE` | 合并 PR（可选，缺失时用 Dev 账号）|

在 GitHub 上看 PR 的历史，你会看到不同的账号分别执行了创建、审查、评论和合并操作——就像一个真实的三人团队在协作。这不是为了好看，它有几个实际价值：

第一，**符合 GitHub 的权限模型**。GitHub 不允许 PR 创建者自己审批自己的 PR（在启用分支保护的情况下）。用不同账号就天然满足了这个约束。

第二，**可审计**。出了问题可以追溯是哪个角色在哪一步做了什么决定。

第三，**权限隔离**。Dev 账号有代码推送权限，Review 账号有审批权限，但它们不需要互相持有对方的权限。

团队文档里记录了三个实际使用的 GitHub 账号：开发 Agent 用 youmiss@163.com，Review Agent 用 gaobiedongtian@163.com，测试 Agent 用 xiangsilian@gmail.com。每个账号都需要仓库的 Write 权限，PAT 通过环境变量注入，绝不明文存储。

---

## 九、Review 和 QA：两种模式灵活切换

审查和测试环节是这个项目在"人机协作"上最见功力的设计。它支持两种模式：

### 默认模式：LLM 自动审查

Review 阶段分两步：先做代码审查（`review_decision()`），再做测试用例审查（`review_test_cases_decision()`）。两步都通过后，系统用 Review 账号的 PAT 调用 `gh pr review --approve` 或 `gh pr review --request-changes`。

QA 阶段类似，`qa_decision()` 让 LLM 基于门禁日志和代码变更做出 QA 决策，然后用 Test 账号的 PAT 发 PR 评论。

这些 LLM 调用的输出格式是严格的 JSON，编排器会解析 JSON 中的 `verdict` 字段来决定通过还是打回，而不是去"理解" LLM 的自然语言回复。这又是确定性设计的一个体现。

### 严格真人模式：等待人类操作

设置环境变量 `AUTOMATION_STRICT_HUMAN_REVIEW=1` 后，系统不会调用 LLM 做审查。取而代之的是，它会启动一个轮询循环，每 30 秒检查一次 GitHub API，看 Review 账号对应的人类用户是否在 PR 上点了 Approve 或 Request changes。超时时间默认 3600 秒（一小时），超时后 REQ 会被标记为 BLOCKED。

QA 的严格真人模式类似，等待 Test 账号的人类用户在 PR 下发一条以 `QA_PASSED` 或 `QA_FAILED` 开头的评论。

这两种模式可以自由组合：Review 用 LLM 自动审、QA 用真人验收，或者全自动，或者全人工。你对 AI 有多信任，就给它多少自主权——而不是只有"全自动"或"全手动"两个极端选项。

---

## 十、客户端的技术细节：不只是套壳

产品层虽然不是整个项目最核心的部分，但它的实现质量也相当不错。几个值得聊的技术点：

### 系统提示词构建

`system_prompt.py` 负责拼接最终发给 LLM 的系统提示词。拼接顺序是：

1. 内置角色提示词（"You are MasterCoder, an AI programming assistant..."）
2. `MASTERCODER.md` 的内容（如果项目根目录下有这个文件）
3. Git 仓库信息（当前分支、最近的 commit、工作区状态等）
4. 用户自定义提示词（如果配置了）

`MASTERCODER.md` 有 50KB 的大小限制，超过会截断。截断时还会小心地处理 UTF-8 多字节字符的边界——逐字节往前回退，直到找到合法的 UTF-8 起始字节。这种细节虽然不起眼，但说明开发者考虑了中文用户的场景。

### 上下文管理：@引用语法

用户可以在对话中用 `@src/config.py` 的语法引用文件。系统会解析这些引用，读取文件内容，检测编程语言，然后以 Markdown 代码块的格式附加到消息里。

引用的文件会经过完整的安全检查：路径沙箱验证（防止 `../` 逃逸出工作目录）、文件大小限制（不超过 1MB）、二进制文件检测（检查前 8KB 有没有 null 字节）、读权限检查。每条消息最多引用 10 个文件。

更贴心的是，它还实现了 Tab 补全——输入 `@src/` 后按 Tab，会列出该目录下的文件和子目录供你选择。这用的是 Python 标准库的 `readline` 模块。

### 安全层

安全设计分两层：

`security/sandbox.py` 做路径隔离，确保所有文件操作都在项目目录内。任何试图通过 `../` 或绝对路径访问项目外文件的操作都会被拦截。

`security/commands.py` 维护一个危险命令黑名单，包括 `rm -rf`、`dd`、`mkfs` 等。AI 调用 `run_command` 时，命令会先经过黑名单匹配，命中就直接拒绝。

除此之外，API Key 也有保护——不会明文显示在终端界面中，不会写入对话历史或日志文件。

### 工具调用的确认机制

当 AI 决定调用工具时（比如写一个文件），客户端会先把操作内容展示给用户，提供三个选项：

- **Yes**：执行这次操作
- **No**：拒绝这次操作
- **Always**：本次会话内后续不再询问，全部自动执行

还有一个 `auto_approve` 配置项可以直接跳过确认。这个分级确认机制在"安全"和"效率"之间找到了不错的平衡点。

---

## 十一、需求文档设计：AI 能看懂的需求

这个项目的需求文档写法本身就值得学习。每个 REQ 都包含以下几部分：

- **需求描述**：用人话说清楚要做什么
- **功能规格**：编号列出具体的功能点，精确到行为细节
- **交付物**：明确列出要交付的文件和测试
- **Review 检查项**：给 Review Agent 用的 checklist
- **验收标准**：给 QA Agent 用的验收条件

举个例子，REQ-01（项目脚手架与入口程序）的功能规格精确到："启动后在终端打印欢迎信息""显示输入提示符 `> `""用户输入空行时不做任何处理，重新显示 `> `"。

这种精度的需求文档不是为人写的——人看着会觉得太啰嗦。但对 AI Agent 来说，模糊的需求是灾难性的，精确的规格才是它能正确工作的前提。

需求之间有明确的依赖关系，通过 `blocked_by` 字段管理。Phase 1 和 Phase 2 的分期也很清晰：先做最小可用版本（能对话、能调用三个核心工具、有基本安全），再迭代完善（补齐工具、加渲染、加会话持久化）。

---

## 十二、CI/CD：从本地到流水线

项目提供了 GitHub Actions 的配置模板（`.github/workflows/automation-pipeline.yml`），可以在 CI 环境里跑自动化流水线。

但文档很诚实地指出了几个需要额外处理的问题：

1. 所有 PAT 和 API Key 都需要配置到 GitHub Secrets 里
2. `GITHUB_TOKEN` 的默认权限可能不够——推送新分支和合并 PR 需要额外授权
3. 严格真人模式下，CI 会长时间等待人类操作，需要调整超时设置
4. 状态文件的回写需要 push 权限

文档的结论是：**Actions 文件是起点模板，上生产前要按组织安全策略补全 Secret 和权限**。

这个态度我很欣赏——没有吹嘘"开箱即用"，而是把已知的边界条件都列出来了。

---

## 十三、测试策略：务实主义

项目有 30+ 个测试文件，覆盖了核心模块。但不是所有模块都有单元测试。

`dev_crew.py`、`crew_agents.py`、`pr_human_gate.py` 这三个模块被明确排除在覆盖率统计之外。原因很简单：它们强依赖真实的 LLM API 和 GitHub 环境，单元测试的 mock 写起来意义不大。

取而代之的是两个冒烟测试脚本：

- `scripts/crewai_glm_smoke.py` — 测试 LLM 连通性（期望返回含 "pong" 的响应）
- `scripts/crewai_github_pat_smoke.py` — 测试三个 PAT 是否有效

这是一个很务实的测试策略：**区分"可以有效单测的模块"和"需要集成测试的模块"，分别处理**。不为了覆盖率数字而写没有意义的 mock，该单测的单测，该冒烟的冒烟。

---

## 十四、整体数据流：串起来看

最后，我们把所有组件串成一条完整的数据流：

```
docs/requirements.md      ← 需求来源
        ↓
state/req-status.json     ← 状态管理
        ↓
Orchestrator._advance()   ← 状态推进
        ↓
┌───────────────────────────────────────────────────┐
│  DEVELOPING 阶段                                    │
│  1. 创建 Git Worktree，切换到功能分支              │
│  2. Dev Agent（CrewAI）读需求 → 写测试 → 写代码   │
│  3. run_local_quality_gates()                      │
│     ├── ruff format（格式化）                       │
│     ├── ruff check（静态检查）                      │
│     └── pytest + coverage（测试 + 覆盖率）          │
│  4. git push → gh pr create                        │
└───────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────┐
│  REVIEWING 阶段                                     │
│  - 默认：LLM 审查代码 + 测试用例 → gh pr review   │
│  - 严格：轮询等待真人在 GitHub 上点 Approve        │
│  （使用 Review 账号 PAT）                          │
└───────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────┐
│  TESTING 阶段                                       │
│  - 默认：LLM QA 决策 → gh pr comment              │
│  - 严格：等待真人评论 QA_PASSED / QA_FAILED        │
│  （使用 Test 账号 PAT）                            │
└───────────────────────────────────────────────────┘
        ↓
gh pr merge（使用 Merge 账号 PAT）
        ↓
state = DONE，保存到 req-status.json
```

整个过程的关键特性：

- **幂等**：任何一步失败，重新运行不会产生副作用
- **可中断可恢复**：状态全在 JSON 文件里，随时可以停下来，随时可以继续
- **可人工干预**：直接编辑 JSON 文件就能改变流程走向
- **错误隔离**：一个 REQ 失败不影响其他 REQ

---

## 十五、这个项目教会我们什么

聊到最后，总结几个我觉得最有价值的经验：

**第一，AI 系统的可靠性不来自更强的模型，而来自更好的约束。** MasterCoder 没有用最贵最好的模型，它默认用的是智谱 GLM。但通过门禁、状态机、类型化输出这些工程手段，它把 LLM 的不确定性控制在了一个安全的范围内。LLM 可以犯错，但错误会被门禁拦住、被重试机制消化，不会像滚雪球一样传导到下游。

**第二，状态持久化的简单方案往往是最好的方案。** JSON 文件做状态存储，很多人会觉得"不够高级"。但对于这个场景，它完美地满足了所有需求：可读、可编辑、可版本控制、无需额外基础设施。如果一开始就上 PostgreSQL 或 Redis，反而增加了部署复杂度和调试难度。

**第三，人机协作需要连续的信任光谱，而不是非此即彼的开关。** MasterCoder 通过严格真人模式的灵活配置，让团队可以根据自己的信任程度，逐步放宽 AI 的自主权。刚开始用的时候可以全部真人审批，跑一段时间建立信任后，再逐步切换到 LLM 自动审查。这比"全自动"或"全手动"两个极端要务实得多。

**第四，需求文档的精度决定 AI 自动化的上限。** 如果需求写得含糊，AI Agent 再强也没用。MasterCoder 的需求文档精确到每一个 API 的行为、每一个边界条件、每一个验收标准——这才是 AI 能正确执行的前提。

**第五，多角色多账号不是花架子。** 它解决了真实的权限审计问题，满足了 GitHub 的分支保护规则，让整个流程在合规性上站得住脚。

当然，项目也有它的局限：强绑定 GitHub（换 GitLab 需要改不少代码）、LLM 主要对接智谱（虽然理论上兼容所有 OpenAI 协议）、大的复杂需求可能超出单次 Crew 的处理能力需要手动拆分。

但作为一个展示"AI Agent 如何与软件工程流程深度结合"的参考实现，MasterCoder 是我见过最完整的开源项目之一。不管你是想做类似的 AI 工程化项目，还是想理解 AI Agent 的架构设计，这个项目都非常值得读一读源码。

好了，今天的内容就到这里。如果你觉得有收获，请点赞关注收藏三连。有问题欢迎在评论区讨论。

我们下期再见。

---

*文档版本：v1.0 | 对应项目提交：19ff773*
