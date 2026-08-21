# AGENTS.md — 项目开发规范（Codex / 通用）

> 本文件是项目的开发守则，Codex 等 AI 工具开发前必须读取。规则按约束强度分为三级，发生冲突时优先遵守更高等级规则。

## 规则等级

- **L1 必须（阻断）**：涉及正确性、安全、版权或架构边界。违反时不得交付或合入。
- **L2 原则上（需说明例外）**：通常必须遵守；确有合理原因时可以例外，但交付时必须说明原因、影响和验证结果。
- **L3 建议（不阻断）**：用于提升一致性和可维护性，不因单独违反而阻断交付。

## 项目简介

「AI 音乐发现平台」——多用户音乐平台，核心：推荐引擎（内容+热门兜底，协同过滤已实现）、AI 辅助（function calling）、RAG 知识问答、播放+滚动歌词、Jamendo 数据管道。

## 技术栈

FastAPI + SQLAlchemy 2.0 + PostgreSQL + pgvector + DeepSeek API；Vue 3 + Vite + Pinia + Element Plus；Docker + Nginx；ruff + mypy + pytest + pre-commit。

## L1 必须（阻断）

### 环境与真实性

- 开发前读取实际项目文件，确认语言、框架、依赖版本和现有实现；信息不足且无法确认时，先询问用户。
- 禁止编造项目中不存在的 import、依赖、工具类、方法或 API。
- 只使用项目实际版本支持的语法和 API；新增后端依赖必须在 `backend/pyproject.toml` 中声明并说明原因。
- 业务规则不明确时不得擅自决定默认值、错误码、自动创建记录等行为。

### 目录与分层

目录结构：

```
backend/
  app/             # FastAPI 源码（core/models/schemas/repositories/services/api）
  migrations/      # Alembic 迁移
  scripts/         # 数据导入与后端维护脚本
  tests/           # pytest 测试
  pyproject.toml   # 后端依赖与工具配置
frontend/          # Vue 3
docs/              # 文档
```

- routes 只负责参数校验和调用 service，不写业务逻辑。
- repositories 只负责数据访问，不写业务判断。
- services 承载业务逻辑、推荐和 AI 编排。

### 代码、安全与版权

- 类型注解必须覆盖公共接口和核心业务边界。
- 使用 SQLAlchemy 2.0 的 `Mapped` / `mapped_column` 写法和 Pydantic v2 API。
- 密钥、密码和环境相关 URL 必须通过 `.env` / settings 配置，禁止写入源码或 Git。
- 禁止死代码、未使用导入和星号导入。
- 推荐引擎、function calling、数据管道等关键模块必须有 pytest 测试。
- 只使用合法授权的数据源；歌词只展示且不进入 Git；音频不得下载或托管版权作品。
- 交付前必须运行适用的 Ruff、mypy 和 pytest，并明确报告通过项与未验证项。

## L2 原则上（需说明例外）

- 可选类型使用 `int | None`，模块使用 `from __future__ import annotations`。
- 文件系统路径使用 `pathlib.Path`；存在变量插值时使用 f-string。
- 公共接口、复杂业务函数和不直观的辅助函数使用中文 docstring。
- 函数保持单一职责；超过 50 行时优先拆分，若保留需确保流程仍清晰且可测试。
- 新功能和架构调整先在 `docs/` 写清方案；简单、低风险修复可在交付说明中记录方案。
- 不在规范目录外新增文件；确有架构需要时先说明理由。

## L3 建议（不阻断）

- 函数和变量使用 `snake_case`，类使用 `PascalCase`，常量使用全大写，表名使用复数。
- 保持小步、单一目的提交；通常一次提交控制在几百行内，生成文件和机械性变更除外。
- 优先复用现有模块，避免一次性临时代码和无必要抽象。
- AI 生成的代码应能解释其用途、依赖和主要执行流程。
