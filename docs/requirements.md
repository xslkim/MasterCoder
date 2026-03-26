# MasterCoder - 需求文档

> 本文档基于 [product-spec.md](./product-spec.md) 产品文档编写，按开发顺序排列需求点。
> 每个需求点均需经过 **开发编码 → Code Review → 测试** 三个阶段。

---

## 交付分期

### Phase 1（最小可用版本 v0.1.0）

Phase 1 目标：实现一个可以对话、调用工具、有基本安全防护的命令行 AI 编程客户端。

**包含需求：**
- REQ-01 ~ REQ-07：项目脚手架、配置、API 客户端、消息管理器、对话循环、工具框架、工具执行引擎
- REQ-08（read_file）、REQ-09（write_file）、REQ-13（run_command）：三个核心工具
- REQ-15：最小安全能力（路径沙箱 + 命令黑名单，不含敏感操作高亮）
- REQ-18：最小命令集（`/help`、`/clear`、`/model`、`/exit`，不含 `/config`）

**Phase 1 交付标准：**
- 用户可通过 `mastercoder` 启动，与 AI 多轮对话
- AI 可调用 read_file、write_file、run_command 三个工具
- 文件操作受沙箱限制，危险命令被拦截
- 斜杠命令可控制会话

### Phase 2（功能完善版本）

Phase 1 全部完成并合并后，开展以下需求：
- REQ-10（edit_file）、REQ-11（list_files）、REQ-12（search_files）：补齐剩余工具
- REQ-14：端到端工具集成
- REQ-15 完整版：敏感操作高亮提醒
- REQ-16 ~ REQ-17：Markdown 渲染、状态栏与 Token 统计
- REQ-18 完整版：补齐 `/config` 命令
- REQ-19 ~ REQ-25：项目配置、会话持久化、多行输入、上下文管理、错误重试、命令行参数、Git 感知

---

## 角色定义

| 角色 | 职责 |
|------|------|
| **开发工程师** | 按需求点进行编码实现，编写单元测试，提交代码 |
| **Review 工程师** | 审查代码质量、架构合理性、安全性、规范一致性 |
| **测试工程师** | 按验收标准执行功能测试、边界测试、回归测试，输出测试报告 |

## 通用流程定义

每个需求点的交付流程如下：

```
开发工程师提交代码 + 单元测试
       ↓
Review 工程师审查代码（通过 / 打回）
       ↓
测试工程师执行验收测试（通过 / 提 Bug）
       ↓
需求点关闭
```

---

## REQ-01：项目脚手架与入口程序

### 需求描述

创建 MasterCoder 项目的基础工程结构和可执行入口。用户在终端输入 `mastercoder` 命令后，程序启动并进入交互式 REPL（Read-Eval-Print Loop）循环，等待用户输入。

### 功能规格

1. 程序通过命令行启动，命令名为 `mastercoder`
2. 启动后在终端打印欢迎信息，格式如下：
   ```
   MasterCoder v0.1.0
   Type /help for available commands, /exit to quit.
   ```
3. 打印欢迎信息后，显示输入提示符 `> `，等待用户键入文本
4. 用户输入文本后按回车，程序暂时将输入内容原样回显（后续需求接入 AI），然后再次显示 `> ` 等待下一轮输入
5. 用户输入 `/exit` 或按 `Ctrl+C` 时，程序打印 `Goodbye!` 并正常退出（exit code 0）
6. 用户输入空行（直接回车）时，不做任何处理，重新显示 `> `

### 交付物

- 项目目录结构（含 `README.md`、依赖配置文件、源码入口文件）
- 可执行的入口程序
- 单元测试：覆盖启动、空输入跳过、`/exit` 退出三个场景

### Review 检查项

- [ ] 项目目录结构清晰，职责分明
- [ ] `pyproject.toml` 完整（项目名、版本、依赖、`[project.scripts]` 入口点）
- [ ] 入口函数逻辑简洁，REPL 循环无阻塞泄漏
- [ ] `Ctrl+C`（SIGINT）信号处理正确，无线程泄漏

### 验收标准

- [ ] 执行 `mastercoder` 命令后，终端显示欢迎信息和输入提示符
- [ ] 输入任意文本回车后，文本被原样回显，再次出现提示符
- [ ] 输入空行后，直接出现新的提示符，无多余输出
- [ ] 输入 `/exit` 后程序退出，exit code 为 0
- [ ] 按 `Ctrl+C` 后程序退出，exit code 为 0
- [ ] 单元测试全部通过

---

## REQ-02：配置系统（全局 + 环境变量）

### 需求描述

实现配置加载模块。程序启动时自动读取全局配置文件和环境变量，解析出 API 连接参数和运行参数。配置优先级为：**环境变量 > 全局配置文件 > 默认值**。

### 功能规格

1. 全局配置文件路径为 `~/.mastercoder/config.json`
2. 配置文件为 JSON 格式，包含以下字段（均为可选，有默认值）：

   | 字段 | 类型 | 默认值 | 说明 |
   |------|------|--------|------|
   | `api_base_url` | string | `"https://api.openai.com/v1"` | API 端点地址 |
   | `api_key` | string | `""` | API 密钥 |
   | `model` | string | `"gpt-4o"` | 模型名称 |
   | `max_tokens` | integer | `4096` | 单次回复最大 token 数，范围 1~100000 |
   | `temperature` | float | `0.0` | 生成温度，范围 0.0~2.0 |
   | `auto_approve` | boolean | `false` | 是否自动批准工具调用 |
   | `system_prompt` | string | `""` | 自定义系统提示词，为空则使用内置默认 |

3. 环境变量映射关系：

   | 环境变量 | 对应配置项 |
   |----------|-----------|
   | `MASTERCODER_API_BASE_URL` | `api_base_url` |
   | `MASTERCODER_API_KEY` | `api_key` |
   | `MASTERCODER_MODEL` | `model` |

4. 当配置文件不存在时，使用全部默认值，不报错
5. 当配置文件存在但 JSON 格式非法时，程序打印错误信息 `Error: Invalid config file at ~/.mastercoder/config.json: <具体解析错误>` 并以 exit code 1 退出
6. `max_tokens` 和 `temperature` 超出合法范围时，打印警告 `Warning: <字段名> value <值> out of range, using default <默认值>` 并使用默认值
7. 程序启动时在日志（非用户可见界面）中记录最终生效的配置（`api_key` 字段脱敏显示为 `sk-****<后4位>`）

### 交付物

- 配置加载模块源码
- 配置结构体/类型定义
- 单元测试：覆盖以下场景
  - 无配置文件时使用默认值
  - 正常解析配置文件
  - 环境变量覆盖配置文件
  - JSON 格式非法时报错退出
  - 字段值超出范围时使用默认值并打印警告

### Review 检查项

- [ ] 配置优先级实现正确：环境变量 > 配置文件 > 默认值
- [ ] 敏感字段（`api_key`）不在任何用户可见输出中明文展示
- [ ] 配置文件路径使用平台无关的 home 目录解析方式
- [ ] 字段校验完整，类型不匹配时有合理错误信息
- [ ] 无硬编码路径

### 验收标准

- [ ] 无 `~/.mastercoder/config.json` 文件时，程序正常启动并使用默认值
- [ ] 创建配置文件写入 `{"api_key":"sk-test123","model":"deepseek-chat"}`，启动后内部配置为对应值
- [ ] 设置环境变量 `MASTERCODER_API_KEY=sk-envkey`，即使配置文件中有 `api_key`，最终生效的也是环境变量的值
- [ ] 配置文件写入非法 JSON `{bad}`，启动后打印错误信息并退出，exit code 为 1
- [ ] 配置文件写入 `{"temperature": 5.0}`，启动后打印警告并使用默认值 0.0
- [ ] 单元测试全部通过

---

## REQ-03：OpenAI 兼容 API 客户端

### 需求描述

实现与 OpenAI Chat Completions API 兼容的 HTTP 客户端模块。该模块负责将对话消息发送给模型服务端，并接收返回结果。支持普通请求和流式（Streaming）请求两种模式。

### 功能规格

1. 请求端点：`POST {api_base_url}/chat/completions`
2. 请求头：
   - `Content-Type: application/json`
   - `Authorization: Bearer {api_key}`
3. 请求体结构：
   ```json
   {
     "model": "<配置的模型名称>",
     "messages": [
       {"role": "system", "content": "..."},
       {"role": "user", "content": "..."},
       {"role": "assistant", "content": "..."}
     ],
     "max_tokens": 4096,
     "temperature": 0.0,
     "stream": true,
     "tools": [...]
   }
   ```
4. **非流式模式**：发送请求，等待完整响应返回，解析 `choices[0].message.content` 作为 AI 回复
5. **流式模式**（默认）：
   - 请求体设置 `"stream": true`
   - 接收 SSE（Server-Sent Events）格式的响应
   - 每收到一个 `data: {...}` 事件，解析 `choices[0].delta.content`，通过回调函数逐片段传出
   - 收到 `data: [DONE]` 时标记流结束
   - 将所有片段拼接后作为完整回复返回
