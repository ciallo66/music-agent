"""应用配置路径测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.core.config import BACKEND_ROOT, Settings


def test_env_file_is_bound_to_backend_directory() -> None:
    """环境变量文件不应随进程当前工作目录变化。"""
    env_file = Settings.model_config["env_file"]

    assert isinstance(env_file, Path)
    assert env_file == BACKEND_ROOT / ".env"
    # 只断言与工作目录无关这一实质，不绑定具体目录名（容器内为 /app）。
    assert env_file.is_absolute()
    assert env_file.name == ".env"


def test_default_secret_key_is_rejected() -> None:
    """示例密钥不能用于启动应用。"""
    for secret_key in ("change-me", "replace-with-a-random-secret"):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings(secret_key=secret_key)
