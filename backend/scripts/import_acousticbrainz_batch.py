"""从本地 JSONL 批量导入已整理的 AcousticBrainz 特征。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.core.database import SessionLocal
from app.models.artist import Artist
from app.models.song import Song
from sqlalchemy import select

SOURCE = "acousticbrainz"
PLACEHOLDER_ARTIST = "AcousticBrainz sample"
PLACEHOLDER_TITLE_PREFIX = "AcousticBrainz recording "


def has_real_metadata(title: str, artist_name: str) -> bool:
    """判断批量记录是否已经补齐可展示的真实曲名和艺术家。"""
    return bool(
        title
        and artist_name
        and artist_name != PLACEHOLDER_ARTIST
        and not title.startswith(PLACEHOLDER_TITLE_PREFIX)
    )


def import_file(path: Path) -> dict[str, int]:
    """幂等导入 JSONL，并返回创建、更新和跳过数量。"""
    created = updated = skipped = 0
    with SessionLocal() as db, path.open(encoding="utf-8") as source_file:
        artists: dict[str, Artist] = {}
        for line in source_file:
            payload: dict[str, Any] = json.loads(line)
            mbid = str(payload.pop("mbid", "")).strip()
            title = str(payload.get("title", "")).strip()
            artist_name = str(payload.pop("artist", "")).strip()
            if not mbid or not has_real_metadata(title, artist_name):
                skipped += 1
                continue
            artist = artists.get(artist_name)
            if artist is None:
                artist = db.scalar(
                    select(Artist).where(
                        Artist.source == SOURCE,
                        Artist.source_id == artist_name,
                    )
                )
                if artist is None:
                    artist = Artist(name=artist_name, source=SOURCE, source_id=artist_name)
                    db.add(artist)
                    db.flush()
                artists[artist_name] = artist
            values = {**payload, "artist_id": artist.id, "source": SOURCE, "source_id": mbid}
            song = db.scalar(select(Song).where(Song.source == SOURCE, Song.source_id == mbid))
            if song is None:
                db.add(Song(**values))
                created += 1
            else:
                for key, value in values.items():
                    setattr(song, key, value)
                updated += 1
            if (created + updated) % 100 == 0:
                db.flush()
        db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}


def main() -> None:
    """解析 JSONL 路径并执行批量导入。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(import_file(args.path))


if __name__ == "__main__":
    main()
