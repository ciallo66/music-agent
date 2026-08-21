"""pytest共享数据库与FastAPI测试夹具。"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from app.core.database import engine, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


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
