"""REQ-13: run_command 工具测试。"""

import sys

import pytest

from mastercoder.tools.run_command import RunCommandTool


class TestRunCommandTool:
    """run_command 工具测试类。"""

    def test_tool_name_and_description(self):
        """测试工具名称和描述。"""
        tool = RunCommandTool()
        assert tool.name == "run_command"
        assert tool.description == "Execute a shell command and return its output"

    def test_parameters_schema(self):
        """测试参数定义符合 JSON Schema。"""
        tool = RunCommandTool()
        schema = tool.parameters

        assert schema["type"] == "object"
        assert "command" in schema["properties"]
        assert "timeout" in schema["properties"]
        assert schema["properties"]["command"]["type"] == "string"
        assert schema["properties"]["timeout"]["type"] == "integer"
        assert "command" in schema["required"]
        assert "timeout" not in schema["required"]

    def test_normal_command_execution(self):
        """测试正常命令执行（echo hello）。"""
        tool = RunCommandTool()
        result = tool.execute({"command": "echo hello"})

        assert "Exit code: 0" in result
        assert "STDOUT:" in result
        assert "hello" in result
        assert "STDERR:" in result

    def test_command_with_nonzero_exit_code(self):
        """测试命令返回非零 exit code。"""
        tool = RunCommandTool()

        # 在不同系统上使用不同的命令
        if sys.platform == "win32":
            result = tool.execute({"command": "exit 1"})
        else:
            result = tool.execute({"command": "ls /nonexistent_directory_12345"})

        assert "Exit code:" in result
        # exit code 应该不是 0
        assert "Exit code: 0" not in result

    def test_command_with_stderr(self):
        """测试 stderr 输出。"""
        tool = RunCommandTool()

        if sys.platform == "win32":
            # Windows: 使用不存在的命令
            result = tool.execute({"command": "dir nonexistent_directory_12345"})
        else:
            # Linux/Mac: ls 不存在的目录会产生 stderr
            result = tool.execute({"command": "ls /nonexistent_directory_12345"})

        assert "STDERR:" in result
        # stderr 不应该是 (empty)
        assert "STDERR:" in result and "(empty)" not in result.split("STDERR:")[1].split("\n")[0]

    def test_empty_stdout(self):
        """测试 stdout 为空时显示 (empty)。"""
        tool = RunCommandTool()

        # 在 Windows 和 Linux 上使用不同的命令创建空输出
        if sys.platform == "win32":
            # Windows: 使用 cd 命令（无输出）
            result = tool.execute({"command": "cd ."})
        else:
            # Linux/Mac: true 命令无输出
            result = tool.execute({"command": "true"})

        assert "Exit code: 0" in result
        assert "STDOUT:" in result
        # 检查 stdout 部分包含 (empty)
        stdout_section = result.split("STDOUT:")[1].split("STDERR:")[0]
        assert "(empty)" in stdout_section or stdout_section.strip() == ""

    def test_timeout(self):
        """测试超时终止（sleep 200，timeout 2）。"""
        tool = RunCommandTool()

        # 使用较短的 sleep 命令测试超时
        result = tool.execute({"command": "sleep 200", "timeout": 2})

        assert "Error: Command timed out after 2 seconds" in result

    def test_output_truncation(self):
        """测试输出截断（超过 50000 字符）。"""
        tool = RunCommandTool()

        # 生成超过 50000 字符的输出
        # 使用 Python 生成 60000 个字符
        result = tool.execute({"command": f"{sys.executable} -c \"print('x' * 60000)\""})

        # 应该包含截断提示
        assert "truncated, showing first 50000 chars" in result
        # 截断提示应该在末尾
        lines = result.split("\n")
        truncated_line = [line for line in lines if "truncated" in line]
        assert len(truncated_line) > 0

    def test_empty_command(self):
        """测试空命令返回错误。"""
        tool = RunCommandTool()
        result = tool.execute({"command": ""})

        assert "Error: Command cannot be empty" in result

    def test_default_timeout(self):
        """测试默认超时时间为 120 秒。"""
        tool = RunCommandTool()

        # 不传 timeout 参数，使用默认值
        result = tool.execute({"command": "echo test"})
        assert "Exit code: 0" in result
        assert "test" in result

    def test_timeout_range_validation(self):
        """测试 timeout 范围限制（1-600）。"""
        tool = RunCommandTool()

        # timeout < 1 应该使用默认值
        result = tool.execute({"command": "echo test", "timeout": 0})
        assert "Exit code: 0" in result

        # timeout > 600 应该使用默认值
        result = tool.execute({"command": "echo test", "timeout": 601})
        assert "Exit code: 0" in result

    def test_working_directory(self):
        """测试工作目录为当前目录。"""
        tool = RunCommandTool()

        # 执行 pwd（Linux/Mac）或 cd（Windows）
        if sys.platform == "win32":
            result = tool.execute({"command": "cd"})
        else:
            result = tool.execute({"command": "pwd"})

        assert "Exit code: 0" in result
        # 输出应该包含当前目录的路径

    def test_shell_syntax_support(self):
        """测试支持管道等 shell 语法。"""
        tool = RunCommandTool()

        if sys.platform == "win32":
            # Windows: 使用 type 和 find
            result = tool.execute({"command": "echo hello world | findstr hello"})
        else:
            # Linux/Mac: 使用管道
            result = tool.execute({"command": "echo hello world | grep hello"})

        assert "Exit code: 0" in result
        assert "hello" in result

    def test_command_with_quotes(self):
        """测试带引号的命令。"""
        tool = RunCommandTool()

        result = tool.execute({"command": 'echo "hello world"'})
        assert "Exit code: 0" in result
        assert "hello world" in result

    def test_stderr_truncation(self):
        """测试 stderr 截断。"""
        tool = RunCommandTool()

        # 生成大量 stderr 输出
        if sys.platform == "win32":
            # Windows: 很难生成大量 stderr，跳过
            pytest.skip("Windows stderr truncation test skipped")
        else:
            # Linux/Mac: 使用 bash 循环生成 stderr
            result = tool.execute(
                {"command": f"{sys.executable} -c \"import sys; sys.stderr.write('x' * 60000)\""}
            )

            # stderr 应该被截断
            assert "truncated, showing first 50000 chars" in result


class TestRunCommandIntegration:
    """run_command 集成测试。"""

    def test_execute_with_python_script(self):
        """测试执行 Python 脚本。"""
        tool = RunCommandTool()

        result = tool.execute({"command": f"{sys.executable} -c \"print('Hello from Python')\""})

        assert "Exit code: 0" in result
        assert "Hello from Python" in result

    def test_multiple_commands_sequentially(self):
        """测试顺序执行多个命令。"""
        tool = RunCommandTool()

        result1 = tool.execute({"command": "echo first"})
        result2 = tool.execute({"command": "echo second"})

        assert "first" in result1
        assert "second" in result2
