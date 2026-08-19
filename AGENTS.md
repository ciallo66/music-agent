# AGENTS.md — 项目开发规范（Codex / 通用）

> 本文件是项目的开发守则，Codex 等 AI 工具开发前必须读取并严格遵守。

## 项目简介
「AI 音乐发现平台」——多用户音乐平台，核心：推荐引擎（协同过滤+内容+混合）、AI 辅助（function calling）、RAG 知识问答、播放+滚动歌词、Jamendo 数据管道。

## 技术栈
FastAPI + SQLAlchemy 2.0 + PostgreSQL + pgvector + DeepSeek API；Vue 3 + Vite + Pinia + Element Plus；Docker + Nginx；ruff + mypy + pytest + pre-commit。

## 目录结构（必须遵守）
```
app/
  main.py          # FastAPI 入口
  core/            # 配置、数据库连接
  models/          # SQLAlchemy 表模型
  schemas/         # Pydantic 请求/响应
  repositories/    # 数据访问层
  services/        # 业务逻辑层（推荐、AI 编排）
  api/v1/routes/   # 路由
frontend/          # Vue 3
scripts/           # 数据导入脚本
tests/             # 测试
docs/              # 文档
```
禁止：routes 写业务逻辑、repositories 写业务判断、一个文件堆几百行。

## 现代写法（禁止旧写法）
- 类型注解必须齐全；可选类型用 `int | None`
- SQLAlchemy 2.0：`Mapped[int] = mapped_column(...)`
- Pydantic v2：`BaseModel` + `model_validator`
- 路径用 `pathlib.Path`；字符串用 f-string；`from __future__ import annotations`
- 显式导入，禁止 `*`

## 可维护性规范
- 函数单一职责，超 50 行拆分
- 禁止硬编码（走 .env）
- 禁止死代码、未使用导入
- 每个函数有中文 docstring
- 命名：`snake_case` 函数、`PascalCase` 类、复数表名

## 开发流程
先规划再写；小步提交；关键模块带 pytest；不理解的代码不合入。

## 数据与版权
只用合法数据源（Jamendo CC 授权）；歌词只展示不进 Git；音频绝不下载托管版权作品。
