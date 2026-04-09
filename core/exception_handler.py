"""全局异常处理模块 - 捕获未处理的异常。"""

from typing import Optional

from mastercoder.error_logger import ErrorLogger


class GlobalExceptionHandler:
    """全局异常处理器。

    捕获未处理的异常，记录到日志文件，并打印用户友好的错误信息。
    """

    def __init__(self, debug_mode: bool = False) -> None:
        """初始化全局异常处理器。

        Args:
            debug_mode: 是否启用调试模式，调试模式下不捕获异常
        """
        self._debug_mode = debug_mode
        self._error_logger: Optional[ErrorLogger] = None

    def _get_error_logger(self) -> ErrorLogger:
        """获取错误日志记录器（延迟初始化）。

        Returns:
            ErrorLogger 实例
        """
        if self._error_logger is None:
            self._error_logger = ErrorLogger()
        return self._error_logger

    def handle_exception(self, error: Exception) -> None:
        """处理异常。

        在调试模式下直接抛出异常，否则捕获并记录错误。

        Args:
            error: 异常对象
        """
        # 调试模式下不捕获异常
        if self._debug_mode:
            raise error

        # 记录错误到日志文件
        try:
            logger = self._get_error_logger()
            logger.log_error(error)
        except Exception:
            # 日志记录失败不影响主流程
            pass

        # 打印用户友好的错误信息
        print(f"Error: An unexpected error occurred: {error}")

    def install(self) -> None:
        """安装全局异常处理器。

        设置 sys.excepthook 来捕获未处理的异常。
        """
        import sys

        def exception_hook(exc_type, exc_value, exc_traceback):
            """异常钩子函数。"""
            # 调试模式下使用默认处理
            if self._debug_mode:
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return

            # 创建异常对象
            error = exc_value
            if error is None:
                error = exc_type()

            # 处理异常
            self.handle_exception(error)

        sys.excepthook = exception_hook


# 全局异常处理器实例
_global_handler: Optional[GlobalExceptionHandler] = None


def get_global_handler(debug_mode: bool = False) -> GlobalExceptionHandler:
    """获取全局异常处理器实例。

    Args:
        debug_mode: 是否启用调试模式

    Returns:
        GlobalExceptionHandler 实例
    """
    global _global_handler
    if _global_handler is None:
        _global_handler = GlobalExceptionHandler(debug_mode=debug_mode)
    return _global_handler


def install_global_handler(debug_mode: bool = False) -> None:
    """安装全局异常处理器。

    Args:
        debug_mode: 是否启用调试模式
    """
    handler = get_global_handler(debug_mode=debug_mode)
    handler.install()
