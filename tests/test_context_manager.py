"""REQ-22：上下文管理 — 手动添加文件功能的单元测试。"""

import os

import pytest

from mastercoder.context_manager import (
    parse_file_references,
    resolve_file_references,
    build_enhanced_message,
    MAX_FILE_REFERENCES,
    suggest_file_reference_completions,
)


class TestParseFileReferences:
    """测试 @ 引用解析功能。"""

    def test_parse_single_reference(self):
        """解析单个 @path 引用。"""
        text = "@src/main.py 这个文件有什么问题？"
        refs, exceeded = parse_file_references(text)
        assert refs == ["src/main.py"]
        assert not exceeded

    def test_parse_multiple_references(self):
        """解析多个 @path 引用。"""
        text = "@a.py @b.py 比较这两个文件"
        refs, exceeded = parse_file_references(text)
        assert refs == ["a.py", "b.py"]
        assert not exceeded

    def test_parse_with_spaces_in_path(self):
        """解析带空格的路径（使用引号）。"""
        text = '@"path with space/file.py" 概括这个文件'
        refs, exceeded = parse_file_references(text)
        assert refs == ["path with space/file.py"]
        assert not exceeded

    def test_parse_at_followed_by_space_not_triggered(self):
        """@ 后跟空格不触发文件引用。"""
        text = "@ someone 这个不是引用"
        refs, exceeded = parse_file_references(text)
        assert refs == []
        assert not exceeded

    def test_parse_email_not_matched(self):
        """@ 解析不会误匹配邮箱地址。"""
        text = "联系我：user@example.com 或 admin@test.org"
        refs, exceeded = parse_file_references(text)
        assert refs == []
        assert not exceeded

    def test_parse_absolute_path(self):
        """解析绝对路径。"""
        text = "@/home/user/project/main.py 这个文件"
        refs, exceeded = parse_file_references(text)
        assert refs == ["/home/user/project/main.py"]
        assert not exceeded

    def test_parse_maximum_references(self):
        """超过 10 个引用时截断。"""
        refs_list = " ".join([f"@file{i}.py" for i in range(15)])
        refs, exceeded = parse_file_references(refs_list)
        assert len(refs) == MAX_FILE_REFERENCES
        assert exceeded
        # 应该只保留前 10 个
        assert refs == [f"file{i}.py" for i in range(10)]


class TestResolveFileReferences:
    """测试文件引用解析和读取功能。"""

    def test_resolve_existing_file(self, tmp_path):
        """成功读取存在的文件。"""
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        refs = ["test.py"]
        resolved = resolve_file_references(refs, str(tmp_path))

        assert len(resolved) == 1
        assert resolved[0]["path"] == "test.py"
        assert resolved[0]["success"] is True
        assert resolved[0]["content"] == "print('hello')"

    def test_resolve_file_not_found(self, tmp_path):
        """文件不存在时返回错误。"""
        refs = ["missing.py"]
        resolved = resolve_file_references(refs, str(tmp_path))

        assert len(resolved) == 1
        assert resolved[0]["success"] is False
        assert "[Error: File not found]" in resolved[0]["content"]

    def test_resolve_directory_error(self, tmp_path):
        """引用目录时返回错误。"""
        # 创建测试目录
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        refs = ["test_dir"]
        resolved = resolve_file_references(refs, str(tmp_path))

        assert len(resolved) == 1
        assert resolved[0]["success"] is False
        assert "Directory references are not supported" in resolved[0]["content"]

    def test_resolve_binary_file_error(self, tmp_path):
        """读取二进制文件时返回错误。"""
        # 创建二进制文件
        binary_file = tmp_path / "image.png"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")

        refs = ["image.png"]
        resolved = resolve_file_references(refs, str(tmp_path))

        assert len(resolved) == 1
        assert resolved[0]["success"] is False
        assert "Cannot read binary file" in resolved[0]["content"]

    def test_resolve_file_too_large_error(self, tmp_path):
        """文件过大时返回错误。"""
        # 创建超过 1MB 的文件
        large_file = tmp_path / "large.txt"
        large_file.write_bytes(b"x" * (1024 * 1024 + 1))

        refs = ["large.txt"]
        resolved = resolve_file_references(refs, str(tmp_path))

        assert len(resolved) == 1
        assert resolved[0]["success"] is False
        assert "File too large" in resolved[0]["content"]

    def test_resolve_path_outside_sandbox(self, tmp_path):
        """路径在沙箱外时返回错误。"""
        refs = ["../../../etc/passwd"]
        resolved = resolve_file_references(refs, str(tmp_path))

        assert len(resolved) == 1
        assert resolved[0]["success"] is False
        assert "Access denied" in resolved[0]["content"]
        assert "outside project directory" in resolved[0]["content"]

    def test_resolve_relative_path(self, tmp_path):
        """相对路径正确解析。"""
        # 创建子目录和文件
        subdir = tmp_path / "src" / "mastercoder"
        subdir.mkdir(parents=True)
        test_file = subdir / "main.py"
        test_file.write_text("# main file", encoding="utf-8")

        refs = ["src/mastercoder/main.py"]
        resolved = resolve_file_references(refs, str(tmp_path))

        assert len(resolved) == 1
        assert resolved[0]["success"] is True
        assert resolved[0]["content"] == "# main file"


