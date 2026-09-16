"""
conftest.py — Pytest fixtures và môi trường test cho my_bot.

Tự động:
  - Thêm src/ vào sys.path để import my_bot hoạt động mà không cần cài đặt package
  - Đặt TELEGRAM_TOKEN giả để config.py không raise RuntimeError
  - Đặt RUNNING_WEBAPP=1 để webapp/main.py không check token khi import
"""

import os
import sys
from pathlib import Path

# ── sys.path setup ─────────────────────────────────────────────────────────────
# Đảm bảo `src/` luôn ở đầu sys.path, bất kể pytest được chạy từ thư mục nào.
_repo_root = Path(__file__).resolve().parent.parent
_src_dir = _repo_root / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# ── Env vars mặc định cho test ─────────────────────────────────────────────────
os.environ.setdefault("TELEGRAM_TOKEN", "dummy-test-token")
os.environ.setdefault("RUNNING_WEBAPP", "1")
