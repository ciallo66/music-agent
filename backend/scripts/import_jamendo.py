"""从 Jamendo 分页导入歌曲元数据。"""

from __future__ import annotations

import argparse

from app.core.database import SessionLocal
from app.services.jamendo_import_service import (
    JamendoClient,
    JamendoImportError,
    JamendoImportService,
)


def parse_args() -> argparse.Namespace:
    """解析导入命令行参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100, help="最多导入条数，默认 100")
    parser.add_argument("--batch-size", type=int, default=50, help="每页请求条数，默认 50")
    parser.add_argument("--dry-run", action="store_true", help="只抓取和校验，不写入数据库")
    return parser.parse_args()


def main() -> None:
    """执行分页导入，并按批次提交事务。"""
    args = parse_args()
    if not 1 <= args.limit <= 10000 or not 1 <= args.batch_size <= 200:
        raise SystemExit("--limit 必须在 1～10000，--batch-size 必须在 1～200")
    try:
        _run_import(args)
    except JamendoImportError as error:
        raise SystemExit(str(error)) from error


def _run_import(args: argparse.Namespace) -> None:
    """执行导入循环，单独拆出便于命令行错误处理。"""
    client = JamendoClient()
    total = fetched = created = updated = skipped = 0
    try:
        while total < args.limit:
            requested = min(args.batch_size, args.limit - total)
            page = client.fetch_page(offset=total, limit=requested)
            if page.raw_count == 0:
                break
            with SessionLocal() as db:
                report = JamendoImportService(db).import_tracks(
                    page.tracks,
                    dry_run=args.dry_run,
                )
                if args.dry_run:
                    db.rollback()
                else:
                    db.commit()
            fetched += report.fetched
            created += report.created
            updated += report.updated
            skipped += report.skipped + sum(page.failure_reasons.values())
            total += page.raw_count
            print(f"已读取 {total}/{args.limit}，新增 {created}，更新 {updated}，跳过 {skipped}")
            if page.raw_count < requested:
                break
    finally:
        client.close()
    print(f"完成：读取 {fetched}，新增 {created}，更新 {updated}，跳过 {skipped}")


if __name__ == "__main__":
    main()
