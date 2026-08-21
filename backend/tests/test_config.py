"""应用配置路径测试。"""

from __future__ import annotations

from pathlib import Path

from app.core.config import BACKEND_ROOT, Settings


def test_env_file_is_bound_to_backend_directory() -> None:
    """环境变量文件不应随进程当前工作目录变化。"""
    env_file = Settings.model_config["env_file"]

    assert isinstance(env_file, Path)
    assert env_file == BACKEND_ROOT / ".env"
    assert env_file.parent.name == "backend"