6. **工具调用识别**：当响应中 `choices[0].message.tool_calls`（非流式）或 `choices[0].delta.tool_calls`（流式）存在时，解析出工具调用列表，每个工具调用包含 `id`、`function.name`、`function.arguments`（JSON 字符串）
7. **错误处理**：
   - HTTP 状态码 401：返回错误 `Authentication failed: invalid API key`
   - HTTP 状态码 404：返回错误 `Model not found: <model name>`
   - HTTP 状态码 429：返回错误 `Rate limit exceeded, please retry later`
   - HTTP 状态码 500+：返回错误 `Server error: <status code>`
   - 网络连接失败：返回错误 `Connection failed: <具体原因>`
   - 响应体 JSON 解析失败：返回错误 `Invalid response format from API`
8. 请求超时设置为 120 秒

### 交付物

- API 客户端模块源码
- 消息类型定义（Message、ToolCall、APIResponse 等）
- 单元测试（使用 Mock HTTP Server）：
  - 非流式正常请求与解析
  - 流式正常请求，验证片段逐个回调且最终拼接正确
  - 流式中包含工具调用的解析
  - 401/404/429/500 错误码处理
  - 网络超时处理
  - 非法 JSON 响应处理

### Review 检查项

- [ ] `Authorization` header 正确拼接，无多余空格
- [ ] 流式解析健壮：处理空行、注释行、非标准前缀
- [ ] 工具调用参数为 JSON 字符串，不在此层解析为具体参数（由上层工具执行器负责）
- [ ] 超时和错误码映射完整
- [ ] 无 API Key 硬编码或泄漏到日志

### 验收标准

- [ ] 使用 Mock Server，发送非流式请求后正确获取 `content` 字段内容
- [ ] 使用 Mock Server，发送流式请求后，回调函数按序收到每个 delta 片段，最终拼接结果与预期一致
- [ ] Mock Server 返回包含 `tool_calls` 的响应，客户端正确解析出工具名称和参数
- [ ] Mock Server 返回 401 时，客户端返回 `Authentication failed` 错误
- [ ] Mock Server 返回 429 时，客户端返回 `Rate limit exceeded` 错误
- [ ] Mock Server 模拟超时（超过 120 秒无响应），客户端返回连接超时错误
- [ ] 单元测试全部通过

---

## REQ-04：对话消息管理器

### 需求描述

实现对话消息的管理模块，维护当前会话的消息列表，支持添加不同角色的消息，并在上下文超长时进行截断处理。

### 功能规格

1. 维护一个有序消息列表，每条消息包含以下字段：
   - `role`: 取值为 `"system"` | `"user"` | `"assistant"` | `"tool"`
   - `content`: 字符串，消息文本内容
   - `tool_calls`: 可选，工具调用列表（仅 `assistant` 角色）
   - `tool_call_id`: 可选，工具调用结果 ID（仅 `tool` 角色）
2. 提供以下操作方法：
   - `add_message(role, content, ...)` — 追加一条消息
   - `get_messages()` — 返回当前完整消息列表
   - `clear()` — 清空所有消息（保留 system 消息）
   - `get_token_estimate()` — 返回当前消息列表的估算 token 数
3. **Token 估算规则**：以字符数 / 4 作为近似 token 数（简化实现，不依赖 tokenizer 库）
4. **上下文截断**：
   - 调用方在发送 API 请求前调用 `prepare_messages(max_context_tokens)` 方法
   - 该方法检查总 token 估算值是否超过 `max_context_tokens`
   - 若超出，从消息列表的**第二条**（跳过 index 0 的 system 消息）开始，逐条移除最早的消息，直到总量不超过限制
   - 返回截断后的消息副本（不修改原始列表）
   - 若截断发生，返回值中附带标记 `truncated: true`
5. `clear()` 调用后，仅保留 role 为 `"system"` 的消息

### 交付物

- 消息管理器模块源码
- 单元测试：
  - 添加各角色消息后 `get_messages()` 返回正确
  - `clear()` 后仅剩 system 消息
  - Token 估算值与字符数 / 4 一致
  - 超出上下文限制时截断行为正确（system 消息保留，最旧的非 system 消息优先移除）
  - 未超出限制时 `truncated` 为 false

### Review 检查项

- [ ] system 消息在任何情况下都不会被截断
- [ ] 截断操作返回副本，不修改原始消息列表
- [ ] Token 估算逻辑集中在一个方法中，便于后续替换为精确 tokenizer
- [ ] 消息字段定义清晰，支持 `tool_calls` 和 `tool_call_id` 扩展

### 验收标准

- [ ] 添加 1 条 system、3 条 user、3 条 assistant 消息后，`get_messages()` 返回 7 条，顺序正确
- [ ] 调用 `clear()` 后，`get_messages()` 返回 1 条（system）
- [ ] 1000 个字符的消息，`get_token_estimate()` 返回 250
- [ ] 设置 `max_context_tokens = 100`，当总量为 200 token 时，`prepare_messages` 返回截断后列表，首条仍为 system，`truncated` 为 true
- [ ] 设置足够大的 `max_context_tokens`，`prepare_messages` 返回完整列表，`truncated` 为 false
- [ ] 单元测试全部通过

---

## REQ-05：基础对话循环（接入 AI）

### 需求描述

将 REQ-01 的 REPL 循环、REQ-02 的配置系统、REQ-03 的 API 客户端、REQ-04 的消息管理器串联，实现用户与 AI 模型的基础对话功能。用户输入文本后，程序将其发送给模型，流式输出 AI 的回复。

### 功能规格

1. 程序启动时：
   - 加载配置（REQ-02）
   - 若 `api_key` 为空，打印 `Error: API key not configured. Set MASTERCODER_API_KEY or add api_key to ~/.mastercoder/config.json` 并以 exit code 1 退出
   - 初始化消息管理器，添加内置 system 消息（内容见下方）
   - 若配置中 `system_prompt` 非空，将其追加到 system 消息末尾
2. **内置 system 消息内容**：
   ```
   You are MasterCoder, an AI programming assistant. You help users with software development tasks including writing code, debugging, refactoring, and explaining code. You have access to tools that can read files, write files, edit files, search files, and run commands on the user's local machine. Always be helpful, concise, and accurate.
   ```
3. 用户输入文本后：
   - 将用户输入作为 `user` 消息添加到消息管理器
   - 调用 `prepare_messages()` 获取当前消息列表（含截断处理）
   - 若发生截断，在终端打印提示 `[Context truncated: earliest messages removed]`
   - 以流式模式调用 API 客户端
   - AI 回复的每个片段实时打印到终端（无换行缓冲，逐片段输出）
   - 流结束后，将完整回复作为 `assistant` 消息添加到消息管理器
   - 打印空行，然后显示输入提示符 `> `
4. **API 调用出错时**：
   - 在终端打印 `Error: <错误信息>`（红色文字，若终端支持）
   - 不将错误信息添加到消息列表
   - 显示 `> ` 等待用户下一轮输入
5. **流式输出期间**用户按 `Ctrl+C`：
   - 中断当前流式接收
   - 将已接收到的部分内容作为 `assistant` 消息添加到消息管理器
   - 打印 `\n[Interrupted]`
   - 显示 `> ` 等待下一轮输入（不退出程序）

### 交付物

- 主循环串联逻辑源码
- 内置 system prompt 定义
- 集成测试（使用 Mock API Server）：
  - 正常对话流程：输入 → 流式输出 → 下一轮输入
  - API 报错时的错误展示和恢复
  - 多轮对话的消息累积正确性
  - api_key 为空时的启动拒绝

### Review 检查项

- [ ] 流式输出无明显延迟缓冲（每个 delta 立即写入 stdout）
- [ ] 多轮对话消息角色交替正确（system, user, assistant, user, assistant...）
- [ ] 错误不会污染消息列表
- [ ] `Ctrl+C` 中断后程序状态正常，可继续对话
- [ ] API key 为空的检查在配置加载后立即执行

### 验收标准

- [ ] 配置有效的 API Key 和 base_url，输入 `hello` 后 AI 流式回复可见，回复结束后可继续输入
- [ ] 多轮对话中，AI 能引用前序对话内容（如第一轮说"我叫张三"，第二轮问"我叫什么"能正确回答）
- [ ] 配置错误的 API Key 后，输入任意文本，终端显示 `Error: Authentication failed: invalid API key`，可继续输入
- [ ] 不设置 API Key 时，程序启动直接报错退出
- [ ] 流式输出过程中按 `Ctrl+C`，输出中断，打印 `[Interrupted]`，可继续下一轮对话
- [ ] 集成测试全部通过

---

## REQ-06：工具定义与注册框架

### 需求描述

实现工具系统的基础框架。定义工具的统一接口规范，实现工具注册机制，以及将已注册工具转换为 OpenAI `tools` 参数格式的序列化方法。

### 功能规格

1. 每个工具需实现以下接口：
   - `name` — 工具名称（字符串，如 `"read_file"`）
   - `description` — 工具描述（字符串，供 AI 理解工具用途）
   - `parameters` — 参数定义（JSON Schema 格式）
   - `execute(params) -> result` — 执行方法，接收参数字典，返回执行结果字符串
2. 工具注册器：
   - 提供 `register(tool)` 方法，将工具实例注册到全局工具列表
   - 提供 `get_tool(name)` 方法，按名称查找已注册工具
   - 提供 `get_openai_tools_schema()` 方法，返回所有工具的 OpenAI `tools` 参数格式数组
