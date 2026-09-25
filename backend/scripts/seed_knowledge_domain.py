"""把音乐领域通识写入知识库并生成向量（幂等）。

为什么需要：原知识库只有 48 条（流派 20 / 乐理 10 / 乐器 10 / 特征 8），
曲库却有 931 首歌、84 位歌手，且以游戏影视原声、德国说唱、日本同人电子、独立摇滚为主。
结果"坂本龙一是谁""这款游戏配乐什么风格"这类问题必然检索不到内容。

幂等策略：按 `source + content` 判断是否已存在，已存在则跳过（不重复插入）。
向量随条目一起生成，避免写入后还要再跑一次 embed_catalog。

用法：
    python -m scripts.seed_knowledge_domain --target all
    python -m scripts.seed_knowledge_domain --target artists --dry-run
"""

from __future__ import annotations

import argparse

from app.core.database import SessionLocal
from app.models.music_knowledge import MusicKnowledge
from app.services.embedding_provider import (
    EmbeddingProviderNotConfiguredError,
    OpenAICompatibleEmbeddingProvider,
)
from app.services.knowledge_domain_data import (
    ARTIST_ENTRIES,
    FEATURE_ENTRIES,
    GENRE_ENTRIES,
    SOUNDTRACK_ENTRIES,
    THEORY_ENTRIES,
)
from sqlalchemy import select

TARGETS: dict[str, tuple[str, tuple[str, ...]]] = {
    "genres": ("流派通识整理", GENRE_ENTRIES),
    "artists": ("曲库歌手通识整理", ARTIST_ENTRIES),
    "theory": ("乐理通识整理", THEORY_ENTRIES),
    "features": ("音乐特征指标整理", FEATURE_ENTRIES),
    "soundtracks": ("游戏影视配乐整理", SOUNDTRACK_ENTRIES),
}


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=(*TARGETS.keys(), "all"),
        default="all",
        help="要写入的知识类别",
    )
    parser.add_argument("--dry-run", action="store_true", help="只统计将新增的条数，不写库")
    parser.add_argument("--batch-size", type=int, default=16, help="单次 Embedding 批量")
    return parser.parse_args()


def main() -> None:
    """按目标类别幂等写入知识条目并生成向量。"""
    args = parse_args()
    if not 1 <= args.batch_size <= 200:
        raise SystemExit("--batch-size 必须在 1～200")
    targets = list(TARGETS) if args.target == "all" else [args.target]
    provider = OpenAICompatibleEmbeddingProvider()
    if not args.dry_run and not provider.is_configured:
        raise SystemExit("未配置 Embedding 服务，无法生成向量")

    with SessionLocal() as db:
        total_added = 0
        for key in targets:
            source, entries = TARGETS[key]
            existing = set(
                db.scalars(select(MusicKnowledge.content).where(MusicKnowledge.source == source))
            )
            pending = [text for text in entries if text not in existing]
            print(
                f"{key}: 数据 {len(entries)} 条，已存在 {len(entries) - len(pending)} 条，"
                f"待写入 {len(pending)} 条"
            )
            if args.dry_run or not pending:
                continue
            for start in range(0, len(pending), args.batch_size):
                batch = pending[start : start + args.batch_size]
                vectors = provider.embed(batch)
                if len(vectors) != len(batch):
                    raise SystemExit("Embedding 返回数量与输入不一致")
                for text, vector in zip(batch, vectors, strict=True):
                    db.add(MusicKnowledge(content=text, source=source, embedding=vector))
                db.flush()
                total_added += len(batch)
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
        total = db.scalar(select(MusicKnowledge.id).order_by(MusicKnowledge.id.desc()).limit(1))
        print(f"\n新增 {total_added} 条（{'(预览，未写入)' if args.dry_run else '已提交'}）")
        if not args.dry_run:
            from sqlalchemy import func

            count = db.scalar(select(func.count()).select_from(MusicKnowledge))
            print(f"知识库当前总数：{count} 条（最后一条 id={total}）")


if __name__ == "__main__":
    try:
        main()
    except EmbeddingProviderNotConfiguredError as error:
        raise SystemExit(str(error)) from error
