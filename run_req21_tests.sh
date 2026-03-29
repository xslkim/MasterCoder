#!/bin/bash
# 只运行 REQ-21 相关的测试
pytest tests/test_req21_multiline_input.py -v --tb=short