3. OpenAI tools 参数格式示例：
   ```json
   [
     {
       "type": "function",
       "function": {
         "name": "read_file",
         "description": "Read the contents of a file at the given path",
         "parameters": {
           "type": "object",
           "properties": {
             "path": {
               "type": "string",
               "description": "The file path to read"
             }
           },
           "required": ["path"]
         }
       }
     }
   ]
   ```
4. 工具名称不允许重复注册，重复时抛出错误 `Tool already registered: <name>`

### 交付物

- 工具接口定义
- 工具注册器模块源码
- 单元测试：
  - 注册一个 mock 工具，`get_tool` 能正确返回
  - `get_openai_tools_schema()` 输出符合 OpenAI 格式
  - 重复注册同名工具时抛出错误
  - 未注册工具的 `get_tool` 返回 `None`

### Review 检查项

- [ ] 工具接口定义清晰，易于扩展新工具
- [ ] 序列化输出严格符合 OpenAI tools 参数 JSON Schema 规范
- [ ] 注册器线程安全（若语言需要考虑并发场景）
- [ ] 无循环依赖

### 验收标准

- [ ] 创建一个实现了工具接口的 mock 工具，注册后 `get_tool("mock")` 返回该工具
- [ ] `get_openai_tools_schema()` 输出的 JSON 可被 OpenAI API 的 `tools` 参数接受（格式校验）
- [ ] 再次注册同名工具时抛出 `Tool already registered: mock` 错误
- [ ] `get_tool("nonexistent")` 返回 `None`，不抛出异常
- [ ] 单元测试全部通过

---

## REQ-07：工具调用执行引擎

### 需求描述

实现工具调用的执行引擎。当 AI 返回的响应中包含 `tool_calls` 时，执行引擎解析工具调用请求，通过用户确认后执行工具，并将结果封装为 `tool` 角色消息返回给 AI 继续推理。

### 功能规格

1. **工具调用检测**：AI 响应解析后，检查是否存在 `tool_calls` 字段。若存在，进入工具调用流程而非直接展示文本回复。
2. **用户确认流程**（`auto_approve` 为 false 时）：
   - 终端展示工具调用信息，格式：
     ```
     Tool call: read_file
     Arguments:
       path: "/home/user/project/main.py"

     [Y]es / [N]o / [A]lways >
     ```
   - 用户输入 `Y` 或 `y` 或直接回车：执行该工具
   - 用户输入 `N` 或 `n`：跳过该工具，向 AI 返回 `Tool call was rejected by user`
   - 用户输入 `A` 或 `a`：执行该工具，并将 `auto_approve` 设为 true（本次会话内后续不再询问）
3. **`auto_approve` 为 true 时**：跳过确认，直接执行工具
4. **工具执行**：
   - 根据 `function.name` 从工具注册器查找对应工具
   - 将 `function.arguments`（JSON 字符串）解析为参数字典
   - 调用工具的 `execute(params)` 方法，获取结果字符串
   - 若工具名称未找到，结果为 `Error: Unknown tool: <name>`
   - 若参数 JSON 解析失败，结果为 `Error: Invalid tool arguments: <解析错误>`
   - 若工具执行抛出异常，结果为 `Error: Tool execution failed: <异常信息>`
5. **结果回传**：
   - 将工具执行结果封装为 `tool` 角色消息，设置对应的 `tool_call_id`
   - 将 AI 的 assistant 消息（含 tool_calls）和 tool 结果消息都添加到消息管理器
   - 再次调用 API（携带完整消息列表），让 AI 基于工具结果继续回复
6. **多工具调用**：若 AI 一次返回多个 `tool_calls`，按顺序逐个执行上述流程
7. **嵌套调用**：AI 基于工具结果再次返回 `tool_calls` 时，重复执行工具调用流程。设置最大嵌套深度为 **20 次**，超过后向 AI 返回 `Error: Maximum tool call depth (20) exceeded` 并要求 AI 给出最终回复

### 交付物

- 工具调用执行引擎源码
- 用户确认交互逻辑
- 单元测试和集成测试：
  - 单个工具调用的完整流程（确认 → 执行 → 结果回传 → AI 继续回复）
  - 用户拒绝工具调用
  - auto_approve 模式
  - 用户选择 Always 后后续自动执行
  - 未知工具名称处理
  - 参数解析失败处理
  - 多工具调用顺序执行
  - 嵌套调用达到上限

### Review 检查项

- [ ] 确认提示信息清晰，用户能理解将要执行的操作
- [ ] tool_call_id 正确对应，不会错配
- [ ] 嵌套深度计数正确，边界条件无 off-by-one
- [ ] 工具执行异常被捕获，不会导致程序崩溃
- [ ] auto_approve 仅在当前会话有效，不持久化

### 验收标准

- [ ] AI 返回 `read_file` 工具调用时，终端展示确认提示，用户输入 `Y` 后工具执行，结果返回给 AI，AI 给出基于文件内容的回复
- [ ] 用户输入 `N` 后，AI 收到拒绝信息并给出替代回复
- [ ] 用户输入 `A` 后，后续工具调用不再弹出确认提示
- [ ] 配置 `auto_approve: true` 后，所有工具调用直接执行
- [ ] AI 返回不存在的工具名时，返回 `Error: Unknown tool` 且程序不崩溃
- [ ] 嵌套调用超过 20 次后，返回上限错误并终止循环
- [ ] 单元测试和集成测试全部通过

---

## REQ-08：工具实现 — read_file

### 需求描述

实现 `read_file` 工具，用于读取本地文件内容并返回给 AI。

### 功能规格

1. 工具名称：`read_file`
2. 工具描述：`"Read the contents of a file at the given path and return its text content"`
3. 参数定义：

   | 参数名 | 类型 | 必填 | 说明 |
   |--------|------|------|------|
   | `path` | string | 是 | 要读取的文件路径（绝对路径或相对于工作目录的相对路径） |

4. 执行逻辑：
   - 若 `path` 为相对路径，基于当前工作目录解析为绝对路径
   - 读取文件全部内容，以 UTF-8 编码解码为字符串
   - 返回格式：`"File: <绝对路径>\n\n<文件内容>"`
5. 错误处理：
   - 文件不存在：返回 `"Error: File not found: <path>"`
   - 无读取权限：返回 `"Error: Permission denied: <path>"`
   - 文件为二进制（包含 null 字节）：返回 `"Error: Cannot read binary file: <path>"`
   - 文件大小超过 1MB：返回 `"Error: File too large (>1MB): <path>"`

### 交付物

- `read_file` 工具实现源码
- 工具注册（在工具注册器中注册）
- 单元测试：
  - 读取正常文本文件
  - 相对路径解析
  - 文件不存在
  - 权限不足
  - 二进制文件检测
  - 超大文件拒绝

### Review 检查项

- [ ] 路径解析无目录穿越漏洞（`../../../etc/passwd` 等不应绕过安全检查——注：本需求暂无沙箱限制，REQ-15 中实现）
- [ ] UTF-8 解码失败时有合理兜底
- [ ] 文件大小检查在读取内容之前完成（先 stat 后 read）
- [ ] 二进制检测逻辑合理（检查前 8192 字节是否包含 null 字节）

### 验收标准

- [ ] 对项目中存在的 `.py` 等文本文件调用 `read_file`，返回完整内容
- [ ] 传入相对路径 `"src/mastercoder/main.py"`，返回基于工作目录的正确文件内容
- [ ] 传入不存在的路径，返回 `Error: File not found` 错误
- [ ] 对无读取权限的文件，返回 `Error: Permission denied` 错误
- [ ] 对二进制文件（如 `.png`），返回 `Error: Cannot read binary file` 错误
- [ ] 对超过 1MB 的文件，返回 `Error: File too large` 错误
- [ ] 单元测试全部通过

---

## REQ-09：工具实现 — write_file

### 需求描述

实现 `write_file` 工具，用于创建或覆写文件。

### 功能规格

1. 工具名称：`write_file`
2. 工具描述：`"Create a new file or overwrite an existing file with the given content"`
3. 参数定义：

   | 参数名 | 类型 | 必填 | 说明 |
   |--------|------|------|------|
   | `path` | string | 是 | 目标文件路径 |
   | `content` | string | 是 | 要写入的文件内容 |

4. 执行逻辑：
   - 若 `path` 为相对路径，基于工作目录解析为绝对路径
   - 若目标文件的父目录不存在，自动递归创建父目录
   - 以 UTF-8 编码写入 `content` 到目标文件
   - 若文件已存在则覆写
   - 返回格式：`"Successfully wrote <字节数> bytes to <绝对路径>"`
5. 错误处理：
   - 路径为目录（非文件）：返回 `"Error: Path is a directory: <path>"`
   - 无写入权限：返回 `"Error: Permission denied: <path>"`
   - 磁盘空间不足等 IO 错误：返回 `"Error: Write failed: <具体错误>"`

### 交付物

- `write_file` 工具实现源码
- 工具注册
- 单元测试：
  - 创建新文件（含父目录自动创建）
  - 覆写已有文件
  - 目标是目录
  - 权限不足

### Review 检查项

- [ ] 父目录创建使用安全的递归创建方式，创建的目录权限合理（0755）
- [ ] 写入操作为原子性或尽量接近原子性（先写临时文件再 rename，或框架保证）
- [ ] 字节数计算基于 UTF-8 编码后的实际字节数，非字符数
- [ ] 不会静默覆写符号链接指向的文件（跟随符号链接即可，但应注意）

### 验收标准

