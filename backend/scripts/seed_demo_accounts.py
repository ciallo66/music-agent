"""初始化演示账号与展示数据（可重复执行）。

用途：换服务器、重建数据卷之后，一条命令把展示环境恢复成可投递的状态。
本脚本只做幂等写入，重复执行不会产生重复数据。

用法（在服务器上、后端容器内执行）：

    docker compose --env-file .env.production exec -T backend \\
        python -m scripts.seed_demo_accounts

可选参数：
    --hero-user / --hero-password      作品号（默认 hero / hero1234）
    --demo-user / --demo-password      演示号（默认 demo / demo1234，只读保护由 DEMO_USERNAME 决定）
    --favorites                        展示号预置的收藏数量（默认 6）
"""

from __future__ import annotations

import argparse

from app.core.database import SessionLocal
from app.models.associations import PlaylistSong
from app.models.favorite import Favorite
from app.models.playlist import Playlist
from app.models.song import Song
from app.models.user import User, UserRole
from app.services.auth_service import AuthService, UsernameAlreadyExistsError
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

DEMO_PLAYLIST_NAME = "夜晚通勤"
DEMO_PLAYLIST_DESCRIPTION = "冷调开场、暖调收尾"


def ensure_user(db: Session, username: str, password: str, *, admin: bool) -> User:
    """按用户名取账号；不存在则创建，并按需要同步角色。"""
    service = AuthService(db)
    existing = db.scalar(select(User).where(User.username == username))
    if existing is None:
        try:
            if admin:
                service.create_admin(username, password)
            else:
                service.register(username, password)
        except UsernameAlreadyExistsError:  # 并发下可能已被另一个进程创建
            pass
        db.flush()
        existing = db.scalar(select(User).where(User.username == username))
    if existing is None:
        raise RuntimeError(f"账号 {username} 创建失败")
    wanted = UserRole.ADMIN.value if admin else UserRole.USER.value
    if existing.role != wanted:
        existing.role = wanted
    return existing


def seed_favorites(db: Session, user: User, limit: int) -> int:
    """给展示号补齐收藏，已收藏的跳过。"""
    song_ids = list(db.scalars(select(Song.id).order_by(Song.id).limit(limit)))
    added = 0
    for song_id in song_ids:
        exists = db.scalar(
            select(Favorite).where(Favorite.user_id == user.id, Favorite.song_id == song_id)
        )
        if exists is None:
            db.add(Favorite(user_id=user.id, song_id=song_id))
            added += 1
    return added


def seed_playlist(db: Session, user: User, limit: int) -> bool:
    """给展示号建一个示例歌单；已存在则不动。"""
    exists = db.scalar(
        select(Playlist).where(Playlist.user_id == user.id, Playlist.name == DEMO_PLAYLIST_NAME)
    )
    if exists is not None:
        return False
    playlist = Playlist(
        user_id=user.id,
        name=DEMO_PLAYLIST_NAME,
        description=DEMO_PLAYLIST_DESCRIPTION,
    )
    db.add(playlist)
    db.flush()
    song_ids = list(db.scalars(select(Song.id).order_by(Song.id).limit(limit)))
    for position, song_id in enumerate(song_ids):
        db.execute(
            insert(PlaylistSong).values(playlist_id=playlist.id, song_id=song_id, position=position)
        )
    return True


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hero-user", default="hero")
    parser.add_argument("--hero-password", default="hero1234")
    parser.add_argument("--demo-user", default="demo")
    parser.add_argument("--demo-password", default="demo1234")
    parser.add_argument("--favorites", type=int, default=6)
    return parser.parse_args()


def main() -> None:
    """创建/修复展示账号与展示数据。"""
    args = parse_args()
    with SessionLocal() as db:
        hero = ensure_user(db, args.hero_user, args.hero_password, admin=False)
        # 演示号给管理员角色，便于展示管理后台；写操作由 DEMO_USERNAME 只读保护拦住。
        demo = ensure_user(db, args.demo_user, args.demo_password, admin=True)
        db.flush()

        hero_favorites = seed_favorites(db, hero, args.favorites)
        hero_playlist = seed_playlist(db, hero, max(1, args.favorites - 2))
        db.commit()

        print(
            f"完成：{hero.username}(收藏 +{hero_favorites}, 新歌单 {hero_playlist})、"
            f"{demo.username}(角色 admin，只读保护由 DEMO_USERNAME 控制)"
        )


if __name__ == "__main__":
    main()
