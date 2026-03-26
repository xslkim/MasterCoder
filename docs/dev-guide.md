# MasterCoder - 开发指导手册

> 本文档指导开发工程师、Review 工程师、测试工程师按照标准化流程完成 MasterCoder 项目的全部需求开发。

---

## 1. 项目信息

### 1.1 仓库地址

```
https://github.com/xslkim/MasterCoder.git
```

### 1.2 团队账号

| 角色 | GitHub 账号（邮箱） |
|------|---------------------|
| 开发工程师 | youmiss@163.com |
| Review 工程师 | gaobiedongtian@163.com |
| 测试工程师 | xiangsilian@gmail.com |

> 密码请通过内部安全渠道获取，不在本文档中明文记录。

---

## 2. Git 分支策略与协作流程

### 2.1 分支命名规范

| 分支类型 | 命名格式 | 示例 |
|----------|----------|------|
| 主分支 | `main` | `main` |
| 需求开发分支 | `feat/req-<编号>-<简要描述>` | `feat/req-01-project-scaffold` |
| Bug 修复分支 | `fix/req-<编号>-<简要描述>` | `fix/req-01-signal-handling` |

### 2.2 单个需求的完整开发流程

```
┌──────────────────────────────────────────────────────────────────────┐
│                       需求开发生命周期                                │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ① 开发工程师                                                        │
│     ├─ 从 main 创建分支: feat/req-XX-xxx                             │
│     ├─ 编写功能代码 + 单元测试                                        │
│     ├─ 本地验证单元测试全部通过                                        │
│     ├─ 推送分支到远程仓库                                             │
│     └─ 创建 Pull Request → 指派 Review 工程师                        │
│           │                                                          │
│  ② Review 工程师                                                     │
│     ├─ 在 PR 中逐项检查 Review 检查项                                 │
│     ├─ 提出修改意见（Comment / Request Changes）                      │
│     ├─ 开发工程师修复后重新 Review                                     │
│     └─ 全部通过后 Approve PR                                         │
│           │                                                          │
│  ③ 测试工程师                                                        │
│     ├─ 拉取 PR 分支到本地                                             │
│     ├─ 按验收标准逐项执行测试                                         │
│     ├─ 编写测试报告（通过/不通过 + Bug 描述）                          │
│     ├─ 不通过 → 在 PR 中提 Issue，开发工程师修复后重测                  │
│     └─ 全部通过 → 在 PR 中 Comment "QA Passed"                       │
│           │                                                          │
│  ④ 合并                                                              │
│     └─ Review Approved + QA Passed → 合并 PR 到 main                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.3 Git 操作速查

**开发工程师 — 创建分支并开始开发：**
```bash
git checkout main
git pull origin main
git checkout -b feat/req-01-project-scaffold
# ... 编写代码 ...
git add <files>
git commit -m "feat(req-01): implement project scaffold and REPL entry"
git push origin feat/req-01-project-scaffold
# 在 GitHub 上创建 PR
```

**测试工程师 — 拉取 PR 分支进行测试：**
```bash
git fetch origin
git checkout feat/req-01-project-scaffold
# ... 执行验收测试 ...
```

### 2.4 Commit Message 规范

```
<type>(req-<编号>): <简要描述>

<可选的详细说明>
```

| type | 含义 |
|------|------|
| `feat` | 新功能实现 |
| `fix` | Bug 修复 |
| `test` | 测试代码 |
| `refactor` | 重构（不影响功能） |
| `docs` | 文档变更 |

### 2.5 Pull Request 规范

PR 标题格式：`[REQ-XX] <需求简称>`

PR 描述模板：
```markdown
## 需求编号
REQ-XX

## 变更说明
- 简要描述本次变更内容

## 交付物清单
- [ ] 功能代码
- [ ] 单元测试
- [ ] 单元测试通过截图/日志

## Review 检查项
（从需求文档复制对应 Review 检查项）