- [ ] 调用 `write_file` 写入新文件后，文件存在且内容正确
- [ ] 目标路径的父目录不存在时，自动创建父目录
- [ ] 覆写已有文件后，文件内容为新内容
- [ ] 返回的字节数与文件实际大小一致
- [ ] 路径指向已有目录时，返回 `Error: Path is a directory` 错误
- [ ] 单元测试全部通过

---

## REQ-10：工具实现 — edit_file

### 需求描述

实现 `edit_file` 工具，用于对已有文件进行精确的局部编辑（基于搜索替换）。

### 功能规格

1. 工具名称：`edit_file`
2. 工具描述：`"Make a targeted edit to a file by replacing an exact string match with new content"`
3. 参数定义：

   | 参数名 | 类型 | 必填 | 说明 |
   |--------|------|------|------|
   | `path` | string | 是 | 要编辑的文件路径 |
   | `old_string` | string | 是 | 要被替换的原始字符串（必须精确匹配） |
   | `new_string` | string | 是 | 替换后的新字符串 |

4. 执行逻辑：
   - 读取目标文件全部内容
   - 在文件内容中查找 `old_string` 的**精确匹配**（区分大小写，包括空白字符）
   - 若找到且**仅有一处匹配**，执行替换并写回文件
   - 返回格式：`"Successfully edited <绝对路径>"`
5. 错误处理：
   - 文件不存在：返回 `"Error: File not found: <path>"`
   - `old_string` 在文件中未找到：返回 `"Error: old_string not found in file"`
   - `old_string` 在文件中找到**多处匹配**：返回 `"Error: old_string has <N> matches, must be unique. Add more surrounding context to old_string to make it unique"`
   - `old_string` 与 `new_string` 相同：返回 `"Error: old_string and new_string are identical"`

### 交付物

- `edit_file` 工具实现源码
- 工具注册
- 单元测试：
  - 正常单处匹配替换
  - 未找到匹配
  - 多处匹配报错
  - old_string 与 new_string 相同
  - 包含特殊字符（换行、tab、引号等）的匹配

### Review 检查项

- [ ] 搜索逻辑为纯字符串匹配，非正则（避免 `old_string` 中的特殊字符被误解释）
- [ ] 替换后文件编码保持 UTF-8
- [ ] 文件写回为完整覆写（非追加）
- [ ] 多处匹配时报错信息包含匹配数量，帮助 AI 调整参数

### 验收标准

- [ ] 文件中有唯一匹配的字符串，替换后文件内容正确
- [ ] `old_string` 不存在于文件中时，返回未找到错误
- [ ] `old_string` 出现 3 次，返回 `Error: old_string has 3 matches` 错误
- [ ] `old_string` 与 `new_string` 相同时，返回 identical 错误
- [ ] 包含换行符的 `old_string` 能正确匹配和替换
- [ ] 单元测试全部通过

---

## REQ-11：工具实现 — list_files

### 需求描述

实现 `list_files` 工具，用于列出目录下的文件，支持 glob 模式匹配。

### 功能规格

1. 工具名称：`list_files`
2. 工具描述：`"List files in a directory, optionally filtered by a glob pattern"`
3. 参数定义：

   | 参数名 | 类型 | 必填 | 说明 |
   |--------|------|------|------|
   | `path` | string | 是 | 目标目录路径 |
   | `pattern` | string | 否 | Glob 过滤模式，默认 `"*"`（当前目录下所有文件）|

4. 执行逻辑：
   - 列出 `path` 目录下匹配 `pattern` 的文件和子目录
   - 支持标准 glob 语法：`*`（任意文件名）、`**`（递归子目录）、`*.py`（按扩展名）等
   - 结果按名称字母序排序
   - 每行一个路径，使用相对于 `path` 的相对路径
   - 目录名后加 `/` 后缀以区分文件
   - 返回格式：`"Directory: <绝对路径>\n\n<逐行文件列表>"`
   - 结果最多返回 **500 条**，超出时在末尾追加 `\n... and <剩余数量> more items`
5. 错误处理：
   - 路径不存在：返回 `"Error: Directory not found: <path>"`
   - 路径不是目录：返回 `"Error: Not a directory: <path>"`
   - 无读取权限：返回 `"Error: Permission denied: <path>"`

### 交付物

- `list_files` 工具实现源码
- 工具注册
- 单元测试：
  - 列出目录内容
  - glob 模式过滤（`*.py`、`**/*.js`）
  - 目录 `/` 后缀
  - 超过 500 条截断
  - 路径不存在 / 非目录

### Review 检查项

- [ ] glob 模式解析使用标准库或成熟第三方库
- [ ] `**` 递归不跟随符号链接（避免循环）
- [ ] 结果排序稳定，目录和文件混合排序
- [ ] 500 条限制在收集阶段即截断，不会先加载全部再截取

### 验收标准

- [ ] 对项目根目录执行 `list_files`，返回文件和子目录列表，目录名有 `/` 后缀
- [ ] `pattern: "*.md"` 仅返回 `.md` 文件
- [ ] `pattern: "**/*.py"` 递归返回所有 `.py` 文件
- [ ] 创建超过 500 个文件的临时目录，返回 500 条 + 截断提示
- [ ] 不存在的路径返回 `Error: Directory not found`
- [ ] 单元测试全部通过

---

## REQ-12：工具实现 — search_files

### 需求描述

实现 `search_files` 工具，用于在文件内容中搜索关键词或正则表达式。

### 功能规格

1. 工具名称：`search_files`
2. 工具描述：`"Search for a pattern in file contents within a directory"`
3. 参数定义：

   | 参数名 | 类型 | 必填 | 说明 |
   |--------|------|------|------|
   | `path` | string | 是 | 搜索的根目录路径 |
   | `pattern` | string | 是 | 搜索模式（支持正则表达式） |
   | `file_pattern` | string | 否 | 文件名过滤 glob，默认 `"*"`（所有文件）|

4. 执行逻辑：
   - 递归遍历 `path` 目录下匹配 `file_pattern` 的所有文本文件
   - 在每个文件中逐行搜索 `pattern`（正则匹配）
   - 跳过二进制文件（包含 null 字节的文件）
   - 跳过 `.git`、`node_modules`、`__pycache__`、`.venv`、`venv` 目录
   - 返回匹配结果，格式为：
     ```
     <相对路径>:<行号>: <该行内容>
     ```
   - 结果最多返回 **100 条匹配**，超出时在末尾追加 `\n... and <剩余数量> more matches`
5. 错误处理：
   - 路径不存在：返回 `"Error: Directory not found: <path>"`
   - 正则表达式非法：返回 `"Error: Invalid regex pattern: <pattern>"`
   - 无匹配结果：返回 `"No matches found for pattern '<pattern>' in <path>"`

### 交付物

- `search_files` 工具实现源码
- 工具注册
- 单元测试：
  - 正常搜索返回匹配行
  - 正则表达式搜索
  - 文件名过滤
  - 跳过二进制文件
  - 跳过排除目录
  - 超过 100 条截断
  - 无匹配结果
  - 非法正则

### Review 检查项

- [ ] 正则编译在搜索前完成，编译失败立即返回错误
- [ ] 文件读取使用逐行方式，不将大文件全部载入内存
- [ ] 排除目录列表可维护（集中定义在常量中）
- [ ] 行内容过长时截断显示（单行超过 200 字符时截断并加 `...`）

### 验收标准

- [ ] 在项目目录搜索 `"func main"` 或 `"def main"`，返回匹配的文件名、行号、行内容
- [ ] 使用正则 `"TODO|FIXME"` 搜索，返回所有 TODO 和 FIXME 标记
- [ ] `file_pattern: "*.py"` 限定仅搜索 Python 文件
- [ ] `.git` 目录和 `node_modules` 目录下的文件不出现在结果中
- [ ] 无匹配时返回 `No matches found`
- [ ] 传入非法正则 `"[invalid"` 时返回错误
- [ ] 单元测试全部通过

---

## REQ-13：工具实现 — run_command

### 需求描述

实现 `run_command` 工具，用于在用户本地执行 shell 命令并返回输出。

### 功能规格

1. 工具名称：`run_command`
2. 工具描述：`"Execute a shell command and return its output"`
3. 参数定义：

   | 参数名 | 类型 | 必填 | 说明 |
   |--------|------|------|------|
   | `command` | string | 是 | 要执行的 shell 命令 |
   | `timeout` | integer | 否 | 超时时间（秒），默认 120，范围 1~600 |

4. 执行逻辑：
   - 使用系统 shell 执行命令（Linux/macOS 用 `sh -c`，Windows 用 `cmd /c`）
   - 工作目录为用户启动 MasterCoder 时所在的目录
   - 捕获 stdout 和 stderr
   - 返回格式：
     ```
     Exit code: <退出码>

     STDOUT:
     <标准输出内容>

     STDERR:
     <标准错误内容>
     ```
   - stdout 或 stderr 为空时，对应部分显示 `(empty)`
   - stdout 和 stderr 各自超过 **50000 字符** 时，截断并在末尾添加 `\n... (truncated, showing first 50000 chars)`
5. **超时处理**：
   - 命令执行超过 `timeout` 指定秒数后，强制终止进程（发送 SIGKILL）
   - 返回：`"Error: Command timed out after <timeout> seconds"`
