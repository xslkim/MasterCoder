# MasterCoder

终端里的 AI 编程助手：在命令行中与模型对话，支持 OpenAI 兼容 API（含自定义 `api_base_url`），并可在当前 Git 仓库上下文中工作。

与 **当前 main 实现一致** 的功能列表见 [`docs/functions.md`](docs/functions.md)。

## 功能概要

- **交互模式**：在终端中持续对话（需配置 API Key）。
- **管道模式**：从标准输入读取一段文本，请求一次模型后输出到标准输出（适合脚本集成）。
- **配置**：环境变量、用户目录下的配置文件、项目内配置（详见下文）。

## 配置 API

在运行前至少需要 **API Key**（以及可选的接口地址、模型名）。

优先级（高到低）：**环境变量** → **项目目录配置** → **`~/.mastercoder/config.json`** → 默认值。

### 环境变量

| 变量 | 含义 |
|------|------|
| `MASTERCODER_API_KEY` | API Key（推荐） |
| `MASTERCODER_API_BASE_URL` | API 基址，默认 `https://api.openai.com/v1` |
| `MASTERCODER_MODEL` | 模型名，默认 `gpt-4o` |

### 配置文件

在用户主目录创建 `~/.mastercoder/config.json`，例如：

```json
{
  "api_key": "your-key",
  "api_base_url": "https://api.openai.com/v1",
  "model": "gpt-4o"
}
```

也可在项目根目录放置项目级配置（若项目内支持相应路径，与 `core/config.py` 中的加载逻辑一致）。

## 命令行用法

安装后命令名为 **`mastercoder`**（见下一节的开发安装；独立可执行文件见「打包」章节）。

```bash
mastercoder --version                    # 版本信息
mastercoder                              # 交互式会话（需 API Key）
mastercoder -m deepseek-chat             # 指定模型
mastercoder -y                           # 自动批准模式
mastercoder --no-color                   # 禁用颜色
echo "用一句话说明这个仓库是做什么的" | mastercoder   # 管道模式（需 API Key）
```

更多参数：

```bash
mastercoder --help
```

**安全提示**：通过 `--api-key` 传参会在系统进程列表中可见，优先使用环境变量或配置文件。

---

## 打包成独立可执行文件（无 Python、无源码）

目标：在**另一台机器**上只拷贝**一个二进制文件**即可运行，**不需要**安装 Python，也**不需要**本仓库源码。

### 在哪种系统上打包，就得到哪种系统的程序

- 在 **Linux x86_64**（含常见 WSL2）上打包 → 得到 **Linux** 可执行文件。
- 在 **Windows** 上打包 → 得到 **.exe**（需在 Windows 上自行执行相同流程）。
- 两台机器架构或 libc 相差过大时，请在**目标环境同类系统**上重新打包。

### 打包步骤（Linux 示例）

1. 准备 **Python 3.11+**（仅用于**构建机**，运行产物不需要）。
2. 克隆或拷贝本仓库，进入项目根目录（含 `pyproject.toml`、`main.py`、`mastercoder.spec`）。

```bash
cd /path/to/MasterCoder
python3 -m venv .venv
source .venv/bin/activate   # Windows 用: .venv\Scripts\activate
pip install -U pip
```

3. **必须**用普通安装把包打进 site-packages（**不要用** `pip install -e`，否则 PyInstaller 无法正确收集 `mastercoder` 包）：

```bash
pip install .
pip install pyinstaller
```

4. 使用仓库中的 spec 生成单文件可执行程序：

```bash
rm -rf build dist
pyinstaller mastercoder.spec
```

5. 产物路径：**`dist/mastercoder`**（Linux）或 Windows 下对应的 **`dist/mastercoder.exe`**。

将该文件复制到目标机器，赋予可执行权限后直接使用：

```bash
chmod +x dist/mastercoder
export MASTERCODER_API_KEY='你的key'
./dist/mastercoder --version
./dist/mastercoder
```

管道模式示例：

```bash
echo "hello" | MASTERCODER_API_KEY='你的key' ./dist/mastercoder
```

### 说明与限制

- 独立可执行文件内**已包含** Python 解释器与依赖，**运行方无需**再装 Python。
- Linux 二进制仍依赖系统提供的动态链接库（如 **glibc**）。若在过旧或过新的发行版上无法运行，请在**目标发行版或 Docker 同类环境**中重新执行打包。
- 首次启动时，单文件形态可能会解压到临时目录，属 PyInstaller 正常行为。

---

## 从源码以 Python 方式运行（开发者）

适合开发与调试：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"    # 可编辑安装，便于改代码
mastercoder --version
```

---

## 许可证

MIT（见 `pyproject.toml` 中的声明）。