## 验收标准
（从需求文档复制对应验收标准）
```

---

## 3. 项目目录结构约定

以下为项目建议目录结构（REQ-01 中创建，后续需求在此基础上扩展）：

```
MasterCoder/
├── docs/                          # 文档目录
│   ├── product-spec.md            # 产品文档
│   ├── requirements.md            # 需求文档
│   └── dev-guide.md               # 本开发指导手册
├── src/                           # 源码目录
│   ├── main.py                    # 程序入口（REQ-01）
│   ├── config.py                  # 配置系统（REQ-02）
│   ├── api_client.py              # API 客户端（REQ-03）
│   ├── message_manager.py         # 消息管理器（REQ-04）
│   ├── chat_loop.py               # 对话循环（REQ-05）
│   ├── tools/                     # 工具模块目录
│   │   ├── __init__.py
│   │   ├── registry.py            # 工具注册器（REQ-06）
│   │   ├── executor.py            # 工具执行引擎（REQ-07）
│   │   ├── read_file.py           # read_file 工具（REQ-08）
│   │   ├── write_file.py          # write_file 工具（REQ-09）
│   │   ├── edit_file.py           # edit_file 工具（REQ-10）
│   │   ├── list_files.py          # list_files 工具（REQ-11）
│   │   ├── search_files.py        # search_files 工具（REQ-12）
│   │   └── run_command.py         # run_command 工具（REQ-13）
│   ├── security.py                # 安全与权限（REQ-15）
│   ├── renderer.py                # Markdown 渲染（REQ-16）
│   ├── ui.py                      # 状态栏与 Spinner（REQ-17）
│   ├── commands.py                # 斜杠命令（REQ-18）
│   ├── project_config.py          # 项目级配置（REQ-19）
│   ├── session.py                 # 会话持久化（REQ-20）
│   ├── input_handler.py           # 多行输入（REQ-21）
│   ├── context.py                 # 上下文管理（REQ-22）
│   ├── retry.py                   # 重试机制（REQ-23）
│   ├── cli.py                     # 命令行参数（REQ-24）
│   └── git_info.py                # Git 感知（REQ-25）
├── tests/                         # 测试目录
│   ├── test_config.py
│   ├── test_api_client.py
│   ├── test_message_manager.py
│   ├── test_chat_loop.py
│   ├── tools/
│   │   ├── test_registry.py
│   │   ├── test_executor.py
│   │   ├── test_read_file.py
│   │   ├── test_write_file.py
│   │   ├── test_edit_file.py
│   │   ├── test_list_files.py
│   │   ├── test_search_files.py
│   │   └── test_run_command.py
│   ├── test_security.py
│   ├── test_renderer.py
│   ├── test_commands.py
│   ├── test_session.py
│   ├── test_retry.py
│   ├── test_cli.py
│   └── test_git_info.py
├── test_reports/                   # 测试报告目录（测试工程师产出）
│   ├── REQ-01_report.md
│   ├── REQ-02_report.md
│   └── ...
├── pyproject.toml                 # 项目依赖配置
├── README.md                      # 项目说明
└── MASTERCODER.md                 # 项目指令文件（REQ-19 中使用）
```

> 注：上述目录以 Python 为示例，实际开发语言由团队决定，结构需保持对应关系。

---

## 4. 需求开发任务分解

下表汇总每个需求点三个角色的具体产出物、涉及文件和进度状态。

### 进度标记说明

| 标记 | 含义 |
|------|------|
| `[ ]` | 未开始 |
| `[D]` | 开发中 |
| `[R]` | Review 中 |
| `[T]` | 测试中 |
| `[F]` | 已修复（Review/测试打回后修复） |
| `[✓]` | 已完成并合并 |

---

### REQ-01：项目脚手架与入口程序

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 功能代码 + 单元测试 | `src/main.py`, `pyproject.toml`, `README.md`, `tests/test_main.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-01_report.md` |

**开发工程师操作步骤：**
1. 从 `main` 创建分支 `feat/req-01-project-scaffold`
2. 创建项目目录结构：`src/`、`tests/`、`docs/`
3. 创建 `pyproject.toml`，定义项目名称、版本（`0.1.0`）、依赖
4. 实现 `src/main.py`：
   - 欢迎信息打印（`MasterCoder v0.1.0`）
   - REPL 循环：读取输入 → 原样回显 → 下一轮
   - 空行跳过
   - `/exit` 退出
   - `Ctrl+C`（SIGINT）信号处理，打印 `Goodbye!` 退出
5. 编写 `tests/test_main.py`：
   - 测试启动输出欢迎信息
   - 测试空输入不回显
   - 测试 `/exit` 正常退出
6. 本地运行 `pytest tests/test_main.py` 确认全部通过
7. 推送并创建 PR `[REQ-01] 项目脚手架与入口程序`

**Review 工程师检查项：**
```
- [ ] 项目目录结构清晰，职责分明
- [ ] pyproject.toml 完整（名称、版本、依赖、入口点）
- [ ] 入口函数逻辑简洁，REPL 循环无阻塞泄漏
- [ ] Ctrl+C 信号处理正确，无线程泄漏
```

**测试工程师验收步骤：**
```bash
# 1. 拉取分支
git checkout feat/req-01-project-scaffold

# 2. 安装依赖并构建
pip install -e .

# 3. 逐项验收
mastercoder                     # 验证欢迎信息和提示符
# 输入 "hello" 回车             # 验证回显
# 直接回车                      # 验证空行跳过
# 输入 "/exit"                  # 验证退出，检查 exit code: echo $?
mastercoder                     # 再次启动
# 按 Ctrl+C                    # 验证退出

# 4. 运行单元测试
pytest tests/test_main.py -v

