# Jamendo 数据导入

导入脚本只保存歌曲元数据和 Jamendo 外链，不下载或托管音频。歌曲和歌手使用 `source + source_id` 唯一索引，重复执行会更新已有记录而不会重复插入。

## 100 条本地验收

在 `backend` 目录执行：

```powershell
$env:JAMENDO_CLIENT_ID = "你的 Jamendo client_id"
python -m scripts.import_jamendo --limit 100 --batch-size 50
```

只检查接口和字段、不写数据库时加 `--dry-run`。脚本按页读取、每页独立提交，单页失败只会回滚该页。

Docker 环境应把有效的 `JAMENDO_CLIENT_ID` 写入本机或服务器的 `.env.production`，然后在项目根目录执行：

```powershell
docker compose --env-file .env.production run --rm backend python -m scripts.import_jamendo --limit 100 --batch-size 50
```

后端镜像已包含 `scripts` 维护工具。Client ID 只放环境文件，不写入源码或 Git；Jamendo 公共测试 ID 不能作为生产凭证。

## 管理员后台任务

- `POST /api/v1/admin/imports/jamendo`：创建后台导入任务，可传 `limit` 和 `batch_size`。
- `GET /api/v1/admin/imports`：查询最近任务。
- `GET /api/v1/admin/imports/{job_id}`：查询任务进度、统计和失败原因。

接口仅允许管理员使用。同一时间只允许一个 Jamendo 任务处于待执行或执行中状态，并由数据库唯一索引提供最终并发保护。任务按页提交进度；网络错误、限流和临时服务端故障会按配置指数退避重试。

## 批量向量化

歌曲或知识切片导入后，可使用已有的 OpenAI-compatible Embedding 服务补齐向量。脚本只读取 `embedding IS NULL` 的记录，重复执行会自动跳过已经完成的记录：

```powershell
docker compose --env-file .env.production run --rm backend python -m scripts.embed_catalog --target all --limit 100 --batch-size 32
```

预览而不写入数据库：

```powershell
docker compose --env-file .env.production run --rm backend python -m scripts.embed_catalog --target songs --limit 100 --dry-run
```

需要先配置 `EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL` 和 `EMBEDDING_MODEL`。脚本按批次提交，事务提交由脚本边界负责，向量服务异常时不会提交当前批次。

## 扩大规模

确认 100 条数据和播放链接均符合授权后，再逐步提高 `--limit`。生产环境应在服务器执行脚本，让数据直接写入服务器 PostgreSQL Docker volume；GitHub 只保存代码和迁移，不保存导入数据或密钥。
