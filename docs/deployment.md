# Docker 部署说明

本项目生产环境使用三个容器：PostgreSQL + pgvector、FastAPI、Nginx（同时提供 Vue 静态文件和 `/api` 反向代理）。模型通过 API 调用，不要求服务器具备 GPU。

## 服务器准备

4 核 CPU、4GB 内存和 40GB SSD 可以运行当前单机版本。服务器只需要安装：

- Docker Engine
- Docker Compose Plugin
- Git（手动拉取代码时需要）

防火墙只开放 SSH（22）和网站端口（80、443）。PostgreSQL 不映射到公网，只允许 Compose 内部网络访问。

## 首次部署

在服务器执行：

```bash
git clone <你的 GitHub 仓库地址> music-agent
cd music-agent
cp .env.production.example .env.production
```

编辑 `.env.production`：

- `POSTGRES_PASSWORD` 使用长随机值；密码只使用 URI 安全字符，避免连接串转义问题。
- `DATABASE_URL` 的主机必须是 `db`，不能写 `127.0.0.1`。
- `SECRET_KEY` 使用独立随机值，不能使用示例值。
- 填写 `DEEPSEEK_API_KEY`。
- 域名备案完成后，将 `CORS_ORIGINS` 改成实际 `https://域名`。

启动：

```bash
docker compose --env-file .env.production up -d --build
```

后端容器启动时会自动执行 `alembic upgrade head`，数据库数据保存在 `postgres_data` volume 中。

检查：

```bash
docker compose ps
curl http://127.0.0.1/health
docker compose logs -f backend
```

## 更新版本

第一版建议手动更新，确认稳定后再接 GitHub Actions：

```bash
git pull --ff-only
docker compose --env-file .env.production up -d --build
```

不要把 `.env.production`、API Key、数据库密码提交到 GitHub。后续 CI/CD 使用 GitHub Secrets 或服务器专用部署密钥。

## 数据备份

上线前建立 PostgreSQL 备份策略。示例：

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

备份文件应保存到服务器外部存储，不要提交到仓库。

## HTTPS

备案和 DNS 生效后，再为 Nginx 增加 HTTPS 证书配置。当前 Nginx 配置先支持 HTTP，SSE 已关闭代理缓冲并延长读取超时。