# 5. 填写测试报告 test_reports/REQ-01_report.md
```

**进度：** `[ ]`

---

### REQ-02：配置系统（全局 + 环境变量）

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 配置加载模块 + 单元测试 | `src/config.py`, `tests/test_config.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-02_report.md` |

**开发工程师操作步骤：**
1. 从 `main` 创建分支 `feat/req-02-config-system`
2. 实现 `src/config.py`：
   - 定义 `Config` 数据类/结构体，包含 7 个字段及默认值
   - 实现 `load_config()` 函数：读取 `~/.mastercoder/config.json` → 合并环境变量
   - JSON 解析异常处理：打印错误信息并 `sys.exit(1)`
   - 字段范围校验：`max_tokens`（1~100000）、`temperature`（0.0~2.0）
   - API Key 脱敏方法：`sk-****<后4位>`
3. 编写 `tests/test_config.py`（使用临时目录和环境变量 mock）：
   - 无配置文件 → 默认值
   - 正常配置文件解析
   - 环境变量 `MASTERCODER_API_KEY` 覆盖配置文件
   - 非法 JSON → 报错退出
   - `temperature: 5.0` → 警告 + 使用默认值
4. 在 `src/main.py` 启动时调用 `load_config()`
5. 推送并创建 PR `[REQ-02] 配置系统`

**Review 工程师检查项：**
```
- [ ] 配置优先级实现正确：环境变量 > 配置文件 > 默认值
- [ ] api_key 不在任何用户可见输出中明文展示
- [ ] 配置文件路径使用 pathlib.Path.home() 或等效的平台无关方式
- [ ] 字段校验完整，类型不匹配时有合理错误信息
- [ ] 无硬编码路径
```

**测试工程师验收步骤：**
```bash
# 1. 拉取分支并安装
git checkout feat/req-02-config-system && pip install -e .

# 2. 验收：无配置文件
rm -f ~/.mastercoder/config.json
mastercoder    # 应正常启动使用默认值

# 3. 验收：正常配置文件
mkdir -p ~/.mastercoder
echo '{"api_key":"sk-test123","model":"deepseek-chat"}' > ~/.mastercoder/config.json
mastercoder    # 内部配置应为 deepseek-chat

# 4. 验收：环境变量覆盖
MASTERCODER_API_KEY=sk-envkey mastercoder   # api_key 应为 sk-envkey

# 5. 验收：非法 JSON
echo '{bad}' > ~/.mastercoder/config.json
mastercoder    # 应报错退出，exit code 1

# 6. 验收：字段超范围
echo '{"temperature": 5.0}' > ~/.mastercoder/config.json
mastercoder    # 应打印警告，使用默认值 0.0

# 7. 运行单元测试
pytest tests/test_config.py -v

# 8. 填写测试报告
```

**进度：** `[ ]`

---

### REQ-03：OpenAI 兼容 API 客户端

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | API 客户端模块 + 类型定义 + 单元测试 | `src/api_client.py`, `tests/test_api_client.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-03_report.md` |

**开发工程师操作步骤：**
1. 从 `main` 创建分支 `feat/req-03-api-client`
2. 定义类型：`Message`、`ToolCall`、`ChatResponse`、`StreamDelta`
3. 实现 `APIClient` 类：
   - `__init__(base_url, api_key, model, max_tokens, temperature)` — 初始化
   - `chat(messages, tools=None, stream=True)` — 发送请求
   - 非流式：解析 `choices[0].message.content` 和 `tool_calls`
   - 流式：SSE 解析，`data: {...}` → delta 回调，`data: [DONE]` → 结束
   - 流式 tool_calls 拼接：跨多个 delta 拼接 `function.arguments`
   - HTTP 错误码映射（401/404/429/500+）
   - 120 秒请求超时
4. 编写 `tests/test_api_client.py`（使用 `pytest` + Mock HTTP Server）：
   - 测试非流式正常请求
   - 测试流式请求的 delta 回调和最终拼接
   - 测试流式 tool_calls 解析
   - 测试各错误码处理
   - 测试网络超时
   - 测试非法 JSON 响应
5. 推送并创建 PR `[REQ-03] API 客户端`

**Review 工程师检查项：**
```
- [ ] Authorization header 正确拼接，无多余空格
- [ ] 流式解析健壮：处理空行、注释行、非标准前缀
- [ ] 工具调用参数保持为 JSON 字符串，不在此层解析
- [ ] 超时和错误码映射完整
- [ ] 无 API Key 硬编码或泄漏到日志
```

**测试工程师验收步骤：**
```bash
# 主要依赖单元测试（Mock Server），逐项检查测试覆盖率
pytest tests/test_api_client.py -v --tb=short

