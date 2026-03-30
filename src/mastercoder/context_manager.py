"""REQ-22：上下文管理 — 手动添加文件功能。

允许用户通过 @ 语法主动将文件内容加入当前对话上下文。
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple


# 单次输入最多引用的文件数
MAX_FILE_REFERENCES = 10

# 文件大小限制（1MB）
MAX_FILE_SIZE = 1024 * 1024


def parse_file_references(text: str) -> Tuple[List[str], bool]:
    """解析用户输入中的所有 @<path> 引用。
    
    Args:
        text: 用户输入的文本
    
    Returns:
        (文件路径列表（最多 10 个）, 是否超过限制)
    """
    refs = []
    
    # 匹配 @"path with space" 或 @path_without_space
    # @ 后必须紧跟 / 或字母，且 @ 前不能是字母（避免匹配邮箱）
    # 模式1: @"quoted path"
    quoted_pattern = r'@"([^"]+)"'
    # 模式2: @unquoted-path (到空格或字符串结束)
    # @ 后必须紧跟字母或 /，不能是其他字符（如 @）
    # 使用更明确的负向后瞻：@ 前不能是字母、数字、下划线或 @
    unquoted_pattern = r'(?<![a-zA-Z0-9_@])@([a-zA-Z/][a-zA-Z0-9_\-./]*)'
    
    # 先匹配带引号的路径
    for match in re.finditer(quoted_pattern, text):
        path = match.group(1)
        if path:
            refs.append(path)
    
    # 再匹配不带引号的路径
    for match in re.finditer(unquoted_pattern, text):
        path = match.group(1)
        if path:
            refs.append(path)
    
    # 检查是否超过限制
    exceeded = len(refs) > MAX_FILE_REFERENCES
    if exceeded:
        refs = refs[:MAX_FILE_REFERENCES]
    
    return refs, exceeded


def resolve_file_references(refs: List[str], working_dir: str) -> List[Dict]:
    """解析文件引用并读取文件内容。
    
    Args:
        refs: 文件路径列表
        working_dir: 当前工作目录
    
    Returns:
        解析结果列表，每个元素包含：
        - path: 文件路径
        - success: 是否成功
        - content: 文件内容或错误信息
    """
    resolved = []
    working_path = Path(working_dir).resolve()
    
    for ref in refs:
        result = {"path": ref, "success": False, "content": ""}
        
        try:
            # 解析路径
            ref_path = Path(ref)
            if not ref_path.is_absolute():
                ref_path = working_path / ref_path
            
            # 解析符号链接和 .. 等
            try:
                ref_path = ref_path.resolve()
            except (OSError, RuntimeError):
                # 符号链接循环等错误
                result["content"] = f"[Error: Invalid path: {ref}]"
                resolved.append(result)
                continue
            
            # 沙箱检查：确保路径在工作目录内
            try:
                ref_path.relative_to(working_path)
            except ValueError:
                result["content"] = "[Error: Access denied: path is outside project directory]"
                resolved.append(result)
                continue
            
            # 检查是否为目录
            if ref_path.is_dir():
                result["content"] = (
                    "[Error: Directory references are not supported, use a file path]"
                )
                resolved.append(result)
                continue
            
            # 检查文件是否存在
            if not ref_path.exists():
                result["content"] = "[Error: File not found]"
                resolved.append(result)
                continue
            
            # 检查文件大小
            file_size = ref_path.stat().st_size
            if file_size > MAX_FILE_SIZE:
                result["content"] = f"[Error: File too large (>1MB): {ref}]"
                resolved.append(result)
                continue
            
            # 读取文件内容
            try:
                content = ref_path.read_text(encoding="utf-8")
                
                # 检查是否为二进制文件（检查 null 字节）
                if "\x00" in content:
                    result["content"] = f"[Error: Cannot read binary file: {ref}]"
                    resolved.append(result)
                    continue
                
                result["success"] = True
                result["content"] = content
            
            except UnicodeDecodeError:
                result["content"] = f"[Error: Cannot read binary file: {ref}]"
        
        except PermissionError:
            result["content"] = f"[Error: Permission denied: {ref}]"
        except Exception as e:
            result["content"] = f"[Error: {str(e)}]"
        
        resolved.append(result)
    
    return resolved


def build_enhanced_message(original_text: str, working_dir: str) -> str:
    """构建增强消息，将文件内容附加到用户消息中。
    
    Args:
        original_text: 用户输入的原始文本
        working_dir: 当前工作目录
    
    Returns:
        增强后的消息文本
    """
    # 解析文件引用
    refs, exceeded = parse_file_references(original_text)
    
    if not refs:
        return original_text
    
    # 解析文件内容
    resolved = resolve_file_references(refs, working_dir)
    
    # 移除原始文本中的 @path 引用
    cleaned_text = original_text
    
    # 先移除带引号的引用
    cleaned_text = re.sub(r'@"[^"]+"\s*', "", cleaned_text)
    # 再移除不带引号的引用
    cleaned_text = re.sub(r'(?<![a-zA-Z0-9_@])@[a-zA-Z/][a-zA-Z0-9_\-./]*\s*', "", cleaned_text)
    # 清理多余的空格
    cleaned_text = " ".join(cleaned_text.split())
    
    # 构建增强消息
    parts = [cleaned_text]
    
    if exceeded:
        warning_msg = f"Warning: Maximum {MAX_FILE_REFERENCES} file references per message, ignoring extra files"
        parts.append(f"\n{warning_msg}")
    
    # 添加文件内容
    for file_info in resolved:
        parts.append("\n---")
        parts.append(f"\nFile: {file_info['path']}")
        
        if file_info["success"]:
            # 根据文件扩展名确定语言
            ext = Path(file_info["path"]).suffix.lstrip(".")
            lang_map = {
                "py": "python",
                "js": "javascript",
                "ts": "typescript",
                "java": "java",
                "c": "c",
                "cpp": "cpp",
                "h": "c",
                "hpp": "cpp",
                "go": "go",
                "rs": "rust",
                "rb": "ruby",
                "php": "php",
                "swift": "swift",
                "kt": "kotlin",
                "scala": "scala",
                "sh": "bash",
                "bash": "bash",
                "zsh": "bash",
                "sql": "sql",
                "html": "html",
                "htm": "html",
                "css": "css",
                "scss": "scss",
                "json": "json",
                "xml": "xml",
                "yaml": "yaml",
                "yml": "yaml",
                "md": "markdown",
                "txt": "",
            }
            lang = lang_map.get(ext, ext)
            
            parts.append(f"\n```{lang}")
            parts.append(file_info["content"])
            parts.append("```")
        else:
            parts.append(f"\n{file_info['content']}")
    
    parts.append("\n---")
    
    return "".join(parts)
