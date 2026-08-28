# AI 音乐发现平台（music-agent）

多用户 AI 音乐平台：推荐引擎 + AI 辅助 + RAG 知识问答 + 播放/滚动歌词。

## 技术栈
- 后端：FastAPI + SQLAlchemy 2.0 + PostgreSQL + pgvector + DeepSeek API
- 向量库：pgvector（业务数据 + 向量一个库）
- 前端：Vue 3 + Vite + Pinia + Element Plus
- 部署：Docker + Nginx
- 质量：ruff + mypy + pytest + pre-commit

## 项目结构
```
backend/            # FastAPI 独立后端项目
  app/              # 后端源码
  migrations/       # Alembic 数据库迁移
  scripts/          # 数据导入和维护脚本
  tests/            # pytest 测试
  pyproject.toml    # Python 依赖与质量工具配置
frontend/           # Vue 3 独立前端项目
  src/              # 页面、状态和 API 客户端
  package.json      # Node.js 依赖与命令
docs/               # 跨端设计文档
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
cp .env.example .env   # 填入数据库、DeepSeek、Jamendo 配置

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

前端与后端代码放在同一仓库、不同目录并分别管理依赖；详细说明见 `frontend/README.md`。

## 开发规范
- 所有开发规范见 `CLAUDE.md`（Claude）和 `AGENTS.md`（Codex）
- 提交前自动跑 ruff + mypy（后端）与 ESLint + vue-tsc（前端），不合规代码进不了仓库