# 可选：配置真实 API 进行手动冒烟测试
# python -c "from src.api_client import APIClient; ..."
```

**进度：** `[ ]`

---

### REQ-04：对话消息管理器

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 消息管理器模块 + 单元测试 | `src/message_manager.py`, `tests/test_message_manager.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-04_report.md` |

**开发工程师操作步骤：**
1. 从 `main` 创建分支 `feat/req-04-message-manager`
2. 实现 `MessageManager` 类：
   - `add_message(role, content, tool_calls=None, tool_call_id=None)`
   - `get_messages()` → 返回消息列表
   - `clear()` → 清空（保留 system）
   - `get_token_estimate()` → `总字符数 / 4`
   - `prepare_messages(max_context_tokens)` → 返回 `(messages, truncated)`
3. 截断逻辑：跳过 index 0（system），从 index 1 开始逐条删除最旧消息
4. 编写 `tests/test_message_manager.py`：全部 5 个测试场景
5. 推送并创建 PR `[REQ-04] 消息管理器`

**Review 工程师检查项：**
```
- [ ] system 消息在任何情况下都不会被截断
- [ ] 截断操作返回副本，不修改原始消息列表
- [ ] Token 估算逻辑集中在一个方法中，便于后续替换
- [ ] 消息字段定义支持 tool_calls 和 tool_call_id
```

**测试工程师验收步骤：**
```bash
pytest tests/test_message_manager.py -v
# 验证全部 5 个场景的断言
```

**进度：** `[ ]`

---

### REQ-05：基础对话循环（接入 AI）

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 对话循环串联代码 + 集成测试 | `src/chat_loop.py`, `src/main.py`（修改）, `tests/test_chat_loop.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-05_report.md` |

**开发工程师操作步骤：**
1. 从 `main` 创建分支 `feat/req-05-chat-loop`
2. 定义内置 system prompt 常量（见需求文档）
3. 实现 `ChatLoop` 类，串联 Config → MessageManager → APIClient：
   - 启动时检查 `api_key` 非空
   - 用户输入 → `add_message("user", ...)` → `prepare_messages()` → `api_client.chat(stream=True)` → 流式输出到终端
   - 流结束 → `add_message("assistant", ...)` → 下一轮
   - API 报错 → 红色 `Error: ...`，不存入消息列表
   - `Ctrl+C` 中断流式 → 保存部分回复 → `[Interrupted]`
4. 修改 `src/main.py`，将 REPL 回显替换为 `ChatLoop` 调用
5. 编写 `tests/test_chat_loop.py`（Mock API Server）
6. 推送并创建 PR `[REQ-05] 基础对话循环`

**Review 工程师检查项：**
```
- [ ] 流式输出每个 delta 立即写入 stdout，无缓冲
- [ ] 多轮对话消息角色交替正确
- [ ] 错误不污染消息列表
- [ ] Ctrl+C 中断后程序状态正常
- [ ] API key 为空时启动检查在配置加载后立即执行
```

**测试工程师验收步骤：**
```bash
# 需要真实或 Mock API 进行手动测试
# 1. 配置有效 API Key，测试正常对话
# 2. 测试多轮对话上下文保持
# 3. 配置错误 API Key，测试错误展示
# 4. 不配置 API Key，测试启动报错退出
# 5. 流式输出中 Ctrl+C 中断测试
pytest tests/test_chat_loop.py -v
```

**进度：** `[ ]`

---

### REQ-06：工具定义与注册框架

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 工具接口 + 注册器 + 单元测试 | `src/tools/__init__.py`, `src/tools/registry.py`, `tests/tools/test_registry.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-06_report.md` |

**开发工程师操作步骤：**
1. 从 `main` 创建分支 `feat/req-06-tool-framework`
2. 在 `src/tools/__init__.py` 中定义 `Tool` 抽象基类/接口：
   - 属性：`name`、`description`、`parameters`（JSON Schema dict）
   - 方法：`execute(params: dict) -> str`
3. 实现 `src/tools/registry.py`：
   - `ToolRegistry` 类
   - `register(tool)` — 重复注册抛 `ValueError("Tool already registered: <name>")`
   - `get_tool(name)` — 未找到返回 `None`
   - `get_openai_tools_schema()` — 返回 OpenAI tools 格式列表
4. 编写 `tests/tools/test_registry.py`：4 个测试场景
5. 推送并创建 PR `[REQ-06] 工具定义框架`

**进度：** `[ ]`

---

### REQ-07：工具调用执行引擎

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 执行引擎 + 确认交互 + 测试 | `src/tools/executor.py`, `tests/tools/test_executor.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-07_report.md` |

**开发工程师操作步骤：**
1. 从 `main` 创建分支 `feat/req-07-tool-executor`
2. 实现 `ToolExecutor` 类：
   - `execute_tool_calls(tool_calls, registry, auto_approve)` — 主入口
   - 用户确认流程：展示工具信息 → 读取 Y/N/A 输入
   - 工具执行 + 异常捕获
   - 结果封装为 `tool` 角色消息
   - 嵌套调用计数，最大深度 20
3. 编写 `tests/tools/test_executor.py`：8 个测试场景
4. 推送并创建 PR `[REQ-07] 工具调用引擎`

**进度：** `[ ]`

---

### REQ-08 ~ REQ-13：六个工具实现（可并行）

> 以下 6 个需求之间**无依赖关系**，可同时开发。每个工具一个分支、一个 PR。

#### REQ-08：read_file

| 阶段 | 产出物 | 涉及文件 |
|------|--------|----------|
| 开发 | read_file 工具 + 测试 | `src/tools/read_file.py`, `tests/tools/test_read_file.py` |
| Review | PR Review | GitHub PR |
| 测试 | 测试报告 | `test_reports/REQ-08_report.md` |

分支：`feat/req-08-read-file`

开发要点：
- 路径解析（相对 → 绝对）
- UTF-8 读取
- 错误：不存在 / 权限 / 二进制（前 8192 字节含 null）/ 超 1MB
- 返回格式 `"File: <path>\n\n<content>"`

验收要点：6 个测试场景（见需求文档）

**进度：** `[ ]`

---

#### REQ-09：write_file

| 阶段 | 产出物 | 涉及文件 |
|------|--------|----------|
| 开发 | write_file 工具 + 测试 | `src/tools/write_file.py`, `tests/tools/test_write_file.py` |
| Review | PR Review | GitHub PR |
| 测试 | 测试报告 | `test_reports/REQ-09_report.md` |

分支：`feat/req-09-write-file`

开发要点：
- 自动递归创建父目录
- UTF-8 写入，返回字节数
- 错误：路径是目录 / 权限不足

**进度：** `[ ]`

---

#### REQ-10：edit_file

| 阶段 | 产出物 | 涉及文件 |
|------|--------|----------|
| 开发 | edit_file 工具 + 测试 | `src/tools/edit_file.py`, `tests/tools/test_edit_file.py` |
| Review | PR Review | GitHub PR |
| 测试 | 测试报告 | `test_reports/REQ-10_report.md` |

分支：`feat/req-10-edit-file`

开发要点：
- 纯字符串匹配（非正则）
- 必须唯一匹配
- 错误：未找到 / 多处匹配（含数量）/ old == new

**进度：** `[ ]`

---

#### REQ-11：list_files

| 阶段 | 产出物 | 涉及文件 |
|------|--------|----------|
| 开发 | list_files 工具 + 测试 | `src/tools/list_files.py`, `tests/tools/test_list_files.py` |
| Review | PR Review | GitHub PR |
| 测试 | 测试报告 | `test_reports/REQ-11_report.md` |

分支：`feat/req-11-list-files`

开发要点：
- 支持 glob `*` `**` 语法
- 目录加 `/` 后缀，字母序排序
- 最多 500 条结果

**进度：** `[ ]`

---

#### REQ-12：search_files

| 阶段 | 产出物 | 涉及文件 |
|------|--------|----------|
| 开发 | search_files 工具 + 测试 | `src/tools/search_files.py`, `tests/tools/test_search_files.py` |
| Review | PR Review | GitHub PR |
| 测试 | 测试报告 | `test_reports/REQ-12_report.md` |

分支：`feat/req-12-search-files`

开发要点：
- 正则搜索，逐行匹配
- 跳过 `.git`、`node_modules`、`__pycache__`、`.venv`、`venv`
- 跳过二进制文件
- 最多 100 条，单行超 200 字符截断

**进度：** `[ ]`

---

#### REQ-13：run_command

| 阶段 | 产出物 | 涉及文件 |
|------|--------|----------|
| 开发 | run_command 工具 + 测试 | `src/tools/run_command.py`, `tests/tools/test_run_command.py` |
| Review | PR Review | GitHub PR |
| 测试 | 测试报告 | `test_reports/REQ-13_report.md` |

分支：`feat/req-13-run-command`

开发要点：
- `subprocess` + `sh -c`，设置工作目录
- stdout/stderr 分别捕获，各限 50000 字符
- 超时 SIGKILL 终止进程组
- 空命令拒绝

**进度：** `[ ]`

---

### REQ-14：工具调用集成 — 端到端对话

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 集成代码 + 端到端测试 | `src/chat_loop.py`（修改）, `src/main.py`（修改）, `tests/test_integration.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-14_report.md` |

分支：`feat/req-14-tool-integration`

**开发工程师操作步骤：**
1. 在 `main.py` 启动时注册全部 6 个工具到 `ToolRegistry`
2. `ChatLoop` 中 API 请求携带 `tools=registry.get_openai_tools_schema()`
3. 检测 AI 响应中的 `tool_calls` → 调用 `ToolExecutor`
4. 展示状态提示：`[Executing: ...]`、`[Done: ...]`、`[Failed: ...]`
5. 编写端到端集成测试（Mock API Server 返回 tool_calls → 工具执行 → 二次请求 → 最终回复）

**测试工程师重点验收：**
- 真实或 Mock API 下，让 AI 读取文件、执行命令、编辑文件的完整流程
- 拒绝工具调用后 AI 的替代回复
- 多工具连续调用场景

**进度：** `[ ]`

---

### REQ-15：安全与权限控制

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 安全模块 + 单元测试 | `src/security.py`, `tests/test_security.py`, 各工具文件（修改） |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-15_report.md` |

