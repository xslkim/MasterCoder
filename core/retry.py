"""重试机制模块 - 实现指数退避的自动重试。"""

import time
import urllib.error
from typing import Any, Callable


class RetryExhaustedError(Exception):
    """重试次数耗尽后抛出的异常。"""

    pass


# 需要重试的 HTTP 状态码
RETRYABLE_STATUS_CODES = {429, 500, 502, 503}

# 不需要重试的 HTTP 状态码
NON_RETRYABLE_STATUS_CODES = {400, 401, 404}


def is_retryable_error(error: Exception) -> bool:
    """判断错误是否可以重试。

    Args:
        error: 异常对象

    Returns:
        True 如果可以重试，False 否则
    """
    # HTTP 错误
    if isinstance(error, urllib.error.HTTPError):
        # 429, 500, 502, 503 触发重试
        if error.code in RETRYABLE_STATUS_CODES:
            return True
        # 400, 401, 404 不重试
        if error.code in NON_RETRYABLE_STATUS_CODES:
            return False
        # 其他 HTTP 错误也不重试
        return False

    # URL 错误（包括连接超时）
    if isinstance(error, urllib.error.URLError):
        return True

    # 其他类型的错误不重试
    return False


def retry_request(
    request_func: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """执行请求并在失败时自动重试。

    重试策略：指数退避，间隔为 1s, 2s, 4s

    Args:
        request_func: 要执行的请求函数
        max_retries: 最大重试次数，默认 3 次
        base_delay: 基础延迟时间（秒），默认 1.0

    Returns:
        请求函数的返回值

    Raises:
        RetryExhaustedError: 重试次数耗尽后仍失败
        Exception: 遇到不可重试的错误时直接抛出原始异常
    """
    retry_count = 0
    last_error = None

    while retry_count <= max_retries:
        try:
            return request_func()
        except Exception as e:
            last_error = e

            # 检查是否可以重试
            if not is_retryable_error(e):
                # 不可重试的错误直接抛出
                raise

            # 已经达到最大重试次数
            if retry_count >= max_retries:
                break

            # 打印重试信息
            print(f"[Retrying... attempt {retry_count + 1}/{max_retries}]")

            # 计算退避时间：1s, 2s, 4s
            delay = base_delay * (2**retry_count)
            time.sleep(delay)

            retry_count += 1

    # 重试次数耗尽，抛出 RetryExhaustedError
    raise RetryExhaustedError(
        f"Request failed after {max_retries} retries: {last_error}"
    ) from last_error
