"""分批补全歌曲时长：从 MusicBrainz 按 MBID 读取 length 并写回数据库。

背景：时长字段一直为空，而 MusicBrainz 的 recording 接口提供 length（毫秒）。
AcousticBrainz 的公开接口已下线，但这里只依赖 MusicBrainz，因此仍然可用。

脚本可重复执行、可中断续跑：
- 只处理 duration 为空且 analysis_metadata.mbid 存在的歌曲
- 每首之间限流 1.2 秒（MusicBrainz 要求每秒不超过 1 次请求）
- 单批写入后提交，中断后再次运行会从剩余记录继续

用法：

    docker compose --env-file .env.production exec -T -w /app backend \\
        python -m scripts.backfill_duration --limit 200
"""

from __future__ import annotations

import argparse
import time

import httpx
from app.core.database import SessionLocal
from app.models.song import Song
from sqlalchemy import select

USER_AGENT = "music-agent-duration-backfill/1.0 ( https://music-agent.cloud )"
API = "https://musicbrainz.org/ws/2/recording/{mbid}?fmt=json"
# MusicBrainz 限流：平均每秒不超过 1 次请求。
REQUEST_INTERVAL_SECONDS = 1.2


def fetch_length(client: httpx.Client, mbid: str) -> int | None:
    """读取一首 recording 的时长（毫秒）；接口没有该字段时返回 None。"""
    response = client.get(API.format(mbid=mbid), headers={"User-Agent": USER_AGENT})
    if response.status_code == 404:
        return None
    response.raise_for_status()
    body = response.json()
    length = body.get("length")
    if isinstance(length, int) and length > 0:
        return length
    return None


def fetch_length_with_retry(client: httpx.Client, mbid: str, *, attempts: int = 4) -> int | None:
    """带退避重试地读取时长：MusicBrainz 负载高时会返回 503，偶发限流不该中断整批。"""
    for attempt in range(attempts):
        try:
            return fetch_length(client, mbid)
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            if status in {429, 503} and attempt < attempts - 1:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
    return None


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100, help="本次最多处理多少首")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写库")
    return parser.parse_args()


def main() -> None:
    """按批补全时长。"""
    args = parse_args()
    if args.limit <= 0:
        raise SystemExit("--limit 必须大于 0")

    with SessionLocal() as db:
        songs = list(
            db.scalars(
                select(Song)
                .where(Song.duration.is_(None), Song.analysis_metadata.is_not(None))
                .order_by(Song.id)
                .limit(args.limit)
            )
        )
        total_missing = len(db.scalars(select(Song.id).where(Song.duration.is_(None))).all())
        print(f"待补全 {total_missing} 首，本次处理 {len(songs)} 首")

        filled = 0
        skipped = 0
        failed = 0
        with httpx.Client(timeout=30.0) as client:
            for index, song in enumerate(songs, start=1):
                metadata = song.analysis_metadata or {}
                mbid = metadata.get("mbid") if isinstance(metadata, dict) else None
                if not isinstance(mbid, str) or not mbid:
                    skipped += 1
                    continue
                try:
                    milliseconds = fetch_length_with_retry(client, mbid)
                except httpx.HTTPError as error:
                    failed += 1
                    print(f"  [{index}/{len(songs)}] {song.id} 请求失败：{error}")
                    time.sleep(REQUEST_INTERVAL_SECONDS)
                    continue
                if milliseconds is None:
                    skipped += 1
                else:
                    # 数据集里的 length 是毫秒；库里 duration 用秒。
                    song.duration = max(1, round(milliseconds / 1000))
                    filled += 1
                if index % 20 == 0:
                    db.commit()
                    print(
                        f"  进度 {index}/{len(songs)}：已补 {filled}，跳过 {skipped}，失败 {failed}"
                    )
                    if args.dry_run:
                        raise SystemExit("dry-run：已完成抽样，未写库")
                time.sleep(REQUEST_INTERVAL_SECONDS)

        if args.dry_run:
            db.rollback()
            print(f"dry-run：可补 {filled} 首，跳过 {skipped}，失败 {failed}（未写库）")
            return
        db.commit()
        print(f"完成：补全 {filled} 首，跳过 {skipped}，失败 {failed}")


if __name__ == "__main__":
    main()