分支：`feat/req-15-security`

**开发工程师操作步骤：**
1. 实现 `src/security.py`：
   - `check_path_sandbox(path, working_dir)` — 解析绝对路径 + 符号链接后检查是否在沙箱内
   - `check_command_blacklist(command)` — 子串匹配黑名单
   - `is_destructive_operation(tool_name, params)` — 敏感操作检测
2. 在各文件工具（read/write/edit/list/search）的 `execute()` 方法开头调用 `check_path_sandbox()`
3. 在 `run_command` 的 `execute()` 方法开头调用 `check_command_blacklist()`
4. 在工具执行器的确认界面中集成 `is_destructive_operation()` 警告展示

**测试工程师重点验收：**
```bash
# 路径穿越测试
# 让 AI 读取 ../../etc/passwd → 应返回 Access denied

# 符号链接测试
ln -s /etc/passwd ./evil_link
# 让 AI 读取 evil_link → 应返回 Access denied

# 命令黑名单测试
# 让 AI 执行 "rm -rf /" → 应返回 Command blocked

# 正常操作不被拦截
# 让 AI 执行 "ls -la" → 应正常返回
```

**进度：** `[ ]`

---

### REQ-16：Markdown 渲染与代码高亮

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 渲染模块 + 高亮 + Diff + 测试 | `src/renderer.py`, `tests/test_renderer.py`, `src/chat_loop.py`（修改） |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-16_report.md` |

分支：`feat/req-16-markdown-renderer`

**开发工程师操作步骤：**
1. 实现 `src/renderer.py`：
   - `MarkdownRenderer` 类，接收文本输出 ANSI 渲染结果
   - `StreamRenderer` 类，逐片段接收并渲染（代码块缓冲到闭合后一次性输出）
   - `render_diff(old_text, new_text)` — unified diff 格式，红绿色
   - 终端能力检测：`os.isatty(1)` + `TERM` 环境变量
2. 语法高亮：推荐使用 `pygments` 库的 `TerminalFormatter`
3. 在 `ChatLoop` 的流式输出中替换为 `StreamRenderer`
4. 在 `edit_file` 执行后调用 `render_diff()`

**进度：** `[ ]`

---

### REQ-17：状态栏与 Token 统计

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | UI 模块 + 测试 | `src/ui.py`, `tests/test_ui.py`, `src/chat_loop.py`（修改） |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-17_report.md` |

