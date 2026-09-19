"""确保演示账号存在且可用（可重复执行）。

用途：登录页的「一键进入演示账号」用的是配置里的演示凭证
（`DEMO_USERNAME` / `DEMO_PASSWORD`，默认 demo / demo1234）。只要库里没有这个
账号、或密码对不上，一键进入就会提示「用户名或密码错误」。本地开发库漏建过
这个账号，正是这么挂掉的。

脚本做三件事，幂等：
1. 账号不存在则创建；已存在则把密码重置成配置里的值（换过密码也能修回来）
2. 把角色固定为 admin：演示账号要看管理后台（只读看）
3. 确保状态是 active

用法（在容器内执行，本地与线上同一套）：

    docker compose --env-file .env.production exec -T -w /app backend \\
        python -m scripts.ensure_demo_account

可选参数：
    --username / --password   覆盖环境变量里的演示凭证
    --no-admin                不提升为管理员（只看前台时可用）
"""

from __future__ import annotations

import argparse

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole, UserStatus
from sqlalchemy import select
from sqlalchemy.orm import Session


def ensure_demo_account(
    db: Session, username: str, password: str, *, promote_admin: bool = True
) -> tuple[User, bool]:
    """确保演示账号存在且密码正确，返回 (账号, 是否新建)。"""
    user = db.scalar(select(User).where(User.username == username))
    created = user is None
    if user is None:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=UserRole.ADMIN.value if promote_admin else UserRole.USER.value,
            status=UserStatus.ACTIVE.value,
        )
        db.add(user)
    else:
        # 已存在：把凭证与角色拉回配置要求的状态，避免「密码被改过」导致一键登录失败
        user.password_hash = hash_password(password)
        user.status = UserStatus.ACTIVE.value
        if promote_admin:
            user.role = UserRole.ADMIN.value
    db.commit()
    db.refresh(user)
    return user, created


def main() -> None:
    """按配置或命令行参数创建 / 修复演示账号。"""
    parser = argparse.ArgumentParser(description="确保演示账号可用")
    parser.add_argument("--username", default=settings.demo_username)
    parser.add_argument("--password", default=settings.demo_password)
    parser.add_argument("--no-admin", action="store_true", help="不把角色提升为 admin")
    args = parser.parse_args()

    with SessionLocal() as db:
        user, created = ensure_demo_account(
            db, args.username, args.password, promote_admin=not args.no_admin
        )

    action = "已创建" if created else "已更新"
    print(
        f"演示账号{action}：{user.username}（角色 {user.role}，状态 {user.status}）；"
        f"登录页一键进入请使用同一套凭证"
    )


if __name__ == "__main__":
    main()