class TestBuildEnhancedMessage:
    """测试构建增强消息功能。"""

    def test_build_single_file_reference(self, tmp_path):
        """单个文件引用正确附加到消息。"""
        # 创建测试文件
        test_file = tmp_path / "README.md"
        test_file.write_text("# Project Title", encoding="utf-8")

        text = "@README.md 概括一下这个文件"
        enhanced = build_enhanced_message(text, str(tmp_path))

        # 应该包含用户文本（去掉 @ 引用）
        assert "概括一下这个文件" in enhanced
        # 应该包含文件内容
        assert "# Project Title" in enhanced
        assert "File: README.md" in enhanced
        assert "```markdown" in enhanced

    def test_build_multiple_file_references(self, tmp_path):
        """多个文件引用都附加到消息。"""
        # 创建测试文件
        (tmp_path / "a.py").write_text("def a(): pass", encoding="utf-8")
        (tmp_path / "b.py").write_text("def b(): pass", encoding="utf-8")

        text = "@a.py @b.py 对比差异"
        enhanced = build_enhanced_message(text, str(tmp_path))

        assert "对比差异" in enhanced
        assert "File: a.py" in enhanced
        assert "def a(): pass" in enhanced
        assert "File: b.py" in enhanced
        assert "def b(): pass" in enhanced

    def test_build_file_not_found_error(self, tmp_path):
        """引用不存在的文件时包含错误信息。"""
        text = "@missing.py 这个文件不存在"
        enhanced = build_enhanced_message(text, str(tmp_path))

        assert "这个文件不存在" in enhanced
        assert "[Error: File not found]" in enhanced

    def test_build_exceed_max_references(self, tmp_path):
        """引用超过 10 个文件时打印警告并截断。"""
        # 创建 15 个文件
        for i in range(15):
            (tmp_path / f"file{i}.py").write_text(f"# file {i}", encoding="utf-8")

        refs_text = " ".join([f"@file{i}.py" for i in range(15)])
        text = f"{refs_text} 测试超过限制"
        enhanced = build_enhanced_message(text, str(tmp_path))

        # 应该包含警告
        assert "Warning: Maximum 10 file references" in enhanced
        # 应该只包含前 10 个文件
        for i in range(10):
            assert f"File: file{i}.py" in enhanced
        # 不应该包含第 11-15 个文件
        for i in range(10, 15):
            assert f"File: file{i}.py" not in enhanced

    def test_build_no_references(self):
        """没有文件引用时返回原始文本。"""
        text = "这是一个普通的消息"
        enhanced = build_enhanced_message(text, "/tmp")

        assert enhanced == text

    def test_build_with_language_detection(self, tmp_path):
        """文件语言正确检测。"""
        # 测试 Python 文件
        (tmp_path / "test.py").write_text("print('hello')", encoding="utf-8")
        text = "@test.py"
        enhanced = build_enhanced_message(text, str(tmp_path))
        assert "```python" in enhanced

        # 测试 JavaScript 文件
        (tmp_path / "test.js").write_text("console.log('hello')", encoding="utf-8")
        text = "@test.js"
        enhanced = build_enhanced_message(text, str(tmp_path))
        assert "```javascript" in enhanced

    def test_build_with_quoted_path(self, tmp_path):
        """带引号的路径正确处理。"""
        # 创建带空格的目录和文件
        space_dir = tmp_path / "my project"
        space_dir.mkdir()
        test_file = space_dir / "main.py"
        test_file.write_text("# main", encoding="utf-8")

        text = '@"my project/main.py" 概括这个文件'
        enhanced = build_enhanced_message(text, str(tmp_path))

        assert "概括这个文件" in enhanced
        assert "# main" in enhanced

    def test_build_directory_reference_error(self, tmp_path):
        """目录引用显示错误信息。"""
        # 创建测试目录
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        text = "@test_dir 这个是目录"
        enhanced = build_enhanced_message(text, str(tmp_path))

        assert "这个是目录" in enhanced
        assert "Directory references are not supported" in enhanced


