# 数据导入

数据以**离线脚本**方式导入，不经过任何 HTTP 接口。当前曲目数据来自 AcousticBrainz（音乐特征）与 MusicBrainz（展示元数据、时长），均为开放数据；脚本只保存元数据和特征，**不下载或托管音频**。

歌曲和歌手使用 `source + source_id` 唯一索引，重复执行会更新已有记录而不会重复插入。

## 脚本一览

| 脚本 | 作用 |
|---|---|
| `scripts/import_acousticbrainz.py` | 按 MusicBrainz recording MBID 拉取单条 AcousticBrainz 特征并入库 |
| `scripts/import_acousticbrainz_batch.py` | 从本地 JSONL 批量导入已整理的 AcousticBrainz 特征 |
| `scripts/enrich_musicbrainz_metadata.py` | 导入前预处理：用 MusicBrainz 为 JSONL 补齐展示元数据 |
| `scripts/backfill_duration.py` | 分批补全歌曲时长（按 MBID 从 MusicBrainz 读取 length） |
| `scripts/embed_catalog.py` | 为歌曲和音乐知识切片批量生成 embedding |
| `scripts/seed_knowledge_domain.py` | 把音乐领域通识写入知识库并生成向量 |
| `scripts/create_admin.py` | 交互式创建管理员账号 |
| `scripts/ensure_demo_account.py` | 确保演示账号存在且可用 |
| `scripts/seed_demo_accounts.py` | 初始化演示账号与展示行为数据 |

所有脚本都在 `backend/` 目录下用 `python -m scripts.<脚本名>` 执行；带 `--dry-run` 的脚本可先预览、不写库。

## 导入曲目

### 批量导入（JSONL）

`import_acousticbrainz_batch` 读取一份已经整理好的 JSONL：

```powershell
cd backend
python -m scripts.import_acousticbrainz_batch path/to/features.jsonl
```

如果 JSONL 缺少展示元数据（歌名、艺术家、专辑等），先用 `enrich_musicbrainz_metadata` 补齐：

```powershell
python -m scripts.enrich_musicbrainz_metadata raw.jsonl enriched.jsonl --batch-size 20
```

### 单条导入（按 MBID）

```powershell
python -m scripts.import_acousticbrainz <musicbrainz-recording-mbid>
```

### 补全时长

```powershell
python -m scripts.backfill_duration --limit 100
python -m scripts.backfill_duration --limit 100 --dry-run   # 只统计，不写库
```

该脚本可重复、可中断续跑。

## 批量向量化

歌曲或知识切片导入后，用已有的 OpenAI-compatible Embedding 服务补齐向量。脚本只读取 `embedding IS NULL` 的记录，重复执行会自动跳过已经完成的记录：

```powershell
cd backend
python -m scripts.embed_catalog --target all --limit 100 --batch-size 32
```

预览而不写入数据库：

```powershell
python -m scripts.embed_catalog --target songs --limit 100 --dry-run
```

需要先配置 `EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL` 和 `EMBEDDING_MODEL`。脚本按批次提交，事务提交由脚本边界负责，向量服务异常时不会提交当前批次。

## 演示与管理员数据

```powershell
python -m scripts.ensure_demo_account
python -m scripts.seed_demo_accounts
```

两个脚本都是幂等的，可重复执行。

## Docker 环境

在服务器上执行脚本时，让数据直接写入服务器 PostgreSQL 的 Docker volume：

```powershell
docker compose --env-file .env.production run --rm backend python -m scripts.embed_catalog --target all --limit 100
```

后端镜像已包含 `scripts` 维护工具。密钥只放环境文件，不写入源码或 Git。

## 关于 Jamendo

环境文件里仍保留 `JAMENDO_*` 配置项，但当前**没有任何代码使用它们**：Jamendo 导入管道已随 `import_jobs` 表一并移除（见迁移 `20260920_14_drop_import_jobs.py`），曲目全部由 AcousticBrainz 管道导入。这些配置项如确认不再需要，可以清理。
