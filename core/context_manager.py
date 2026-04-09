"""REQ-22：上下文管理 — 手动添加文件功能。"""

from __future__ import annotations

import os
import re
from pathlib import Path

from mastercoder.security.sandbox import check_path_in_sandbox
from mastercoder.tools.read_file import ReadFileTool

MAX_FILE_REFERENCES = 10
MAX_FILE_SIZE = ReadFileTool.MAX_FILE_SIZE
_BINARY_CHECK_SIZE = ReadFileTool.BINARY_CHECK_SIZE

_QUOTED_REFERENCE_RE = re.compile(r'@"([^"]+)"')
_UNQUOTED_REFERENCE_RE = re.compile(r"(?<![a-zA-Z0-9_@])@([a-zA-Z/][a-zA-Z0-9_\-./]*)")
_QUOTED_COMPLETION_RE = re.compile(r'(?<!\S)@"([^"]*)$')
_UNQUOTED_COMPLETION_RE = re.compile(r'(?<![a-zA-Z0-9_@])@([^\s"]*)$')


def parse_file_references(text: str) -> tuple[list[str], bool]:
    """解析用户输入中的所有 @<path> 引用。"""
    refs: list[str] = []

    for match in _QUOTED_REFERENCE_RE.finditer(text):
        refs.append(match.group(1))

    for match in _UNQUOTED_REFERENCE_RE.finditer(text):
        refs.append(match.group(1))

    exceeded = len(refs) > MAX_FILE_REFERENCES
    if exceeded:
        refs = refs[:MAX_FILE_REFERENCES]
    return refs, exceeded


def _resolve_reference_path(ref: str, working_dir: str) -> tuple[Path | None, str | None]:
    sandbox_error = check_path_in_sandbox(ref, working_dir)
    if sandbox_error:
        return None, f"[{sandbox_error}]"

    try:
        ref_path = Path(ref)
        if not ref_path.is_absolute():
            ref_path = Path(working_dir) / ref_path
        return ref_path.resolve(), None
    except (OSError, RuntimeError, ValueError):
        return None, f"[Error: Invalid path: {ref}]"


def _read_reference_content(ref_path: Path, ref: str) -> tuple[bool, str]:
    if not ref_path.exists():
        return False, "[Error: File not found]"
    if ref_path.is_dir():
        return False, "[Error: Directory references are not supported, use a file path]"

    try:
        file_size = ref_path.stat().st_size
    except OSError:
        return False, f"[Error: Cannot access file: {ref}]"
    if file_size > MAX_FILE_SIZE:
        return False, f"[Error: File too large (>1MB): {ref}]"

    if not os.access(ref_path, os.R_OK):
        return False, f"[Error: Permission denied: {ref}]"

    try:
        with open(ref_path, "rb") as file_obj:
            if b"\x00" in file_obj.read(_BINARY_CHECK_SIZE):
                return False, f"[Error: Cannot read binary file: {ref}]"
    except OSError:
        return False, f"[Error: Permission denied: {ref}]"

    try:
        with open(ref_path, encoding="utf-8") as file_obj:
            return True, file_obj.read()
    except UnicodeDecodeError:
        return False, f"[Error: Cannot read binary file: {ref}]"
    except OSError:
        return False, f"[Error: Permission denied: {ref}]"


def resolve_file_references(refs: list[str], working_dir: str) -> list[dict[str, str | bool]]:
    """解析文件引用并读取文件内容。"""
    resolved: list[dict[str, str | bool]] = []

    for ref in refs:
        ref_path, error = _resolve_reference_path(ref, working_dir)
        if error:
            resolved.append({"path": ref, "success": False, "content": error})
            continue

        success, content = _read_reference_content(ref_path, ref)
        resolved.append({"path": ref, "success": success, "content": content})

    return resolved


def _detect_language(ref: str) -> str:
    ext = Path(ref).suffix.lstrip(".")
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
    return lang_map.get(ext, ext)


def _remove_file_references(text: str) -> str:
    cleaned = _QUOTED_REFERENCE_RE.sub("", text)
    cleaned = _UNQUOTED_REFERENCE_RE.sub("", cleaned)
    normalized_lines = [re.sub(r"[ \t]{2,}", " ", line).strip() for line in cleaned.splitlines()]
    return "\n".join(line for line in normalized_lines if line).strip()


def build_enhanced_message(original_text: str, working_dir: str) -> str:
    """构建增强消息，将文件内容附加到用户消息中。"""
    refs, exceeded = parse_file_references(original_text)
    if not refs:
        return original_text

    resolved = resolve_file_references(refs, working_dir)
    cleaned_text = _remove_file_references(original_text)

    parts: list[str] = []
    if cleaned_text:
        parts.append(cleaned_text)

    if exceeded:
        parts.append(
            f"Warning: Maximum {MAX_FILE_REFERENCES} file references per message, ignoring extra files"
        )

    for file_info in resolved:
        parts.append("---")
        parts.append(f"File: {file_info['path']}")
        if file_info["success"]:
            lang = _detect_language(str(file_info["path"]))
            parts.append(f"```{lang}")
            parts.append(str(file_info["content"]))
            parts.append("```")
        else:
            parts.append(str(file_info["content"]))

    parts.append("---")
    return "\n\n".join(parts)


def _extract_completion_fragment(text: str) -> tuple[str, bool] | None:
    if not text or text.endswith((" ", "\t", "\n")):
        return None

    quoted_match = _QUOTED_COMPLETION_RE.search(text)
    if quoted_match:
        return quoted_match.group(1), True

    unquoted_match = _UNQUOTED_COMPLETION_RE.search(text)
    if not unquoted_match:
        return None
    return unquoted_match.group(1), False


def suggest_file_reference_completions(text: str, working_dir: str) -> list[str]:
    """根据当前输入文本返回 @ 引用补全候选。"""
    fragment_info = _extract_completion_fragment(text)
    if fragment_info is None:
        return []

    fragment, quoted = fragment_info
    if fragment.startswith("/"):
        return []

    working_path = Path(working_dir).resolve()
    if fragment.endswith("/"):
        parent_fragment = fragment.rstrip("/")
        name_prefix = ""
    else:
        parent_fragment = str(Path(fragment).parent)
        if parent_fragment == ".":
            parent_fragment = ""
        name_prefix = Path(fragment).name

    search_dir = working_path if not parent_fragment else (working_path / parent_fragment)
    sandbox_error = check_path_in_sandbox(str(search_dir), str(working_path))
    if sandbox_error or not search_dir.exists() or not search_dir.is_dir():
        return []

    matches: list[str] = []
    for candidate in sorted(search_dir.iterdir(), key=lambda item: item.name):
        if not candidate.name.startswith(name_prefix):
            continue
        relative = candidate.relative_to(working_path).as_posix()
        if candidate.is_dir():
            relative += "/"
        if quoted or " " in relative:
            matches.append(f'@"{relative}"')
        else:
            matches.append(f"@{relative}")
    return matches


def install_file_reference_completion(working_dir: str) -> None:
    """为交互式输入安装 @ 文件补全。"""
    try:
        import readline
    except ImportError:
        return

    def _complete(_text: str, state: int) -> str | None:
        if state == 0:
            _complete.matches = suggest_file_reference_completions(
                readline.get_line_buffer(), working_dir
            )
        try:
            return _complete.matches[state]
        except IndexError:
            return None

    _complete.matches = []
    readline.set_completer_delims(" \t\n")
    readline.parse_and_bind("tab: complete")
    readline.set_completer(_complete)
