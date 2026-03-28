"""测试 MasterCoder 主入口功能。"""

import subprocess
import sys
import signal
import time


def test_startup_and_exit():
    """测试程序启动、欢迎信息和 /exit 退出。"""
    process = subprocess.Popen(
        [sys.executable