分支：`feat/req-17-statusbar-tokens`

**开发工程师操作步骤：**
1. 实现 `src/ui.py`：
   - `build_prompt(model, cwd, git_branch)` → 格式化提示符字符串
   - `Spinner` 类：后台线程 braille 动画，`start(text)` / `stop()`
   - `format_token_stats(round_input, round_output, total_input, total_output)` → 灰色统计行
2. Git 分支检测：`subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], ...)` 超时 2 秒

**进度：** `[ ]`

---

### REQ-18：斜杠命令系统

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 命令解析器 + 各命令实现 + 测试 | `src/commands.py`, `tests/test_commands.py`, `src/main.py`（修改） |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-18_report.md` |

分支：`feat/req-18-slash-commands`

**开发工程师操作步骤：**
1. 实现 `src/commands.py`：
   - `CommandParser` 类：解析 `/` 开头输入
   - 注册 5 个命令：`/help`、`/clear`、`/model`、`/config`、`/exit`
   - 命令名大小写不敏感
2. 在 REPL 主循环中，优先于 AI 消息发送进行斜杠命令检测

**进度：** `[ ]`

---

### REQ-19：项目级配置与 MASTERCODER.md

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 项目配置加载 + prompt 拼接 + 测试 | `src/project_config.py`, `src/config.py`（修改）, `tests/test_project_config.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-19_report.md` |

分支：`feat/req-19-project-config`

**进度：** `[ ]`

---

### REQ-20：会话持久化与恢复

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 会话模块 + /sessions 命令 + 测试 | `src/session.py`, `src/commands.py`（修改）, `tests/test_session.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-20_report.md` |

分支：`feat/req-20-session-persistence`

**开发工程师操作步骤：**
1. 实现 `src/session.py`：
   - `SessionManager` 类
   - `save(session_id, messages, metadata)` — 原子写入 JSON
   - `load(session_id)` → 消息列表
   - `get_latest()` → 最近一个会话
   - `list_sessions(limit=20)` → 按 `updated_at` 降序
2. 在 `ChatLoop` 每轮结束后调用 `save()`
3. 添加 `--resume` 启动参数
4. 添加 `/sessions` 斜杠命令

**进度：** `[ ]`

---

### REQ-21：多行输入与输入历史

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 输入处理模块 + 测试 | `src/input_handler.py`, `tests/test_input_handler.py`, `src/main.py`（修改） |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-21_report.md` |

