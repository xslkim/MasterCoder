"""REQ-15 安全与权限控制测试。"""

from pathlib import Path

from mastercoder.security.sandbox import (
    check_path_in_sandbox,
    is_sensitive_file_operation,
)
from mastercoder.security.commands import (
    check_command_blacklist,
    is_sensitive_command,
)


class TestPathSandbox:
    """路径沙箱检查测试。"""

    def test_valid_path_in_project(self, tmp_path: Path):
        """合法路径通过检查。"""
        # 在项目目录内的文件
        file_path = tmp_path / "test.txt"
        file_path.touch()

        # 相对路径
        result = check_path_in_sandbox("test.txt", str(tmp_path))
        assert result is None  # None 表示通过

        # 绝对路径
        result = check_path_in_sandbox(str(file_path), str(tmp_path))
        assert result is None

    def test_parent_directory_traversal_blocked(self, tmp_path: Path):
        """../ 穿越路径被拒绝。"""
        # 尝试访问项目目录外的文件
        result = check_path_in_sandbox("../../etc/passwd", str(tmp_path))
        assert result == "Error: Access denied: path is outside project directory"

        # 多级穿越
        result = check_path_in_sandbox("../../../tmp", str(tmp_path))
        assert result == "Error: Access denied: path is outside project directory"

    def test_symlink_outside_sandbox_blocked(self, tmp_path: Path):
        """符号链接指向沙箱外被拒绝。"""
        # 创建一个指向沙箱外的符号链接
        link_path = tmp_path / "passwd_link"
        link_path.symlink_to("/etc/passwd")

        # 尝试读取符号链接
        result = check_path_in_sandbox(str(link_path), str(tmp_path))
        assert result == "Error: Access denied: path is outside project directory"

    def test_symlink_inside_sandbox_allowed(self, tmp_path: Path):
        """符号链接指向沙箱内被允许。"""
        # 创建一个文件
        file_path = tmp_path / "test.txt"
        file_path.write_text("hello")

        # 创建指向沙箱内文件的符号链接
        link_path = tmp_path / "link.txt"
        link_path.symlink_to(file_path)

        # 应该被允许
        result = check_path_in_sandbox(str(link_path), str(tmp_path))
        assert result is None

    def test_nested_path_allowed(self, tmp_path: Path):
        """嵌套路径被允许。"""
        # 创建嵌套目录
        nested_dir = tmp_path / "a" / "b" / "c"
        nested_dir.mkdir(parents=True)

        file_path = nested_dir / "test.txt"
        file_path.touch()

        # 相对路径
        result = check_path_in_sandbox("a/b/c/test.txt", str(tmp_path))
        assert result is None

        # 绝对路径
        result = check_path_in_sandbox(str(file_path), str(tmp_path))
        assert result is None


class TestCommandBlacklist:
    """命令黑名单检查测试。"""

    def test_rm_rf_root_blocked(self):
        """rm -rf / 被拦截。"""
        result = check_command_blacklist("rm -rf /")
        assert result is not None
        assert "Error: Command blocked for safety" in result
        assert "rm -rf /" in result.lower()

        # 变体
        result = check_command_blacklist("sudo rm -rf /")
        assert result is not None

        # 大小写不敏感
        result = check_command_blacklist("RM -RF /")
        assert result is not None

    def test_mkfs_blocked(self):
        """mkfs 命令被拦截。"""
        result = check_command_blacklist("mkfs.ext4 /dev/sda1")
        assert result is not None
        assert "Error: Command blocked for safety" in result
        assert "mkfs" in result.lower()

    def test_dd_dev_blocked(self):
        """dd if=/dev/ 被拦截。"""
        result = check_command_blacklist("dd if=/dev/zero of=/dev/sda")
        assert result is not None
        assert "Error: Command blocked for safety" in result
        assert "dd if=" in result.lower()

    def test_fork_bomb_blocked(self):
        """fork bomb 被拦截。"""
        result = check_command_blacklist(":(){ :|:& };:")
        assert result is not None
        assert "Error: Command blocked for safety" in result

    def test_normal_command_allowed(self):
        """正常命令不被拦截。"""
        # ls 命令
        result = check_command_blacklist("ls -la")
        assert result is None

        # git 命令
        result = check_command_blacklist("git status")
        assert result is None

        # rm 普通文件（不是 -rf /）
        result = check_command_blacklist("rm test.txt")
        assert result is None

        # echo 命令
        result = check_command_blacklist("echo hello")
        assert result is None

    def test_blacklist_case_insensitive(self):
        """黑名单匹配不区分大小写。"""
        result = check_command_blacklist("MKFS.EXT4 /DEV/SDA1")
        assert result is not None
        assert "mkfs" in result.lower()


class TestSensitiveOperationDetection:
    """敏感操作检测测试。"""

    def test_write_file_overwrite_detection(self, tmp_path: Path):
        """write_file 覆写已有文件被检测为敏感操作。"""
        # 创建一个已存在的文件
        file_path = tmp_path / "test.txt"
        file_path.write_text("original content")

        # 检测是否为敏感操作
        result = is_sensitive_file_operation(str(file_path), str(tmp_path))
        assert result is True

    def test_write_file_new_file_not_sensitive(self, tmp_path: Path):
        """write_file 创建新文件不是敏感操作。"""
        # 不存在的文件
        file_path = tmp_path / "new_file.txt"

        result = is_sensitive_file_operation(str(file_path), str(tmp_path))
        assert result is False

    def test_rm_command_sensitive(self):
        """包含 rm 的命令被标记为敏感。"""
        result = is_sensitive_command("rm test.txt")
        assert result is True

    def test_git_push_sensitive(self):
        """包含 git push 的命令被标记为敏感。"""
        result = is_sensitive_command("git push origin main")
        assert result is True

    def test_git_reset_sensitive(self):
        """包含 git reset 的命令被标记为敏感。"""
        result = is_sensitive_command("git reset --hard HEAD~1")
        assert result is True

    def test_drop_table_sensitive(self):
        """包含 DROP TABLE 的命令被标记为敏感。"""
        result = is_sensitive_command("DROP TABLE users;")
        assert result is True

        # 大小写不敏感
        result = is_sensitive_command("drop table users;")
        assert result is True

    def test_delete_from_sensitive(self):
        """包含 DELETE FROM 的命令被标记为敏感。"""
        result = is_sensitive_command("DELETE FROM users WHERE id=1;")
        assert result is True

    def test_normal_command_not_sensitive(self):
        """正常命令不被标记为敏感。"""
        result = is_sensitive_command("ls -la")
        assert result is False

        result = is_sensitive_command("git status")
        assert result is False

        result = is_sensitive_command("echo hello")
        assert result is False
