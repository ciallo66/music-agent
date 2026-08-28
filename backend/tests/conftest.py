"""pytest共享数据库与FastAPI测试夹具。"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.database import engine, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if os.getenv("TEST_DATABASE_URL") is None:
    raise RuntimeError(
        "测试必须设置 TEST_DATABASE_URL，并使用独立测试数据库；禁止直接连接开发数据库。"
    )


@pytest.fixture(scope="session", autouse=True)
def migrate_test_database() -> Generator[None, None, None]:
    """测试开始前将独立数据库迁移到当前 head。"""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", os.environ["TEST_DATABASE_URL"].replace("%", "%%"))
    command.upgrade(config, "head")
    yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """在外层事务中提供可回滚的测试数据库会话。"""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """让FastAPI请求复用可回滚的测试会话。"""

    def override_get_db() -> Generator[Session, None, None]:
        """返回当前测试数据库会话。"""
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
