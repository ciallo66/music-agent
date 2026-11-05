# AI 智能体工具（music-agent）

多用户 AI 智能体工具：以音乐数据作为当前演示载体，提供工具调用、推荐分析、RAG 知识问答，以及需用户确认的写操作。

> **数据与版权**：曲目数据来自 AcousticBrainz（开源音频分析，提供节拍、调性、频谱等特征），展示元数据与时长由 MusicBrainz 补齐，均为开放数据。
> 本平台**不下载、不托管音频，不提供播放**；**歌词不做存储与展示**，文本类字段不进入数据库。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI 0.139 · SQLAlchemy 2.0 · Alembic · Uvicorn |
| 数据库 | PostgreSQL + pgvector（业务数据与向量同库） |
| 认证 | PyJWT 双 Token + Argon2id |
| AI | DeepSeek API（function calling + RAG，httpx 直连，无额外 SDK） |
| 前端 | Vue 3 · Vite · TypeScript · Pinia · Element Plus · ECharts |
| 质量 | ruff · mypy · pytest · ESLint · Prettier · vue-tsc · pre-commit |
| 部署 | Docker Compose · Nginx · GitHub Actions |

运行环境：Python 3.10+（CI 使用 3.12），Node 22。

## 项目结构

```
backend/            # FastAPI 独立后端项目
  app/              # 分层源码：api / core / models / repositories / schemas / services / workers
  migrations/       # Alembic 数据库迁移
  scripts/          # 数据导入与运维脚本
  tests/            # pytest 测试
  pyproject.toml    # Python 依赖与质量工具配置
frontend/           # Vue 3 独立前端项目
  src/              # 页面、状态和 API 客户端
  package.json      # Node.js 依赖与命令
docs/               # 设计文档
```

## 快速开始（后端）

```bash
# 1. 进入后端并创建虚拟环境
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Mac/Linux: source .venv/bin/activate

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 配置环境
cp .env.example .env   # 填入数据库、DeepSeek 等配置

# 4. 启动
uvicorn app.main:app --reload
```

运行后端测试时必须使用独立数据库，不得复用开发库：

```bash
cd backend
# Windows PowerShell
$env:TEST_DATABASE_URL="postgresql+psycopg://postgres:密码@127.0.0.1:5432/music_agent_test"
alembic upgrade head
python -m pytest tests -q
```

首次配置 Git 门禁时回到仓库根目录执行 `backend/.venv/Scripts/pre-commit install`（Linux/macOS 使用对应的 `bin/pre-commit`）。

## 快速开始（前端）

```bash
cd frontend
npm install
npm run dev
```

## Docker 部署

生产环境部署说明见 [`docs/deployment.md`](docs/deployment.md)。当前 Compose 包含 PostgreSQL + pgvector、FastAPI 和 Nginx，服务器不需要 GPU；生产环境变量模板见 `.env.production.example`。

前端与后端代码放在同一仓库、不同目录并分别管理依赖；详细说明见 [`frontend/README.md`](frontend/README.md)。

## 文档索引

- [`docs/deployment.md`](docs/deployment.md) — 生产环境部署说明
- [`docs/frontend-visual.md`](docs/frontend-visual.md) — 前端视觉与交互规范（设计令牌、图标、状态与自查清单）
- `docs/data-import.md` — 数据导入管道
- `docs/web-search.md` — 联网搜索能力
- `docs/agent-fallback.md` — Agent 异常兜底策略
- `docs/agent-tool-security.md` — 工具调用安全边界
- [`backend/migrations/README.md`](backend/migrations/README.md) — 数据库迁移说明

## 开发规范

- 所有开发规范见 `CLAUDE.md`（Claude）和 `AGENTS.md`（Codex）
- 提交前自动跑 ruff + mypy（后端）与 ESLint + vue-tsc（前端），不合规代码进不了仓库
