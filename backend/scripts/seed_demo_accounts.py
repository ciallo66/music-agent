"""初始化演示账号与展示数据（可重复执行）。

用途：换服务器、重建数据卷之后，一条命令把展示环境恢复成可投递的状态。
脚本只做幂等写入：已有数据不会重复插入，重复执行结果一致。

写入的是**行为数据**（收藏、浏览记录、反馈、示例歌单），用于让画像页的
趋势图、活跃时段、风格分布有内容可展示。演示账号本身仍是只读的，
访客无法修改这些数据。

用法（在服务器上、后端容器内执行）：

    docker compose --env-file .env.production exec -T -w /app backend \\
        python -m scripts.seed_demo_accounts

可选参数：
    --hero-user / --hero-password   作品号（默认 hero / hero1234，展示数据挂在这个号上）
    --demo-user / --demo-password   演示号（默认 demo / demo1234，只读，给访客看）
    --favorites                     预置收藏数量（默认 12）
    --views                         预置浏览记录条数（默认 40，散布在最近 30 天）
    --feedback                      预置反馈条数（默认 8）
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models.associations import PlaylistSong
from app.models.favorite import Favorite
from app.models.play_record import PlayRecord
from app.models.playlist import Playlist
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.song import Song
from app.models.user import User, UserRole
from app.services.auth_service import AuthService, UsernameAlreadyExistsError
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

DEMO_PLAYLISTS = (
    ("夜晚通勤", "冷调开场、暖调收尾，适合夜路与长通勤"),
    ("专注时段", "器乐为主、人声占比低，写代码时不抢注意力"),
)
# 反馈动作按"更真实"的比例分布：多数是看过，少数是喜欢，个别不喜欢。
FEEDBACK_PLAN = (("seen", 4), ("like", 3), ("similar", 2), ("dislike", 1))


def ensure_user(db: Session, username: str, password: str, *, admin: bool) -> User:
    """按用户名取账号；不存在则创建，并按需要同步角色。"""
    service = AuthService(db)
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        try:
            if admin:
                service.create_admin(username, password)
            else:
                service.register(username, password)
        except UsernameAlreadyExistsError:  # 并发下可能已被另一个进程创建
            pass
        db.flush()
        user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise RuntimeError(f"账号 {username} 创建失败")
    wanted = UserRole.ADMIN.value if admin else UserRole.USER.value
    if user.role != wanted:
        user.role = wanted
    return user


def pick_song_ids(db: Session, count: int, *, offset: int = 0) -> list[int]:
    """按主键顺序取若干歌曲，用于构造稳定的展示数据。"""
    return list(db.scalars(select(Song.id).order_by(Song.id).offset(offset).limit(max(0, count))))


def seed_favorites(db: Session, user: User, song_ids: list[int]) -> int:
    """补收藏；已收藏的跳过。"""
    existing = set(db.scalars(select(Favorite.song_id).where(Favorite.user_id == user.id)).all())
    added = 0
    for song_id in song_ids:
        if song_id in existing:
            continue
        db.add(Favorite(user_id=user.id, song_id=song_id))
        added += 1
    return added


def seed_views(db: Session, user: User, song_ids: list[int], total: int) -> int:
    """写入浏览记录，时间散布在最近 30 天，覆盖「互动趋势」和「活跃时段」两个图。"""
    existing = int(
        db.scalar(select(func.count()).select_from(PlayRecord).where(PlayRecord.user_id == user.id))
        or 0
    )
    if existing > 0 or not song_ids or total <= 0:
        return 0
    now = datetime.now(timezone.utc)
    rows = []
    for index in range(total):
        song_id = song_ids[index % len(song_ids)]
        # 前 60% 集中在 19:00–23:00，其余散布全天，图上能看出「夜间更活跃」
        hour = random.choice([19, 20, 21, 22, 23]) if index % 5 < 3 else random.randint(8, 18)
        stamp = (now - timedelta(days=random.randint(0, 29))).replace(
            hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59)
        )
        rows.append({"user_id": user.id, "song_id": song_id, "played_at": stamp})
    db.execute(insert(PlayRecord), rows)
    return len(rows)


def seed_feedback(db: Session, user: User, song_ids: list[int]) -> int:
    """写入反馈：喜欢/类似会影响推荐排序，不感兴趣会把歌曲排除。"""
    existing = int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationFeedback)
            .where(RecommendationFeedback.user_id == user.id)
        )
        or 0
    )
    if existing > 0 or not song_ids:
        return 0
    cursor = 0
    added = 0
    for action, count in FEEDBACK_PLAN:
        for _ in range(count):
            if cursor >= len(song_ids):
                break
            db.add(RecommendationFeedback(user_id=user.id, song_id=song_ids[cursor], action=action))
            cursor += 1
            added += 1
    return added


def seed_playlists(db: Session, user: User, song_ids: list[int]) -> int:
    """建示例歌单；同名已存在则跳过。"""
    created = 0
    for index, (name, description) in enumerate(DEMO_PLAYLISTS):
        exists = db.scalar(
            select(Playlist).where(Playlist.user_id == user.id, Playlist.name == name)
        )
        if exists is not None:
            continue
        playlist = Playlist(user_id=user.id, name=name, description=description)
        db.add(playlist)
        db.flush()
        for position, song_id in enumerate(song_ids[index * 3 : index * 3 + 5]):
            db.execute(
                insert(PlaylistSong).values(
                    playlist_id=playlist.id, song_id=song_id, position=position
                )
            )
        created += 1
    return created


def seed_account(
    db: Session, user: User, *, favorites: int, views: int, feedback: int
) -> dict[str, int]:
    """给一个账号补齐展示数据。"""
    favorite_ids = pick_song_ids(db, favorites)
    view_ids = pick_song_ids(db, max(views, favorites), offset=2)
    feedback_ids = pick_song_ids(db, feedback, offset=20)
    stats = {
        "favorites": seed_favorites(db, user, favorite_ids),
        "views": seed_views(db, user, view_ids, views),
        "feedback": seed_feedback(db, user, feedback_ids),
        "playlists": seed_playlists(db, user, favorite_ids),
    }
    db.flush()
    return stats


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hero-user", default="hero")
    parser.add_argument("--hero-password", default="hero1234")
    parser.add_argument("--demo-user", default="demo")
    parser.add_argument("--demo-password", default="demo1234")
    parser.add_argument("--favorites", type=int, default=12)
    parser.add_argument("--views", type=int, default=40)
    parser.add_argument("--feedback", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    """创建/修复展示账号与展示数据。"""
    args = parse_args()
    with SessionLocal() as db:
        hero = ensure_user(db, args.hero_user, args.hero_password, admin=False)
        # 演示号给管理员角色，便于展示管理后台；写操作由 DEMO_USERNAME 只读保护拦住。
        demo = ensure_user(db, args.demo_user, args.demo_password, admin=True)
        db.flush()

        for user in (hero, demo):
            stats = seed_account(
                db, user, favorites=args.favorites, views=args.views, feedback=args.feedback
            )
            print(
                f"{user.username}: 收藏 +{stats['favorites']}、浏览 +{stats['views']}、"
                f"反馈 +{stats['feedback']}、歌单 +{stats['playlists']}"
            )
        db.commit()
        print("完成。演示账号只读，这些行为数据仅用于让画像页有内容可展示。")


if __name__ == "__main__":
    main()
