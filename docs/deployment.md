# Docker 部署说明

本项目生产环境使用三个容器：PostgreSQL + pgvector、FastAPI、Nginx（同时提供 Vue 静态文件和 `/api` 反向代理）。产品定位是 AI 智能体工具，音乐数据仅作为当前演示与知识载体；模型通过 API 调用，不要求服务器具备 GPU。

## 服务器准备

4 核 CPU、4GB 内存和 40GB SSD 可以运行当前单机版本。服务器只需要安装：

- Docker Engine
- Docker Compose Plugin
- Git（手动拉取代码时需要）

防火墙只开放 SSH（22）和网站端口（80、443）。PostgreSQL 不映射到公网，只允许 Compose 内部网络访问。

## 外部账号与配置位置

当前页面和业务代码开发不依赖外部密钥。进行真实联调时按需准备：

| 能力 | 需要的配置 | 官方入口 | 是否现在必须 |
|---|---|---|---|
| Agent 对话 | `DEEPSEEK_API_KEY` | [DeepSeek API Keys](https://platform.deepseek.com/api_keys) / [官方接入文档](https://api-docs.deepseek.com/) | 真实 AI 联调必须 |
| Jamendo 导入 | `JAMENDO_CLIENT_ID` | [Jamendo Developer Portal](https://devportal.jamendo.com/) / [认证文档](https://developer.jamendo.com/v3.0/authentication) | 真实 100 条导入必须 |
| RAG 向量化 | `EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL`、`EMBEDDING_MODEL` | 可选使用 [OpenAI API Keys](https://platform.openai.com/api-keys) / [Embedding 文档](https://developers.openai.com/api/docs/guides/embeddings) | 非必须；未配置时走文本检索兜底 |

密钥填写位置：

- 本地 Docker：`C:\Users\28265\Desktop\music-agent\.env.production`
- 本地直接运行 FastAPI：`C:\Users\28265\Desktop\music-agent\backend\.env`
- 服务器 Docker：计划放在 `/opt/music-agent/.env.production`
- GitHub Actions（CI/CD 开发完成后）：[仓库 Actions Secrets](https://github.com/ciallo66/music-agent/settings/secrets/actions)

不要把任何 API Key、数据库密码或 SSH 私钥发到聊天中，也不要提交到 Git；只需要告诉开发者“已配置”即可。

## 首次部署

在服务器执行：

```bash
cd /opt
git clone https://github.com/ciallo66/music-agent.git music-agent
cd /opt/music-agent
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

### GitHub Actions + GHCR

仓库中的 GitHub Actions 会在推送 `master` 后构建并推送两个镜像到 GHCR；服务器配置 `BACKEND_IMAGE`、`FRONTEND_IMAGE` 和 `FRONTEND_PORT=8080` 后执行 `docker compose pull` 与 `docker compose up -d`，由现有 Nginx 反向代理到 8080。

服务器使用镜像更新：

```bash
docker compose --env-file .env.production pull
docker compose --env-file .env.production up -d
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