分支：`feat/req-21-multiline-input`

**进度：** `[ ]`

---

### REQ-22：上下文管理 — 手动添加文件

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | @ 引用解析 + Tab 补全 + 测试 | `src/context.py`, `tests/test_context.py`, `src/chat_loop.py`（修改） |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-22_report.md` |

分支：`feat/req-22-file-context`

**进度：** `[ ]`

---

### REQ-23：错误处理与重试机制

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | 重试模块 + 日志模块 + 测试 | `src/retry.py`, `src/api_client.py`（修改）, `tests/test_retry.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-23_report.md` |

分支：`feat/req-23-error-retry`

**开发工程师操作步骤：**
1. 实现 `src/retry.py`：
   - `retry_with_backoff(func, max_retries=3, retryable_codes=[429,500,502,503])` — 装饰器/包裹函数
   - 指数退避：1s → 2s → 4s
   - 终端打印 `[Retrying... attempt N/3]`
2. 全局异常处理：在 `main.py` REPL 循环中 try/except 兜底
3. 日志模块：追加写入 `~/.mastercoder/error.log`，超 5MB 截断保留 2MB

**进度：** `[ ]`

---

### REQ-24：命令行参数与启动选项

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | CLI 模块 + 非交互模式 + 测试 | `src/cli.py`, `src/main.py`（修改）, `tests/test_cli.py` |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-24_report.md` |

分支：`feat/req-24-cli-args`

**开发工程师操作步骤：**
1. 使用 `argparse` 或 `click` 实现参数解析
2. 参数：`-m/--model`、`--api-key`、`--api-url`、`-y/--auto-approve`、`-r/--resume`、`-v/--version`、`-h/--help`、`--no-color`
3. 非交互模式：`not sys.stdin.isatty()` → 读取 stdin → 单次回复 → 退出
4. 优先级链：命令行 > 环境变量 > 项目配置 > 全局配置 > 默认值

**进度：** `[ ]`

---

### REQ-25：Git 仓库感知增强

| 阶段 | 负责人 | 产出物 | 涉及文件 |
|------|--------|--------|----------|
| 开发 | 开发工程师 | Git 信息模块 + 测试 | `src/git_info.py`, `tests/test_git_info.py`, `src/chat_loop.py`（修改） |
| Review | Review 工程师 | PR Review 意见 | GitHub PR Comment |
| 测试 | 测试工程师 | 测试报告 | `test_reports/REQ-25_report.md` |

分支：`feat/req-25-git-awareness`

**开发工程师操作步骤：**
1. 实现 `src/git_info.py`：
   - `is_git_repo()` → bool
   - `get_branch()` → str | None
   - `get_status_summary()` → str（最多 20 行）
   - `get_recent_commits(count=5)` → str
   - 所有 git 命令超时 2 秒
2. 启动时收集 Git 信息并追加到 system 消息
3. 提示符刷新时调用 `get_branch()`

**进度：** `[ ]`

---

## 5. 测试报告模板

测试工程师对每个需求点执行验收后，在 `test_reports/` 目录下创建报告文件。

文件命名：`REQ-XX_report.md`

模板内容：

```markdown
# REQ-XX 测试报告

## 基本信息
- 需求编号：REQ-XX
- 需求名称：<名称>
- 测试日期：YYYY-MM-DD
- 测试分支：feat/req-xx-xxx
- 测试工程师：xiangsilian@gmail.com

## 单元测试
- 执行命令：`pytest tests/test_xxx.py -v`
- 通过数：X
- 失败数：X
- 结果：通过 / 不通过

## 验收测试

| 序号 | 验收标准 | 结果 | 备注 |
|------|----------|------|------|
| 1 | <从需求文档复制> | 通过/不通过 | <失败原因或截图> |
| 2 | ... | ... | ... |

## Bug 列表（如有）

| Bug 编号 | 描述 | 严重级别 | 状态 |
|----------|------|----------|------|
| BUG-XX-01 | ... | 高/中/低 | 待修复/已修复/已关闭 |

## 最终结论
- [ ] 通过：全部验收标准满足，可合并
- [ ] 不通过：存在未解决 Bug，需修复后重测
```

