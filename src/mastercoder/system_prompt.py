"""System prompt 构建模块 - 支持 MASTERCODER.md 注入和自定义提示词拼接。"""

from pathlib import Path


# 内置 system prompt
BUILTIN_SYSTEM_PROMPT = """You are MasterCoder, an AI programming assistant. You help users with software development tasks including writing code, debugging, refactoring, and explaining code. You have access to tools that can read files, write files, edit files, search files, and run commands on the user's local machine. Always be helpful, concise, and accurate."""

# 50KB 限制
MAX_MASTERCODER_MD_SIZE = 50 * 1024  # 50KB in bytes


def read_mastercoder_md(working_dir: Path) -> str:
    """读取 MASTERCODER.md 文件内容。

    如果文件超过 50KB，截断到前 50KB 并打印警告。
    确保截断不会破坏 UTF-8 多字节字符。

    Args:
        working_dir: 工作目录路径

    Returns:
        MASTERCODER.md 文件内容，如果不存在则返回空字符串
    """
    mastercoder_md_path = working_dir / "MASTERCODER.md"

    if not mastercoder_md_path.exists():
        return ""

    try:
        # 读取文件内容（二进制模式）
        with open(mastercoder_md_path, "rb") as f:
            content_bytes = f.read()

        # 检查文件大小
        if len(content_bytes) > MAX_MASTERCODER_MD_SIZE:
            print("Warning: MASTERCODER.md exceeds 50KB, truncating to first 50KB")
            # 截断到 50KB
            content_bytes = content_bytes[:MAX_MASTERCODER_MD_SIZE]

            # 确保 UTF-8 安全：从截断位置向前查找有效的 UTF-8 边界
            # 逐个字节向前查找，直到找到有效的 UTF-8 起始字节
            while content_bytes:
                try:
                    # 尝试解码
                    content_bytes.decode("utf-8")
                    break
                except UnicodeDecodeError:
                    # 截断位置在多字节字符中间，移除最后一个字节
                    content_bytes = content_bytes[:-1]

        # 解码为字符串
        return content_bytes.decode("utf-8")

    except (OSError, IOError):
        # 文件读取错误，返回空字符串
        return ""


def build_system_prompt(working_dir: Path, custom_prompt: str) -> str:
    """构建完整的 system prompt。

    拼接顺序：
    1. 内置 system prompt
    2. MASTERCODER.md 内容（如果存在）
    3. 用户自定义 system_prompt（如果配置）

    各部分之间用 "---" 分隔。

    Args:
        working_dir: 工作目录路径
        custom_prompt: 用户自定义 system_prompt 配置

    Returns:
        完整的 system prompt
    """
    parts = [BUILTIN_SYSTEM_PROMPT]

    # 读取 MASTERCODER.md
    mastercoder_md_content = read_mastercoder_md(working_dir)
    if mastercoder_md_content:
        parts.append("---")
        parts.append("Project instructions (from MASTERCODER.md):")
        parts.append(mastercoder_md_content)

    # 添加用户自定义提示词
    if custom_prompt:
        parts.append("---")
        parts.append("Custom instructions:")
        parts.append(custom_prompt)

    return "\n".join(parts)


def get_builtin_system_prompt() -> str:
    """获取内置 system prompt。

    Returns:
        内置 system prompt 字符串
    """
    return BUILTIN_SYSTEM_PROMPT
