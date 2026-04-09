"""错误日志模块 - 记录异常到日志文件。"""

import traceback
from datetime import datetime
from pathlib import Path


class ErrorLogger:
    """错误日志记录器。

    将异常信息记录到 ~/.mastercoder/error.log 文件。
    """

    # 日志文件路径
    LOG_DIR_NAME = ".mastercoder"
    LOG_FILE_NAME = "error.log"

    # 文件大小限制（字节）
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    TRUNCATE_KEEP_SIZE = 2 * 1024 * 1024  # 保留 2MB

    def __init__(self) -> None:
        """初始化错误日志记录器。"""
        self._log_file_path = self._get_log_file_path()
        self._ensure_log_directory()

    def _get_log_file_path(self) -> Path:
        """获取日志文件路径。

        Returns:
            日志文件路径 ~/.mastercoder/error.log
        """
        home = Path.home()
        return home / self.LOG_DIR_NAME / self.LOG_FILE_NAME

    def _ensure_log_directory(self) -> None:
        """确保日志目录存在。"""
        log_dir = self._log_file_path.parent
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

    def log_error(self, error: Exception) -> None:
        """记录错误到日志文件。

        日志格式：[2026-03-26 14:30:22] ERROR: <错误信息>\n<堆栈信息>\n

        Args:
            error: 要记录的异常对象
        """
        # 检查并截断日志文件
        self._truncate_if_needed()

        # 格式化日志条目
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_message = str(error)
        stack_trace = traceback.format_exc()

        log_entry = f"[{timestamp}] ERROR: {error_message}\n{stack_trace}\n"

        # 追加写入日志文件
        with open(self._log_file_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

    def _truncate_if_needed(self) -> None:
        """如果日志文件超过 5MB，在写入前先截断（保留最后 2MB）。"""
        if not self._log_file_path.exists():
            return

        file_size = self._log_file_path.stat().st_size

        if file_size > self.MAX_FILE_SIZE:
            self._truncate_file()

    def _truncate_file(self) -> None:
        """截断日志文件，保留最后 2MB。

        使用原子性操作：先读取、截断、再写入临时文件，最后替换原文件。
        """
        try:
            # 读取文件的最后 2MB
            with open(self._log_file_path, "r", encoding="utf-8") as f:
                # 移动到截断位置
                file_size = self._log_file_path.stat().st_size
                truncate_pos = max(0, file_size - self.TRUNCATE_KEEP_SIZE)
                f.seek(truncate_pos)

                # 读取剩余内容
                remaining_content = f.read()

            # 写入临时文件
            temp_file_path = self._log_file_path.with_suffix(".tmp")
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(remaining_content)

            # 原子性替换
            temp_file_path.replace(self._log_file_path)

        except Exception:
            # 如果截断失败，不影响主流程，继续写入
            pass

    def get_log_file_path(self) -> Path:
        """获取日志文件路径。

        Returns:
            日志文件路径
        """
        return self._log_file_path
