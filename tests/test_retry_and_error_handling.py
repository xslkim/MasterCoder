"""REQ-23：错误处理与重试机制单元测试

测试覆盖以下场景：
- 429 触发重试，第 2 次成功
- 500 触发重试，3 次均失败后报错
- 401 不重试
- 404 不重试
- 400 不重试
- 重试间隔符合指数退避 (1s, 2s, 4s)
- 日志写入格式正确
- 日志文件截断
"""

from pathlib import Path
from unittest.mock import patch
import urllib.error

import pytest

from mastercoder.retry import retry_request, RetryExhaustedError


class TestRetryMechanism:
    """测试重试机制"""

    def test_429_triggers_retry_and_succeeds_on_second_attempt(self) -> None:
        """429 触发重试，第 2 次成功"""
        call_count = 0

        def mock_request_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 第一次返回 429
                raise urllib.error.HTTPError(
                    url="http://test.com",
                    code=429,
                    msg="Rate Limit",
                    hdrs=None,
                    fp=None,
                )
            # 第二次成功
            return "success"

        with patch("builtins.print") as mock_print:
            result = retry_request(mock_request_func, max_retries=3)

        assert result == "success"
        assert call_count == 2  # 第一次失败，第二次成功

        # 验证打印了重试信息
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Retrying... attempt 1/3" in str(call) for call in print_calls)

    def test_500_triggers_retry_and_fails_after_3_retries(self) -> None:
        """500 触发重试，3 次均失败后报错"""
        call_count = 0

        def mock_request_func():
            nonlocal call_count
            call_count += 1
            # 每次都返回 500
            raise urllib.error.HTTPError(
                url="http://test.com",
                code=500,
                msg="Internal Server Error",
                hdrs=None,
                fp=None,
            )

        with patch("builtins.print") as mock_print:
            with pytest.raises(RetryExhaustedError):
                retry_request(mock_request_func, max_retries=3)

        assert call_count == 4  # 初始 + 3 次重试

        # 验证打印了 3 次重试信息
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert sum("Retrying... attempt" in str(call) for call in print_calls) == 3

    def test_502_triggers_retry(self) -> None:
        """502 触发重试"""
        call_count = 0

        def mock_request_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise urllib.error.HTTPError(
                    url="http://test.com",
                    code=502,
                    msg="Bad Gateway",
                    hdrs=None,
                    fp=None,
                )
            return "success"

        with patch("builtins.print"):
            result = retry_request(mock_request_func, max_retries=3)

        assert result == "success"
        assert call_count == 2

    def test_503_triggers_retry(self) -> None:
        """503 触发重试"""
        call_count = 0

        def mock_request_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise urllib.error.HTTPError(
                    url="http://test.com",
                    code=503,
                    msg="Service Unavailable",
                    hdrs=None,
                    fp=None,
                )
            return "success"

        with patch("builtins.print"):
            result = retry_request(mock_request_func, max_retries=3)

        assert result == "success"
        assert call_count == 2

    def test_connection_timeout_triggers_retry(self) -> None:
        """网络连接超时触发重试"""
        call_count = 0

        def mock_request_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise urllib.error.URLError("Connection timed out")
            return "success"

        with patch("builtins.print"):
            result = retry_request(mock_request_func, max_retries=3)

        assert result == "success"
        assert call_count == 2

    def test_401_does_not_retry(self) -> None:
        """401 不重试，直接报错"""
        call_count = 0

        def mock_request_func():
            nonlocal call_count
            call_count += 1
            raise urllib.error.HTTPError(
                url="http://test.com",
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=None,
            )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            retry_request(mock_request_func, max_retries=3)

        assert exc_info.value.code == 401
        assert call_count == 1  # 只调用一次，不重试

    def test_404_does_not_retry(self) -> None:
        """404 不重试，直接报错"""
        call_count = 0

        def mock_request_func():
            nonlocal call_count
            call_count += 1
            raise urllib.error.HTTPError(
                url="http://test.com",
                code=404,
                msg="Not Found",
                hdrs=None,
                fp=None,
            )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            retry_request(mock_request_func, max_retries=3)

        assert exc_info.value.code == 404
        assert call_count == 1

    def test_400_does_not_retry(self) -> None:
        """400 不重试，直接报错"""
        call_count = 0

        def mock_request_func():
            nonlocal call_count
            call_count += 1
            raise urllib.error.HTTPError(
                url="http://test.com",
                code=400,
                msg="Bad Request",
                hdrs=None,
                fp=None,
            )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            retry_request(mock_request_func, max_retries=3)

        assert exc_info.value.code == 400
        assert call_count == 1


