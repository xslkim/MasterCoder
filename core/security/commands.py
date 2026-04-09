"""命令黑名单检查模块。

检查命令是否包含危险模式，防止执行破坏性操作。
"""

import re
from typing import List, Optional

# 命令黑名单模式列表（不区分大小写）
COMMAND_BLACKLIST: List[str] = [
    r"rm\s+-rf\s+/",  # rm -rf /
    r"mkfs",  # mkfs 命令
    r"dd\s+if=.*/dev/",  # dd if=.../dev/
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;:",  # fork bomb
]

# 敏感命令模式列表（不区分大小写）
SENSITIVE_COMMAND_PATTERNS: List[str] = [
    r"\brm\b",  # rm 命令
    r"\bgit\s+push\b",  # git push
    r"\bgit\s+reset\b",  # git reset
    r"\bDROP\s+TABLE\b",  # SQL DROP TABLE
    r"\bDELETE\s+FROM\b",  # SQL DELETE FROM
]


def check_command_blacklist(command: str) -> Optional[str]:
    """检查命令是否命中黑名单。

    Args:
        command: 要检查的命令字符串

    Returns:
        None 表示命令安全，不在黑名单中
        错误字符串表示命令被拦截，包含匹配到的模式
    """
    # 检查每个黑名单模式
    for pattern in COMMAND_BLACKLIST:
        # 不区分大小写匹配
        if re.search(pattern, command, re.IGNORECASE):
            # 提取匹配到的模式用于错误消息
            match = re.search(pattern, command, re.IGNORECASE)
            matched_pattern = match.group(0) if match else pattern
            return f"Error: Command blocked for safety: {matched_pattern}"

    # 命令不在黑名单中
    return None


def is_sensitive_command(command: str) -> bool:
    """检测命令是否为敏感操作。

    Args:
        command: 要检查的命令字符串

    Returns:
        True 表示是敏感操作
        False 表示不是敏感操作
    """
    # 检查每个敏感模式
    for pattern in SENSITIVE_COMMAND_PATTERNS:
        # 不区分大小写匹配
        if re.search(pattern, command, re.IGNORECASE):
            return True

    return False


def get_warning_for_sensitive_command() -> str:
    """获取敏感命令的警告消息。

    Returns:
        警告消息字符串
    """
    return "[WARNING: Destructive operation]"
