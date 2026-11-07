"""
AI Quiz Assistant - Automated & Integration Test Suite
"""
import os
import sys

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")

for _path in [_proj_root, _src_dir]:
    if _path not in sys.path:
        sys.path.insert(0, _path)
