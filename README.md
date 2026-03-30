# MasterCoder

MasterCoder is a terminal-based AI coding assistant with project-aware prompts, configuration layering, Git context injection, and `@file` context expansion.

详细使用文档见 [docs/mastercoder-user-guide.md](docs/mastercoder-user-guide.md)。

## Shipped In This Release

- Interactive terminal chat entrypoint via `mastercoder`
- Command-line startup options such as `--model`, `--api-key`, `--api-url`, `--no-color`, and `--version`
- Global and project-level configuration loading
- `MASTERCODER.md` project instruction injection
- `@path/to/file` and `@"path with spaces"` file context injection
- Git-aware prompt and Git summary injection into the system prompt
- Non-interactive pipeline mode through stdin

## Quick Start

```bash
git clone git@github.com:xslkim/MasterCoder.git
cd MasterCoder
python3 -m pip install -e .

mkdir -p ~/.mastercoder
cat > ~/.mastercoder/config.json <<'EOF'
{
	"api_key": "YOUR_API_KEY",
	"api_base_url": "https://api.openai.com/v1",
	"model": "gpt-4o"
}
EOF

mastercoder
```

如果你不想把密钥写入文件，也可以只设置环境变量：

```bash
export MASTERCODER_API_KEY="YOUR_API_KEY"
export MASTERCODER_API_BASE_URL="https://api.openai.com/v1"
export MASTERCODER_MODEL="gpt-4o"
mastercoder
```

## Common Commands

```bash
mastercoder
mastercoder -m deepseek-chat
mastercoder --api-key "$MASTERCODER_API_KEY" --api-url https://example.com/v1
mastercoder --version
mastercoder --no-color
echo "Summarize this repository" | mastercoder --api-key "$MASTERCODER_API_KEY"
```

## Configuration Locations

- Global config: `~/.mastercoder/config.json`
- Project config: `<repo>/.mastercoder/config.json`
- Project instructions: `<repo>/MASTERCODER.md`

配置优先级：命令行参数 > 环境变量 > 项目级配置 > 全局配置 > 默认值。

## Current Limitations

- `--resume` 参数已经实现了解析，但当前发布版本尚未把会话恢复流程接入启动入口。
- 会话持久化与会话列表模块已经在仓库中实现，但当前主入口没有暴露 `/sessions` 等用户命令。
- 顶层 fallback REPL 在没有 API key 时仅提供本地回显和 `/exit`，不会调用模型。
- 仓库中保留了自动化开发框架代码；本发布分支面向最终用户时，应以 `src/mastercoder/` 和 [docs/mastercoder-user-guide.md](docs/mastercoder-user-guide.md) 为准。

## Internal Docs

如果你还需要仓库内的自动化开发框架说明，可以继续参考：

- [docs/automation-tutorial.md](docs/automation-tutorial.md)
- [docs/mastercoder-automation.md](docs/mastercoder-automation.md)