6. 错误处理：
   - shell 不可用：返回 `"Error: Shell not available"`
   - 命令为空字符串：返回 `"Error: Command cannot be empty"`

### 交付物

- `run_command` 工具实现源码
- 工具注册
- 单元测试：
  - 正常命令执行（如 `echo hello`）
  - 命令返回非零 exit code
  - stderr 输出
  - 超时终止
  - 输出截断
  - 空命令

### Review 检查项

- [ ] 进程启动使用 shell 包裹，支持管道、重定向等 shell 语法
- [ ] 超时后使用 SIGKILL 确保进程被终止，同时终止子进程组
- [ ] stdout/stderr 截断在读取阶段限制，不会先读取全部大输出再截断
- [ ] 命令执行不阻塞主进程的信号处理（如 `Ctrl+C` 仍可中断）
- [ ] 工作目录传入正确

### 验收标准

- [ ] 执行 `echo hello` 返回 exit code 0 和 stdout `hello`
- [ ] 执行 `ls nonexistent` 返回非零 exit code 和 stderr 错误信息
- [ ] 执行 `sleep 200` 并设置 `timeout: 2`，2 秒后返回超时错误
- [ ] 执行 `python -c "print('x' * 100000)"` 后 stdout 被截断至 50000 字符
- [ ] 空命令返回 `Error: Command cannot be empty`
- [ ] 单元测试全部通过

---

## REQ-14：工具调用集成 — 端到端对话

### 需求描述

将 REQ-06 ~ REQ-13 实现的所有工具集成到 REQ-05 的对话循环中，实现完整的"用户提问 → AI 调用工具 → 工具执行 → AI 基于结果回复"端到端流程。

### 功能规格

1. 程序启动时，将所有 6 个工具注册到工具注册器
2. API 请求中携带 `tools` 参数（通过 `get_openai_tools_schema()` 获取）
3. 对话循环中集成工具调用执行引擎（REQ-07）
4. 工具执行前，在终端展示工具调用信息并等待用户确认（受 `auto_approve` 配置控制）
5. 工具执行过程中，终端显示状态提示：`[Executing: <tool_name>...]`
6. 工具执行完成后，终端显示结果摘要：
   - 成功时：`[Done: <tool_name>] <结果前 100 字符>...`（结果超过 100 字符时截断）
   - 失败时：`[Failed: <tool_name>] <错误信息>`

### 交付物

- 工具注册启动逻辑
- 工具调用在对话循环中的集成代码
- 终端工具状态展示逻辑
- 端到端集成测试（使用 Mock API Server）：
  - 用户提问 → AI 调用 read_file → 返回文件内容 → AI 基于内容回复
  - 用户提问 → AI 调用 run_command → 返回命令输出 → AI 基于输出回复
  - 用户提问 → AI 连续调用多个工具 → 最终回复
  - 用户拒绝工具调用 → AI 给出替代回复

### Review 检查项

- [ ] 所有 6 个工具均已注册
- [ ] 工具调用状态提示不干扰流式输出
- [ ] 多工具调用场景下，每个工具的确认和状态提示独立展示
- [ ] 工具执行结果正确传回消息管理器

### 验收标准

- [ ] 连接真实或 Mock API，输入"读取当前目录下的 README.md"，AI 调用 `read_file`，确认后返回文件内容，AI 基于内容回复
- [ ] 输入"列出当前目录文件"，AI 调用 `list_files`，确认后返回文件列表，AI 整理后回复
- [ ] 输入"运行 `ls -la`"，AI 调用 `run_command`，确认后执行命令，AI 展示输出
- [ ] 拒绝工具调用后，AI 给出"无法执行该操作"类的替代回复
- [ ] 工具执行过程中终端显示 `[Executing: ...]` 状态
- [ ] 集成测试全部通过

---

## REQ-15：安全与权限控制

### 需求描述

实现文件操作的沙箱约束和命令执行的安全限制，防止 AI 越权操作。

### 功能规格

1. **文件操作沙箱**：
   - 所有文件操作工具（`read_file`、`write_file`、`edit_file`、`list_files`、`search_files`）的目标路径必须位于**项目目录（工作目录）及其子目录**内
   - 此限制为硬性约束，初版不提供配置项放宽
   - 路径解析后，检查其绝对路径是否以工作目录的绝对路径为前缀
   - 若路径越界，返回 `"Error: Access denied: path is outside project directory"`
   - 路径中包含 `..` 的情况，先解析为绝对路径再检查（防止 `../../etc/passwd` 穿越）
   - 符号链接：解析符号链接的实际目标路径后再检查是否在沙箱内

2. **命令黑名单**：
   - `run_command` 工具执行前，检查命令是否包含以下危险模式（不区分大小写）：
     - `rm -rf /`
     - `mkfs`
     - `dd if=`（后接 `/dev/`）
     - `:(){ :|:& };:` (fork bomb)
   - 命中黑名单时，返回 `"Error: Command blocked for safety: <匹配到的模式>"`
   - 黑名单定义为可配置的列表，集中维护

3. **敏感操作高亮提醒**：
   - 以下操作在用户确认界面中额外显示红色警告 `[WARNING: Destructive operation]`：
     - `write_file` 覆写已有文件时
     - `run_command` 中包含 `rm`、`git push`、`git reset`、`DROP TABLE`、`DELETE FROM` 时
   - 警告仅为提示，不阻止用户确认执行

### 交付物

- 路径沙箱检查模块源码
- 命令黑名单检查模块源码
- 敏感操作检测逻辑
- 单元测试：
  - 合法路径通过检查
  - `../` 穿越路径被拒绝
  - 符号链接指向沙箱外被拒绝
  - 黑名单命令被拦截
  - 敏感操作标记正确
  - 正常命令不被误拦截

### Review 检查项

- [ ] 路径检查在 resolve 后进行，不可被 `..` 或符号链接绕过
- [ ] 黑名单匹配是子串匹配，避免过于宽泛的正则导致误拦
- [ ] 敏感操作检测为独立函数，不耦合到确认流程
- [ ] 黑名单和敏感模式列表集中定义，易于维护

### 验收标准

- [ ] `read_file` 传入 `../../etc/passwd`，返回 `Error: Access denied: path is outside project directory`
- [ ] 在项目目录创建指向 `/etc/passwd` 的符号链接，`read_file` 读取该链接，返回 `Access denied`
- [ ] `run_command` 传入 `rm -rf /`，返回 `Error: Command blocked for safety`
- [ ] `run_command` 传入正常命令 `ls -la`，正常执行不被拦截
- [ ] `write_file` 覆写已有文件时，确认界面显示 `[WARNING: Destructive operation]`
- [ ] `run_command` 含 `git push` 时，确认界面显示警告
- [ ] 单元测试全部通过

---

## REQ-16：终端界面 — Markdown 渲染与代码高亮

### 需求描述

增强终端输出的可读性，实现 AI 回复中 Markdown 内容的终端渲染和代码块语法高亮。

### 功能规格

1. **Markdown 渲染**（终端 ANSI 转义序列实现）：

   | Markdown 元素 | 渲染效果 |
   |---------------|----------|
   | `# 标题` | 粗体 + 白色 |
   | `## 二级标题` | 粗体 |
   | `**粗体**` | ANSI 粗体 |
   | `` `行内代码` `` | 灰色背景 |
   | ` ```代码块``` ` | 带边框的代码区域（见下方） |
   | `- 列表项` | 保持原样，前缀 `  - ` 缩进 |
   | `> 引用` | 灰色文字，前缀 `│ ` |

2. **代码块渲染**：
   - 代码块上方显示语言标签（如 `─── python ───`）
   - 代码内容区域左侧添加 `│ ` 前缀
   - 代码块下方显示闭合线 `──────────`

3. **语法高亮**：
   - 对代码块中的内容按指定语言进行语法高亮
   - 至少支持以下语言：`python`、`javascript`/`js`、`typescript`/`ts`、`go`、`rust`、`java`、`c`、`cpp`、`bash`/`sh`、`json`、`yaml`、`html`、`css`、`sql`
   - 未指定语言或不支持的语言时，不做高亮，仅做代码块边框渲染
   - 高亮使用 ANSI 256 色或 16 色（兼容大多数终端）

4. **Diff 展示**：
   - 当 `edit_file` 工具执行成功后，在终端展示修改前后的 diff
   - 格式为 unified diff：
     - 删除行前缀 `- ` 并标红色
     - 新增行前缀 `+ ` 并标绿色
     - 上下文行前缀 `  `（两个空格）
   - 显示修改位置的前后各 3 行上下文

5. **流式渲染**：
   - 流式输出过程中，逐步解析和渲染 Markdown
   - 代码块在完整接收到闭合 ` ``` ` 后再统一渲染（代码块内的内容暂缓显示，等闭合后一次性高亮输出）
   - 非代码块的内容保持逐片段输出

### 交付物

- Markdown 渲染器模块源码
- 语法高亮模块源码（可使用第三方高亮库）
- Diff 展示模块源码
- 流式渲染集成逻辑
- 单元测试：
  - 各 Markdown 元素的 ANSI 输出正确
  - 代码块边框和语言标签
  - 至少 3 种语言的高亮输出非空（有 ANSI 颜色码）
  - Diff 输出格式和颜色

### Review 检查项

- [ ] ANSI 转义序列正确闭合，不会污染后续输出
- [ ] 嵌套 Markdown 元素处理合理（如粗体内的行内代码）
- [ ] 流式渲染中，代码块状态机状态正确维护（跨多个 delta 片段的 ` ``` ` 识别）
- [ ] 使用终端颜色前检测终端是否支持（`TERM` 环境变量或 `isatty`），不支持时降级为纯文本