class TestRetryIntervals:
    """测试重试间隔"""

    def test_exponential_backoff_intervals(self) -> None:
        """重试间隔符合指数退避 (1s, 2s, 4s)"""
        sleep_times = []

        def mock_sleep(seconds):
            sleep_times.append(seconds)

        def mock_request_func():
            raise urllib.error.HTTPError(
                url="http://test.com",
                code=500,
                msg="Internal Server Error",
                hdrs=None,
                fp=None,
            )

        with patch("time.sleep", side_effect=mock_sleep):
            with patch("builtins.print"):
                with pytest.raises(RetryExhaustedError):
                    retry_request(mock_request_func, max_retries=3)

        # 验证指数退避：1, 2, 4
        assert sleep_times == [1, 2, 4]

    def test_retry_with_actual_sleep_timing(self) -> None:
        """测试实际重试时间（验证 sleep 被调用）"""
        call_count = 0
        sleep_called = []

        def mock_request_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise urllib.error.HTTPError(
                    url="http://test.com",
                    code=429,
                    msg="Rate Limit",
                    hdrs=None,
                    fp=None,
                )
            return "success"

        def mock_sleep(seconds):
            sleep_called.append(seconds)

        with patch("time.sleep", side_effect=mock_sleep):
            with patch("builtins.print"):
                result = retry_request(mock_request_func, max_retries=3)

        assert result == "success"
        assert sleep_called == [1, 2]  # 前两次失败后重试，间隔 1s 和 2s


class TestErrorLogging:
    """测试错误日志"""

    def test_log_file_format(self, tmp_path: Path, monkeypatch) -> None:
        """日志写入格式正确"""
        from mastercoder.error_logger import ErrorLogger

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        logger = ErrorLogger()

        # 记录一个错误
        try:
            raise ValueError("Test error for logging")
        except Exception as e:
            logger.log_error(e)

        # 检查日志文件
        log_file = tmp_path / ".mastercoder" / "error.log"
        assert log_file.exists()

        log_content = log_file.read_text()

        # 验证格式：包含时间戳、ERROR、错误信息和堆栈
        assert "[20" in log_content  # 时间戳以 [202 开头
        assert "ERROR:" in log_content
        assert "Test error for logging" in log_content
        assert "Traceback" in log_content or "ValueError" in log_content

    def test_log_file_truncation(self, tmp_path: Path, monkeypatch) -> None:
        """日志文件超过 5MB 时截断（保留最后 2MB）"""
        from mastercoder.error_logger import ErrorLogger

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        logger = ErrorLogger()

        # 创建一个大于 5MB 的日志文件
        log_file = tmp_path / ".mastercoder" / "error.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # 写入 6MB 的数据
        large_content = "X" * 1024 * 1024 * 6  # 6MB
        log_file.write_text(large_content)

        # 记录一个新错误，应该触发截断
        try:
            raise ValueError("Test truncation")
        except Exception as e:
            logger.log_error(e)

        # 检查文件大小应该在 2MB 左右（加上新日志）
        file_size = log_file.stat().st_size
        assert file_size < 3 * 1024 * 1024  # 小于 3MB

        # 验证新错误被写入
        log_content = log_file.read_text()
        assert "Test truncation" in log_content

    def test_log_file_directory_creation(self, tmp_path: Path, monkeypatch) -> None:
        """日志目录不存在时自动创建"""
        from mastercoder.error_logger import ErrorLogger

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # 确保目录不存在
        log_dir = tmp_path / ".mastercoder"
        assert not log_dir.exists()

        logger = ErrorLogger()

        # 记录一个错误
        try:
            raise ValueError("Test directory creation")
        except Exception as e:
            logger.log_error(e)

        # 检查目录和文件被创建
        assert log_dir.exists()
        log_file = log_dir / "error.log"
        assert log_file.exists()


class TestGlobalExceptionHandling:
    """测试全局异常处理"""

    def test_global_exception_handler_catches_unexpected_errors(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """全局异常捕获未预期的错误"""
        from mastercoder.exception_handler import GlobalExceptionHandler

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        handler = GlobalExceptionHandler()

        # 模拟一个未捕获的异常
        try:
            raise RuntimeError("Unexpected error")
        except Exception as e:
            handler.handle_exception(e)

        # 检查错误被记录到日志
        log_file = tmp_path / ".mastercoder" / "error.log"
        assert log_file.exists()

        log_content = log_file.read_text()
        assert "Unexpected error" in log_content

    def test_global_exception_prints_user_friendly_message(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        """全局异常打印用户友好的错误信息"""
        from mastercoder.exception_handler import GlobalExceptionHandler

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        handler = GlobalExceptionHandler()

        # 模拟一个异常
        try:
            raise RuntimeError("Test error")
        except Exception as e:
            handler.handle_exception(e)

        # 检查打印的错误信息
        captured = capsys.readouterr()
        assert "Error: An unexpected error occurred:" in captured.out
        assert "Test error" in captured.out
