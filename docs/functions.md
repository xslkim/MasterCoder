# MasterCoder 已实现功能（main 分支）

以下为 `main.py` 与 `core/`（包名 `mastercoder`）**已接入主流程**的能力。

## 入口与运行模式

- `mastercoder` 命令行入口；`-v` / `--version` 打印版本并退出；`--help` 显示参数帮助。
- **有 API Key（交互 TTY）：** 多轮对话，流式输出模型回复。
- **无 API Key（交互 TTY）：** 简易回显 REPL；`/exit` 退出；`Ctrl+C` / EOF 退出；空行跳过。
- **管道（stdin 非 TTY）：** 单次读取全部输入，流式请求一次模型，纯文本输出后退出。

## 配置

- 默认值 → `~/.mastercoder/config.json` → `<工作目录>/.mastercoder/config.json` → 环境变量 → 命令行覆盖。
- 环境变量：`MASTERCODER_API_BASE_URL`、`MASTERCODER_API_KEY`、`MASTERCODER_MODEL`。
- 非法 JSON 配置文件报错退出；`max_tokens` / `temperature` 越界回退默认值并警告。
- 参与请求与 system 的字段：`api_base_url`、`api_key`、`model`、`max_tokens`、`temperature`、`system_prompt`。

## 命令行（对行为有影响）

- `-m` / `--model`、`--api-key`、`--api-url`、`--no-color`。
- `-y` / `--auto-approve` 与配置项 `auto_approve` 会写入内存，但当前**无工具调用链路**，无实际效果。
- `--resume` 仅被解析，**未实现**会话恢复。

## 对话与 API

- OpenAI 兼容 `POST …/chat/completions`，`stream: true`，Bearer 鉴权，解析 `delta.content` 流式打印（无 `tools` / tool_calls）。
- 内存中多轮消息；超过默认 **100 条**时按条数截断非 system 消息并提示。
- 流式过程中 `Ctrl+C`：打印中断提示，已生成内容可写入历史。
- API 错误打印 `Error: …`；TTY 下可用红色（`--no-color` 时关闭）；错误不进入消息列表。

## System 提示词

- 内置说明 + 可选 `MASTERCODER.md`（超 50KB 截断并警告）+ Git 仓库信息（分支、近期 log、status 摘要）+ 可选 `system_prompt` 配置。

## 提示符与 Git

- 提示符含模型名、当前目录简写（`~` 表示家目录）、可选当前 Git 分支（每次刷新）。

## `@` 文件引用（仅交互式、有 API Key）

- 解析 `@路径`，将文件内容拼入用户消息；沙箱限制在工作目录内；单次最多 10 个引用；1MB / 二进制等校验。
- 支持 `@"含空格路径"`；支持 `readline` 时 Tab 补全（依赖终端环境）。

## 非交互管道

- 不处理 `@` 引用；stdin 全文作为单条用户消息（带完整 system）。