### 验收标准

- [ ] AI 回复包含标题、粗体、列表、代码块时，终端渲染为对应的格式化效果
- [ ] Python 代码块有语法高亮（关键字、字符串、注释颜色不同）
- [ ] 未知语言的代码块有边框但无高亮
- [ ] `edit_file` 执行后终端显示红绿色 diff
- [ ] 流式输出时，普通文本逐步显示，代码块在完整接收后一次性显示
- [ ] 重定向输出到文件时（`mastercoder > output.txt`），无 ANSI 转义序列
- [ ] 单元测试全部通过

---

## REQ-17：终端界面 — 状态栏与 Token 统计

### 需求描述

在终端界面中添加状态指示信息，展示当前模型、工作目录、AI 运行状态和 Token 用量。

### 功能规格

1. **输入提示符增强**：
   - 将提示符从简单的 `> ` 改为包含上下文信息的格式：
     ```
     mastercoder [gpt-4o] ~/project (main) >
     ```
   - 格式：`mastercoder [<模型名>] <工作目录短路径> (<git分支>) > `
   - 工作目录使用 `~` 替代 home 目录前缀
   - 若不在 Git 仓库中，省略 `(分支)` 部分

2. **AI 思考状态**：
   - API 请求发出后、首个回复片段到达前，显示旋转动画：`⠋ Thinking...`（使用 braille spinner 字符序列：`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`）
   - 首个片段到达后，停止动画并清除该行，开始展示 AI 回复

3. **工具执行状态**：
   - 工具执行期间显示：`⠋ Running <tool_name>...`（同样使用旋转动画）
   - 工具执行完成后停止动画

4. **Token 统计**：
   - 每轮对话完成后，在 AI 回复下方显示统计行：
     ```
     [tokens: ↑1234 ↓567 | total: ↑5000 ↓2000]
     ```
   - `↑` 表示输入 token（prompt tokens），`↓` 表示输出 token（completion tokens）
   - 第一组为本轮对话的 token 数，第二组为累计 token 数
   - Token 数从 API 响应的 `usage` 字段获取；若 API 未返回 `usage`，显示 `[tokens: estimated]` 并使用消息管理器的估算值
   - 统计行使用灰色暗色显示，不干扰主要内容

### 交付物

- 增强版输入提示符逻辑
- Git 分支检测模块（执行 `git rev-parse --abbrev-ref HEAD`）
- Spinner 动画模块（异步/后台线程更新终端显示）
- Token 统计与展示逻辑
- 单元测试：
  - 提示符格式正确（含/不含 Git 分支）
  - Git 分支检测（在 Git 仓库 / 非 Git 仓库中）
  - Token 统计累加正确

### Review 检查项

- [ ] Spinner 动画在后台运行，不阻塞输入或输出处理
- [ ] Spinner 清除时使用 `\r` + 空格覆盖，不留残留
- [ ] Git 命令执行静默处理失败（非 Git 仓库时不报错）
- [ ] Token 统计溢出安全（累计值使用 64 位整数）

### 验收标准

- [ ] 在 Git 仓库中，提示符显示 `mastercoder [<model>] <path> (<branch>) > `
- [ ] 在非 Git 目录中，提示符不含分支信息
- [ ] 发送消息后，AI 回复前出现旋转动画 `Thinking...`
- [ ] 工具执行期间出现旋转动画 `Running <tool_name>...`
- [ ] AI 回复结束后，下方显示 token 统计行
- [ ] 多轮对话后，累计 token 数正确累加
- [ ] 单元测试全部通过

---

## REQ-18：斜杠命令系统

### 需求描述

实现斜杠命令解析和执行机制，用户输入以 `/` 开头的文本时，作为内部命令处理而非发送给 AI。

### 功能规格

1. **命令解析**：
   - 用户输入以 `/` 开头时，识别为斜杠命令
   - 命令格式：`/<command> [args]`
   - 命令名不区分大小写
   - 未识别的命令：打印 `Unknown command: /<command>. Type /help for available commands.`

2. **内置命令**：

   | 命令 | 参数 | 行为 |
   |------|------|------|
   | `/help` | 无 | 打印所有可用命令及其说明 |
   | `/clear` | 无 | 清空当前对话历史（保留 system 消息），打印 `Conversation cleared.` |
   | `/model` | `[model_name]` | 无参数时打印当前模型名；有参数时切换模型并打印 `Model switched to <model_name>` |
   | `/config` | 无 | 打印当前生效的配置（`api_key` 脱敏显示） |
   | `/exit` | 无 | 打印 `Goodbye!` 并退出程序（exit code 0）|

3. **`/help` 输出格式**：
   ```
   Available commands:
     /help           Show this help message
     /clear          Clear conversation history
     /model [name]   Show or switch the current model
     /config         Show current configuration
     /exit           Exit MasterCoder
   ```

4. **`/model` 切换逻辑**：
   - 切换仅修改当前会话的模型名称，不修改配置文件
   - 切换后下一次 API 请求使用新模型名称
   - 提示符中的模型名同步更新

5. **`/config` 输出格式**：
   ```
   Current configuration:
     api_base_url:  https://api.openai.com/v1
     api_key:       sk-****abcd
     model:         gpt-4o
     max_tokens:    4096
     temperature:   0.0
     auto_approve:  false
     system_prompt: (default)
   ```
   - `api_key` 仅显示前 3 个字符和最后 4 个字符，中间用 `****` 替代
   - `system_prompt` 为空时显示 `(default)`，非空时显示前 50 个字符 + `...`

### 交付物

- 斜杠命令解析器源码
- 各命令实现
- 单元测试：
  - `/help` 输出包含所有命令
  - `/clear` 后消息列表仅剩 system
  - `/model` 无参数显示当前模型，有参数切换成功
  - `/config` 输出所有配置项且 key 脱敏
  - `/exit` 退出
  - 未知命令提示

### Review 检查项

- [ ] 斜杠命令解析优先于 AI 消息发送
- [ ] 命令名解析忽略大小写
- [ ] `/model` 切换不影响配置文件
- [ ] `/config` 输出中无敏感信息泄漏

### 验收标准

- [ ] 输入 `/help` 后打印命令列表，格式与规格一致
- [ ] 输入 `/clear` 后对话历史被清空，下一轮 AI 不记得之前的内容
- [ ] 输入 `/model deepseek-chat` 后提示符中模型名变为 `deepseek-chat`
- [ ] 输入 `/model` 后打印当前模型名
- [ ] 输入 `/config` 后打印当前配置，api_key 脱敏显示
- [ ] 输入 `/exit` 后程序退出
- [ ] 输入 `/unknown` 后打印未知命令提示
- [ ] 输入 `/HELP`（大写）正常识别为 help 命令
- [ ] 单元测试全部通过

---

## REQ-19：项目级配置与 MASTERCODER.md

### 需求描述

实现项目级配置文件加载和 `MASTERCODER.md` 项目指令文件的自动注入。

### 功能规格

1. **项目级配置文件**：
   - 路径：`<工作目录>/.mastercoder/config.json`
   - 格式与全局配置文件相同
   - 最终配置优先级：**环境变量 > 项目级配置 > 全局配置 > 默认值**
   - 项目级配置文件不存在时，静默忽略

2. **MASTERCODER.md 指令文件**：
   - 程序启动时检查工作目录下是否存在 `MASTERCODER.md` 文件
   - 若存在，读取其全部内容
   - 将内容追加到 system 消息中，格式：
     ```
     <内置 system prompt>

     ---

     Project instructions (from MASTERCODER.md):

     <MASTERCODER.md 内容>
     ```
   - 若文件不存在，不追加，不报错
   - `MASTERCODER.md` 文件大小超过 **50KB** 时，打印警告 `Warning: MASTERCODER.md exceeds 50KB, truncating to first 50KB` 并截断

3. **自定义系统提示词整合**：
   - 若用户配置了 `system_prompt`，拼接顺序为：
     ```
     <内置 system prompt>
     ---
     Project instructions (from MASTERCODER.md):
     <MASTERCODER.md 内容>
     ---
     Custom instructions:
     <用户 system_prompt 配置>
     ```
   - 各部分之间用 `---` 分隔

### 交付物

- 项目级配置加载逻辑（扩展 REQ-02 配置系统）
- MASTERCODER.md 读取和注入逻辑
- system prompt 拼接逻辑
- 单元测试：
  - 项目级配置覆盖全局配置
  - 环境变量覆盖项目级配置
  - MASTERCODER.md 存在时注入到 system 消息
  - MASTERCODER.md 不存在时无影响
  - 超大 MASTERCODER.md 截断
  - system_prompt + MASTERCODER.md 拼接顺序

### Review 检查项

- [ ] 配置优先级链完整正确
- [ ] MASTERCODER.md 读取在启动阶段一次性完成，不在每轮对话中重复读取
- [ ] 截断以字节为单位，不会截断 UTF-8 多字节字符的中间位置
- [ ] system prompt 拼接后长度合理，不超出模型上下文窗口的合理占比

### 验收标准

