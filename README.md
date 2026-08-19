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
app/
  main.py          # FastAPI 入口
  core/            # 配置、数据库
  models/          # 表模型
  schemas/         # Pydantic
  repositories/    # 数据访问
  services/        # 业务逻辑（推荐、AI 编排）
  api/v1/routes/   # 路由
frontend/          # Vue 3
scripts/           # 数据导入
tests/             # 测试
docs/              # 文档
```

## 快速开始（后端）

```bash
# 1. 创建虚拟环境
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Mac/Linux: source .venv/bin/activate

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 配置环境
cp .env.example .env   # 填入数据库、DeepSeek、Jamendo 配置

# 4. 安装 pre-commit（提交前强制检查）
pre-commit install

# 5. 启动
uvicorn app.main:app --reload
```

## 开发规范
- 所有开发规范见 `CLAUDE.md`（Claude）和 `AGENTS.md`（Codex）
- 提交前自动跑 ruff + mypy，不合规代码进不了仓库