class TestEdgeCases:
    """测试边界情况。"""

    def test_empty_text(self):
        """空文本正确处理。"""
        refs, exceeded = parse_file_references("")
        assert refs == []
        assert not exceeded

        enhanced = build_enhanced_message("", "/tmp")
        assert enhanced == ""

    def test_at_at_end_of_line(self):
        """行尾的 @ 正确处理。"""
        text = "看看这个文件 @"
        refs, exceeded = parse_file_references(text)
        # @ 后没有路径，不应该匹配
        assert refs == []
        assert not exceeded

    def test_multiple_at_symbols(self):
        """多个连续的 @ 符号。"""
        text = "@@file.py"
        refs, exceeded = parse_file_references(text)
        # 第一个 @ 后跟 @，不符合路径规则
        assert refs == []
        assert not exceeded

    def test_at_in_code_block(self, tmp_path):
        """代码块中的 @ 符号不应该被解析。"""
        # 注意：当前实现会解析所有 @，这是一个已知的限制
        # 如果需要避免解析代码块中的 @，需要更复杂的解析逻辑
        text = "```\n@file.py\n```"
        refs, exceeded = parse_file_references(text)
        # 当前实现会解析
        assert "file.py" in refs

    def test_permission_denied(self, tmp_path):
        """无权限文件返回错误（Unix 系统）。"""
        # 跳过 Windows 系统
        if os.name == "nt":
            pytest.skip("Permission test not applicable on Windows")

        # 创建文件并移除读权限
        test_file = tmp_path / "secret.py"
        test_file.write_text("secret data", encoding="utf-8")
        test_file.chmod(0o000)

        try:
            refs = ["secret.py"]
            resolved = resolve_file_references(refs, str(tmp_path))

            assert len(resolved) == 1
            assert resolved[0]["success"] is False
            assert "Permission denied" in resolved[0]["content"]
        finally:
            # 恢复权限以便清理
            test_file.chmod(0o644)

    def test_symlink_outside_sandbox(self, tmp_path):
        """符号链接指向沙箱外被拒绝。"""
        # 跳过 Windows 系统
        if os.name == "nt":
            pytest.skip("Symlink test not applicable on Windows")

        # 创建指向 /tmp 的符号链接
        link = tmp_path / "link_to_tmp"
        link.symlink_to("/tmp")

        try:
            refs = ["link_to_tmp"]
            resolved = resolve_file_references(refs, str(tmp_path))

            assert len(resolved) == 1
            # 符号链接指向目录，应该报目录错误
            assert resolved[0]["success"] is False
            assert (
                "Directory references are not supported" in resolved[0]["content"]
                or "Access denied" in resolved[0]["content"]
            )
        finally:
            link.unlink()


class TestFileReferenceCompletion:
    """测试 @ 文件补全。"""

    def test_complete_root_level_reference(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "README.md").write_text("# readme", encoding="utf-8")

        matches = suggest_file_reference_completions("@R", str(tmp_path))

        assert matches == ["@README.md"]

    def test_complete_nested_directory_reference(self, tmp_path):
        nested = tmp_path / "src" / "mastercoder"
        nested.mkdir(parents=True)
        (nested / "main.py").write_text("print('hello')", encoding="utf-8")

        matches = suggest_file_reference_completions("@src/ma", str(tmp_path))

        assert matches == ["@src/mastercoder/"]

    def test_complete_quoted_reference_with_spaces(self, tmp_path):
        spaced = tmp_path / "my project"
        spaced.mkdir()
        (spaced / "main.py").write_text("print('hello')", encoding="utf-8")

        matches = suggest_file_reference_completions('@"my p', str(tmp_path))

        assert matches == ['@"my project/"']