- [ ] 创建 `.mastercoder/config.json` 写入 `{"model":"local-model"}`，启动后模型为 `local-model`（覆盖全局配置）
- [ ] 设置 `MASTERCODER_MODEL=env-model`，启动后模型为 `env-model`（覆盖项目级配置）
- [ ] 创建 `MASTERCODER.md` 写入 "Always use TypeScript"，与 AI 对话时 AI 行为受此指令影响
- [ ] 删除 `MASTERCODER.md` 后启动，无报错，system 消息中无 Project instructions 段
- [ ] 创建超过 50KB 的 `MASTERCODER.md`，启动时打印截断警告
- [ ] 同时存在 `MASTERCODER.md` 和 `system_prompt` 配置时，system 消息中两者均存在且顺序正确
- [ ] 单元测试全部通过

---

## REQ-20：会话持久化与恢复

### 需求描述

实现对话历史的本地持久化存储，以及上次会话的恢复功能。

### 功能规格

1. **存储位置**：`~/.mastercoder/sessions/` 目录下
2. **会话文件命名**：`<session_id>.json`，其中 `session_id` 为 `<时间戳>_<4位随机hex>`（如 `20260326_143022_a1b2.json`）
3. **自动保存**：
   - 每轮对话完成（AI 回复结束）后，自动将当前消息列表保存到会话文件
   - 保存格式：
     ```json
     {
       "session_id": "20260326_143022_a1b2",
       "created_at": "2026-03-26T14:30:22Z",
       "updated_at": "2026-03-26T14:35:10Z",
       "working_directory": "/home/user/project",
       "model": "gpt-4o",
       "messages": [...]
     }
     ```
   - `messages` 中包含所有消息（含 system），格式与消息管理器内部格式一致

4. **会话恢复**：
   - 程序启动时添加命令行参数 `--resume`：
     - `mastercoder --resume` — 恢复最近一次会话
     - `mastercoder --resume <session_id>` — 恢复指定会话
   - 恢复时加载消息列表到消息管理器，终端打印 `Resumed session <session_id> (<消息条数> messages)`
   - 恢复的会话继续使用原 session_id 文件保存
   - 若指定的 session_id 不存在，打印 `Error: Session not found: <session_id>` 并以 exit code 1 退出

5. **会话列表**：
   - 新增斜杠命令 `/sessions`：列出最近 20 个会话，格式：
     ```
     Recent sessions:
       20260326_143022_a1b2  2026-03-26 14:30  ~/project       gpt-4o    12 messages
       20260325_091055_c3d4  2026-03-25 09:10  ~/other-repo    deepseek  8 messages
     ```
   - 按 `updated_at` 降序排列

6. **`/clear` 命令更新**：执行 `/clear` 后，生成新的 session_id，开始新的会话文件

### 交付物

- 会话序列化/反序列化模块
- 自动保存逻辑
- `--resume` 命令行参数解析
- `/sessions` 斜杠命令
- 单元测试：
  - 会话保存后文件内容正确
  - 从文件恢复后消息列表正确
  - `--resume` 无参数恢复最近会话
  - `--resume` 指定不存在的 session_id 报错
  - `/sessions` 列表排序正确
  - `/clear` 后生成新会话

### Review 检查项

- [ ] 会话文件写入为原子操作（先写临时文件再 rename），防止写入中断导致文件损坏
- [ ] 恢复时校验 JSON 格式，损坏文件给出清晰报错
- [ ] 会话文件不包含 API Key 等敏感信息
- [ ] `sessions` 目录自动创建

### 验收标准

- [ ] 正常对话后，`~/.mastercoder/sessions/` 下生成对应会话文件
- [ ] 退出程序后执行 `mastercoder --resume`，恢复上次对话内容，AI 能回忆之前的上下文
- [ ] `mastercoder --resume 20260326_143022_a1b2` 恢复指定会话
- [ ] 指定不存在的 session_id，报错退出
- [ ] 输入 `/sessions` 显示最近会话列表
- [ ] 输入 `/clear` 后，后续对话保存到新的会话文件
- [ ] 单元测试全部通过

---

## REQ-21：多行输入与输入历史

### 需求描述

增强终端输入体验，支持多行文本输入和输入历史浏览。

### 功能规格