---

## 6. 进度总览表

| 需求 | 名称 | 分支 | 开发 | Review | 测试 | 状态 |
|------|------|------|------|--------|------|------|
| REQ-01 | 项目脚手架 | `feat/req-01-project-scaffold` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-02 | 配置系统 | `feat/req-02-config-system` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-03 | API 客户端 | `feat/req-03-api-client` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-04 | 消息管理器 | `feat/req-04-message-manager` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-05 | 基础对话循环 | `feat/req-05-chat-loop` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-06 | 工具定义框架 | `feat/req-06-tool-framework` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-07 | 工具调用引擎 | `feat/req-07-tool-executor` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-08 | read_file | `feat/req-08-read-file` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-09 | write_file | `feat/req-09-write-file` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-10 | edit_file | `feat/req-10-edit-file` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-11 | list_files | `feat/req-11-list-files` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-12 | search_files | `feat/req-12-search-files` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-13 | run_command | `feat/req-13-run-command` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-14 | 工具集成 | `feat/req-14-tool-integration` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-15 | 安全与权限 | `feat/req-15-security` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-16 | Markdown 渲染 | `feat/req-16-markdown-renderer` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-17 | 状态栏与统计 | `feat/req-17-statusbar-tokens` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-18 | 斜杠命令 | `feat/req-18-slash-commands` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-19 | 项目级配置 | `feat/req-19-project-config` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-20 | 会话持久化 | `feat/req-20-session-persistence` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-21 | 多行输入 | `feat/req-21-multiline-input` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-22 | 手动添加上下文 | `feat/req-22-file-context` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-23 | 错误处理与重试 | `feat/req-23-error-retry` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-24 | 命令行参数 | `feat/req-24-cli-args` | `[ ]` | `[ ]` | `[ ]` | 未开始 |
| REQ-25 | Git 感知 | `feat/req-25-git-awareness` | `[ ]` | `[ ]` | `[ ]` | 未开始 |

---

## 7. 并行开发建议

根据需求依赖关系，推荐以下开发批次：

### 第一批（串行，打地基）
```
REQ-01 → REQ-02 → REQ-03 → REQ-04 → REQ-05
```
这 5 个需求是全部后续功能的基础，必须按顺序完成。

### 第二批（工具框架 + 六工具并行）
```
REQ-06 → REQ-07（串行）
REQ-08 ~ REQ-13（可并行，均只依赖 REQ-06）
```
REQ-06 完成后，REQ-07 与 REQ-08~13 可同时开展。

### 第三批（集成 + 安全）
```
REQ-14（等 REQ-05 + REQ-07 + REQ-08~13 全部完成）
REQ-15（等 REQ-08~13 全部完成）
```

### 第四批（UI 增强 + 扩展功能，可并行）
```
REQ-16  Markdown 渲染      ← 依赖 REQ-05
REQ-17  状态栏与统计        ← 依赖 REQ-05
REQ-18  斜杠命令            ← 依赖 REQ-01
REQ-19  项目级配置          ← 依赖 REQ-02
REQ-20  会话持久化          ← 依赖 REQ-04
REQ-21  多行输入            ← 依赖 REQ-01
REQ-22  手动添加上下文      ← 依赖 REQ-05 + REQ-08
REQ-23  错误处理与重试      ← 依赖 REQ-03
REQ-24  命令行参数          ← 依赖 REQ-02
REQ-25  Git 感知            ← 依赖 REQ-17
```
其中 REQ-16~24（除 REQ-25）互不依赖，可根据人力并行。REQ-25 等 REQ-17 完成后开始。

---

## 8. 注意事项

### 8.1 安全
- **绝对禁止**在代码中硬编码 API Key
- **绝对禁止**将 `~/.mastercoder/config.json` 提交到 Git 仓库
- 在 `.gitignore` 中添加：
  ```
  .mastercoder/
  *.log
  test_reports/
  ```

### 8.2 代码规范
- 代码风格统一：使用 `black` 格式化（Python）或团队约定的 linter
- 所有公开方法需有 docstring
- 变量命名使用 `snake_case`
- 常量使用 `UPPER_SNAKE_CASE`

### 8.3 测试规范
- 单元测试覆盖率目标：**80%** 以上
- 每个需求的单元测试必须随功能代码一起提交
- 使用临时目录进行文件操作测试，测试后清理
- Mock 外部依赖（API 请求、文件系统）以保证测试稳定性

### 8.4 沟通机制
- 开发工程师提交 PR 后，在 PR 中 @ Review 工程师
- Review 通过后，在 PR 中 @ 测试工程师
- Bug 通过 GitHub Issue 跟踪，标签格式 `bug/req-XX`
- 紧急问题通过内部即时通讯工具直接沟通
