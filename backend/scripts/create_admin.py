"""交互式创建管理员账号。"""

from __future__ import annotations

from getpass import getpass

from app.core.database import SessionLocal
from app.schemas.auth import RegisterRequest
from app.services.auth_service import AuthService, UsernameAlreadyExistsError
from pydantic import ValidationError
from sqlalchemy.orm import Session


def create_admin_account(db: Session, username: str, password: str) -> None:
    """校验输入并创建管理员账号。"""
    payload = RegisterRequest(username=username, password=password)
    AuthService(db).create_admin(payload.username, payload.password.get_secret_value())


def main() -> None:
    """隐藏读取密码并交互式创建管理员。"""
    username = input("管理员用户名（6～18位，区分大小写）：")
    password = getpass("管理员密码（6～18位）：")
    password_confirmation = getpass("再次输入管理员密码：")
    if password != password_confirmation:
        raise SystemExit("两次输入的密码不一致，未创建管理员。")

    try:
        with SessionLocal() as db:
            create_admin_account(db, username, password)
    except ValidationError as error:
        raise SystemExit(f"输入校验失败：{error}") from error
    except UsernameAlreadyExistsError as error:
        raise SystemExit("用户名已存在，未创建管理员。") from error

    print(f"管理员 {username} 创建成功。")


if __name__ == "__main__":
    main()
