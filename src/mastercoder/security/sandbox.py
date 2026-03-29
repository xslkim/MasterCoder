"""路径沙箱检查模块。

所有文件操作工具的目标路径必须位于项目目录（工作目录）及其子目录内。
"""

from pathlib import Path
from typing import Optional


def check_path_in_sandbox(path: str, working_directory: str) -> Optional[str]:
    """检查路径是否在沙箱内。

    Args:
        path: 要检查的路径（相对或绝对）
        working_directory: 工作目录（沙箱根目录）

    Returns:
        None 表示路径合法，在沙箱内
        错误字符串表示路径越界
    """
    # 将路径解析为绝对路径
    target_path = Path(path)

    # 如果是相对路径，基于工作目录解析
    if not target_path.is_absolute():
        target_path = Path(working_directory) / target_path

    # 解析为绝对路径（处理 .. 等）
    try:
        target_absolute = target_path.resolve()
    except (OSError, RuntimeError):
        # 路径解析失败（如符号链接循环）
        return "Error: Access denied: path is outside project directory"

    # 获取工作目录的绝对路径
    working_abs = Path(working_directory).resolve()

    # 检查目标路径是否以工作目录为前缀
    try:
        # 使用 relative_to 检查是否在沙箱内
        target_absolute.relative_to(working_abs)
    except ValueError:
        # 不在沙箱内
        return "Error: Access denied: path is outside project directory"

    # 路径在沙箱内
    return None


def is_sensitive_file_operation(path: str, working_directory: str) -> bool:
    """检测文件操作是否为敏感操作（覆写已有文件）。

    Args:
        path: 目标文件路径
        working_directory: 工作目录

    Returns:
        True 表示是敏感操作（文件已存在，将被覆写）
        False 表示不是敏感操作（文件不存在）
    """
    # 将路径解析为绝对路径
    target_path = Path(path)

    if not target_path.is_absolute():
        target_path = Path(working_directory) / target_path

    # 解析绝对路径
    try:
        target_absolute = target_path.resolve()
    except (OSError, RuntimeError):
        # 路径解析失败，返回 False
        return False

    # 检查文件是否存在
    return target_absolute.exists()


def get_warning_for_sensitive_operation(operation_type: str) -> str:
    """获取敏感操作的警告消息。

    Args:
        operation_type: 操作类型（如 "file_overwrite", "command"）

    Returns:
        警告消息字符串
    """
    return "[WARNING: Destructive operation]"
