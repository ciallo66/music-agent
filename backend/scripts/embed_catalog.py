"""为歌曲和音乐知识切片批量生成 embedding。"""

from __future__ import annotations

import argparse

from app.core.database import SessionLocal
from app.services.embedding_batch_service import EmbeddingBatchService, EmbeddingTarget
from app.services.embedding_provider import (
    EmbeddingProviderNotConfiguredError,
    OpenAICompatibleEmbeddingProvider,
)


def parse_args() -> argparse.Namespace:
    """解析向量化命令参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("songs", "knowledge", "all"), default="all")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    """按目标执行批量向量化。"""
    args = parse_args()
    if not 1 <= args.limit <= 10000 or not 1 <= args.batch_size <= 200:
        raise SystemExit("--limit 必须在 1～10000，--batch-size 必须在 1～200")
    targets: tuple[EmbeddingTarget, ...] = (
        ("songs", "knowledge") if args.target == "all" else (args.target,)
    )
    provider = OpenAICompatibleEmbeddingProvider()
    try:
        for target in targets:
            with SessionLocal() as db:
                report = EmbeddingBatchService(db, provider).embed_missing(
                    target,
                    limit=args.limit,
                    batch_size=args.batch_size,
                    dry_run=args.dry_run,
                )
                if args.dry_run:
                    db.rollback()
                else:
                    db.commit()
            print(
                f"{target} 完成：处理 {report.processed}，剩余至少 {report.remaining}"
                + ("（预览，未写入）" if args.dry_run else "")
            )
    except EmbeddingProviderNotConfiguredError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