1. **多行输入**：
   - 用户按 `Shift+Enter` 或 `\` + `Enter` 时，插入换行而非提交输入
   - 多行输入时，第二行起的提示符变为 `... ` 以区分续行
   - 按 `Enter`（非组合键）时提交全部输入
   - 示例：
     ```
     > 帮我写一个函数\
     ... 要求输入是字符串
     ... 输出是反转后的字符串
     ```

2. **输入历史**：
   - 按 `↑`（上箭头）浏览上一条历史输入
   - 按 `↓`（下箭头）浏览下一条历史输入
   - 历史记录仅保存用户输入，不保存斜杠命令
   - 当前会话的历史记录存储在内存中
   - 最多保存最近 **100 条**历史输入

3. **粘贴支持**：
   - 从剪贴板粘贴的多行文本自动识别，不会逐行提交
   - 使用终端的 bracketed paste mode 检测粘贴操作

### 交付物

- 多行输入处理逻辑
- 输入历史管理模块
- Bracketed paste mode 支持
- 单元测试：
  - `\` + Enter 触发换行
  - 多行提交后内容完整
  - 历史上下翻页
  - 超过 100 条后最旧的被淘汰
  - 斜杠命令不存入历史

### Review 检查项

- [ ] `Shift+Enter` 检测依赖终端能力，需有 fallback（`\` + Enter）
- [ ] 输入历史不包含空输入
- [ ] Bracketed paste mode 在退出时正确关闭（恢复终端状态）
- [ ] 多行输入状态下 `Ctrl+C` 取消当前输入并回到单行模式

### 验收标准

- [ ] 输入 `hello\` 后按 Enter，出现 `... ` 续行提示，继续输入后再按 Enter 提交全部内容
- [ ] 提交后按 `↑`，显示上一条输入内容
- [ ] 连续按 `↑` 多次可翻阅更早的历史
- [ ] 按 `↓` 返回更近的历史
- [ ] 粘贴多行文本后，文本完整显示在输入区域，不会自动提交
- [ ] 输入 `/help` 后按 `↑`，显示的不是 `/help` 而是上一条用户消息
- [ ] 单元测试全部通过

---

## REQ-22：上下文管理 — 手动添加文件

### 需求描述

允许用户通过 `@` 语法主动将文件内容加入当前对话上下文，无需等待 AI 调用工具。支持一次引用多个文件，但每个 `@` 引用必须指向文件，不支持目录展开（传入目录路径时提示 `Error: Directory references are not supported, use a file path`）。

### 功能规格

1. **`@` 语法**：
   - 用户输入中包含 `@<文件路径>` 时，程序在发送给 AI 前自动读取该文件并附加到消息中
   - 示例：`@src/mastercoder/main.py 这个文件有什么问题？`
   - 支持多个文件引用：`@a.py @b.py 比较这两个文件`
   - 文件路径支持相对路径和绝对路径

2. **处理逻辑**：
   - 解析用户输入中的所有 `@<path>` 引用
   - 逐个读取文件内容（复用 `read_file` 工具的逻辑，含大小和二进制检查）
   - 将文件内容附加到用户消息中，格式：
     ```
     <用户输入的原始文本（去掉 @path 部分）>

     ---
     File: src/mastercoder/main.py
     ```python
     <文件内容>
     ```

     ---
     File: src/utils.py
     ```python
     <文件内容>
     ```
     ```
   - 文件读取失败时，在对应位置显示错误：`File: src/missing.py\n[Error: File not found]`

3. **路径补全**：
   - 用户输入 `@` 后按 `Tab` 键，触发文件路径补全
   - 补全范围为当前工作目录下的文件
   - 支持逐级目录补全

4. **限制**：
   - 单次输入最多引用 **10 个文件**，超出时提示 `Warning: Maximum 10 file references per message, ignoring extra files`
   - `@` 后紧跟空格的不视为文件引用（如 `@ someone` 不触发）

### 交付物

- `@` 引用解析模块
- 文件内容附加逻辑
- Tab 补全逻辑
- 单元测试：
  - 解析单个/多个 `@path` 引用
  - 文件内容正确附加到消息
  - 文件不存在时附加错误信息
  - 超过 10 个引用时截断
  - `@` 后跟空格不触发
  - 路径中含空格时使用引号 `@"path with space/file.py"`

### Review 检查项

- [ ] `@` 解析不会误匹配邮箱地址（需要 `@` 后紧跟 `/` 或字母且不含 `@` 前的字母）
- [ ] 文件读取复用 read_file 逻辑，包含沙箱检查
- [ ] Tab 补全不阻塞输入
- [ ] 消息格式对 AI 友好，文件内容有明确边界

### 验收标准

- [ ] 输入 `@README.md 概括一下这个文件`，AI 收到文件内容并给出概括
- [ ] 输入 `@a.py @b.py 对比差异`，两个文件内容都附加到消息中
- [ ] 引用不存在的文件时，消息中包含 `[Error: File not found]`
- [ ] 引用超过 10 个文件时打印警告，仅前 10 个生效
- [ ] `@ someone` 不触发文件引用
- [ ] 输入 `@` 后按 Tab 出现路径补全建议
- [ ] 单元测试全部通过

---

## REQ-23：错误处理与重试机制

### 需求描述

完善全局错误处理，增加 API 请求的自动重试机制。

### 功能规格

1. **自动重试**：
   - 以下错误触发自动重试：
     - HTTP 429（Rate Limit）
     - HTTP 500、502、503（服务端错误）
     - 网络连接超时
   - 重试策略：指数退避，间隔为 `1s, 2s, 4s`，最多重试 **3 次**
   - 每次重试时终端打印 `[Retrying... attempt <N>/3]`
   - 3 次重试仍失败后，展示最终错误信息

2. **非重试错误**：
   - HTTP 401（鉴权失败）：直接报错，不重试
   - HTTP 404（模型不存在）：直接报错，不重试
   - HTTP 400（请求格式错误）：直接报错，不重试

3. **全局异常兜底**：
   - 程序运行中的未捕获异常不应导致程序直接崩溃
   - 捕获顶层异常，打印 `Error: An unexpected error occurred: <异常信息>`
   - 打印后程序回到 `> ` 提示符继续运行
   - 异常信息同时写入日志文件 `~/.mastercoder/error.log`（追加写入，含时间戳和堆栈信息）

4. **日志文件**：
   - 路径：`~/.mastercoder/error.log`
   - 每条日志格式：`[2026-03-26 14:30:22] ERROR: <错误信息>\n<堆栈信息>\n`
   - 日志文件超过 **5MB** 时，在写入前先截断（保留最后 2MB）

### 交付物

- 重试模块源码
- 全局异常处理逻辑
- 日志模块源码
- 单元测试：
  - 429 触发重试，第 2 次成功
  - 500 触发重试，3 次均失败后报错
  - 401 不重试
  - 重试间隔符合指数退避
  - 日志写入格式正确
  - 日志文件截断

### Review 检查项

- [ ] 重试间隔使用 sleep 而非忙等
- [ ] 重试计数器正确，无 off-by-one
- [ ] 全局异常捕获不掩盖开发期间的逻辑错误（建议 debug 模式下不捕获）
- [ ] 日志文件截断操作为原子性

### 验收标准

- [ ] Mock Server 第一次返回 429，第二次返回 200，程序打印重试信息后正常获取回复
- [ ] Mock Server 连续 4 次返回 500，程序重试 3 次后显示错误
- [ ] Mock Server 返回 401，程序直接显示错误不重试
- [ ] 手动触发一个运行时异常（如破坏会话文件格式），程序打印错误后可继续使用
- [ ] `~/.mastercoder/error.log` 中包含异常的时间戳和堆栈
- [ ] 单元测试全部通过

---

## REQ-24：命令行参数与启动选项

### 需求描述

实现完整的命令行参数解析，支持通过启动参数自定义程序行为。

### 功能规格

1. **命令行参数**：

   | 参数 | 短参数 | 类型 | 说明 |
   |------|--------|------|------|
   | `--model` | `-m` | string | 指定模型名称（覆盖配置文件） |
   | `--api-key` | 无 | string | 指定 API Key（覆盖配置文件和环境变量） |
   | `--api-url` | 无 | string | 指定 API Base URL |
   | `--auto-approve` | `-y` | bool | 启用自动批准模式 |
   | `--resume` | `-r` | string (可选) | 恢复会话，可选指定 session_id |
   | `--version` | `-v` | bool | 打印版本号并退出 |
   | `--help` | `-h` | bool | 打印帮助信息并退出 |
   | `--no-color` | 无 | bool | 禁用终端颜色输出 |

2. **非交互模式（管道输入）**：
   - 当 stdin 不是 TTY 时（如 `echo "hello" | mastercoder`），进入非交互模式
   - 读取 stdin 全部内容作为用户输入
   - 发送给 AI 并打印回复（纯文本，无 ANSI 颜色）
   - 打印完成后直接退出（exit code 0）
   - 非交互模式下 `auto_approve` 默认为 true

3. **版本号**：`--version` 输出格式为 `MasterCoder v0.1.0`

4. **最终配置优先级**：**命令行参数 > 环境变量 > 项目级配置 > 全局配置 > 默认值**

### 交付物

- 命令行参数解析模块源码
- 非交互模式逻辑
- 帮助信息文本
- 单元测试：
  - 各参数解析正确
  - 参数覆盖配置文件
  - 非交互模式检测和处理
  - `--version` 和 `--help` 输出

### Review 检查项

- [ ] 使用成熟的命令行参数解析库
- [ ] `--api-key` 在进程参数列表中可见（`/proc/*/cmdline`），需在帮助信息中提醒用户使用环境变量更安全
- [ ] 非交互模式下无 spinner 和交互提示
- [ ] 优先级链完整：命令行 > 环境变量 > 项目配置 > 全局配置 > 默认值

### 验收标准

- [ ] `mastercoder -m deepseek-chat` 启动后使用 deepseek-chat 模型
- [ ] `mastercoder -y` 启动后工具调用无需确认
- [ ] `mastercoder --version` 打印版本号并退出
- [ ] `mastercoder --help` 打印帮助信息并退出
- [ ] `echo "hello" | mastercoder` 打印 AI 回复后自动退出，输出无颜色
- [ ] `mastercoder --no-color` 启动后所有输出无 ANSI 转义序列
- [ ] `-m` 参数覆盖配置文件和环境变量中的 model 设置
- [ ] 单元测试全部通过

---

## REQ-25：Git 仓库感知增强

### 需求描述

增强程序对 Git 仓库状态的感知能力，将 Git 信息自动注入对话上下文，帮助 AI 更好地理解项目状态。

### 功能规格

1. **Git 状态检测**（程序启动时执行一次）：
   - 检测当前目录是否为 Git 仓库（通过 `git rev-parse --is-inside-work-tree`）
   - 若是 Git 仓库，收集以下信息：
     - 当前分支名：`git rev-parse --abbrev-ref HEAD`
     - 仓库状态摘要：`git status --short`（最多取前 20 行）
     - 最近 5 条 commit 信息：`git log --oneline -5`

2. **信息注入**：
   - 将 Git 信息追加到 system 消息中，格式：
     ```
     ---
     Git repository detected:
     Branch: main

     Recent commits:
     a1b2c3d Fix login bug
     e4f5g6h Add user dashboard
     ...

     Status:
     M  src/mastercoder/main.py
      M src/utils.py
     ?? new_file.txt
     ```
   - Git 状态为 clean 时显示 `Status: clean`

3. **实时分支显示**：
   - 提示符中的 Git 分支在每次显示 `> ` 时刷新（执行 `git rev-parse --abbrev-ref HEAD`）
   - Git 命令执行失败时静默忽略，提示符中不显示分支

### 交付物

- Git 信息收集模块源码
- system 消息注入逻辑
- 提示符分支刷新逻辑
- 单元测试：
  - Git 仓库中正确收集信息
  - 非 Git 目录无报错
  - Git 信息注入到 system 消息格式正确
  - 分支切换后提示符更新

### Review 检查项

- [ ] 所有 Git 命令设置超时（2 秒），防止大仓库卡住
- [ ] Git 命令失败时不影响程序启动
- [ ] `git status --short` 结果限制行数，避免大量未跟踪文件淹没上下文
- [ ] 提示符刷新的 Git 命令为异步或有缓存（避免每次输入都卡顿）

### 验收标准

- [ ] 在 Git 仓库中启动，AI 能感知当前分支和最近 commit（如问"当前在哪个分支"能正确回答）
- [ ] 在非 Git 目录中启动，程序正常运行，无报错
- [ ] 切换分支后（`git checkout other-branch`），下一次提示符中分支名更新
- [ ] 修改文件后，重新启动程序，Git status 反映未提交的修改
- [ ] 单元测试全部通过

---

## 需求依赖关系总览

```
REQ-01 项目脚手架
  ↓
REQ-02 配置系统
  ↓
REQ-03 API 客户端
  ↓
REQ-04 消息管理器
  ↓
REQ-05 基础对话循环 ← 依赖 REQ-01~04
  ↓
REQ-06 工具定义框架
  ↓
REQ-07 工具调用引擎 ← 依赖 REQ-06
  ↓
REQ-08~13 六个工具实现 ← 依赖 REQ-06（可并行开发）
  ↓
REQ-14 工具集成 ← 依赖 REQ-05, REQ-07, REQ-08~13
  ↓
REQ-15 安全与权限 ← 依赖 REQ-08~13
  ↓
REQ-16 Markdown 渲染 ← 依赖 REQ-05
REQ-17 状态栏与统计 ← 依赖 REQ-05
REQ-18 斜杠命令 ← 依赖 REQ-01
  ↓
REQ-19 项目级配置 ← 依赖 REQ-02
REQ-20 会话持久化 ← 依赖 REQ-04, REQ-18（/sessions 命令）, REQ-24（--resume 参数）
REQ-21 多行输入 ← 依赖 REQ-01
REQ-22 手动添加上下文 ← 依赖 REQ-05, REQ-08
REQ-23 错误处理与重试 ← 依赖 REQ-03
REQ-24 命令行参数 ← 依赖 REQ-02
REQ-25 Git 感知 ← 依赖 REQ-17
```

> REQ-08 ~ REQ-13 六个工具实现之间无依赖，可分配给不同开发工程师并行开发。
> REQ-16、REQ-17、REQ-18 之间无依赖，可并行开发。
> REQ-19 ~ REQ-25 之间依赖关系较弱，可根据团队资源灵活调整开发顺序。
