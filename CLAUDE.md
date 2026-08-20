# CLAUDE.md — 项目开发规范

> 本文件是项目的开发守则，每次开发前必须读取。规则按约束强度分为三级；自动化工具只能覆盖其中一部分，未自动覆盖的规则仍需开发者和评审者检查。

## 规则等级

- **L1 必须（阻断）**：涉及正确性、安全、版权或架构边界。违反时不得交付或合入。
- **L2 原则上（需说明例外）**：通常必须遵守；确有合理原因时可以例外，但交付时必须说明原因、影响和验证结果。
- **L3 建议（不阻断）**：用于提升一致性和可维护性，不因单独违反而阻断交付。

## 项目简介

「AI 音乐发现平台」——多用户音乐平台，核心能力：

- 推荐引擎（基于内容 + 热门兜底；协同过滤已实现）
- AI 辅助（function calling：可解释推荐、口味分析、自然语言找歌）
- RAG 音乐知识问答
- 播放 + 滚动歌词（Jamendo 音频 + LRC）
- 数据管道（Jamendo API 抓 1 万条进 PostgreSQL）

## 技术栈

- 后端：FastAPI + SQLAlchemy 2.0 + PostgreSQL + DeepSeek API
- 向量库：pgvector（PostgreSQL 内置扩展，业务数据 + 向量一个库）
- 前端：Vue 3 (Composition API) + Vite + Pinia + Element Plus
- 部署：Docker + Nginx
- 工具：ruff（格式+lint）、mypy（类型）、pytest（测试）、pre-commit（提交前检查）

## L1 必须（阻断）

### 环境与真实性

- 开发前读取 `pyproject.toml`、现有源码和相关文档，确认实际版本、依赖、工具类和调用方式。
- 禁止编造不存在的 import、依赖、工具类、方法或 API；需要新能力时先说明并声明依赖。
- 只使用项目实际版本支持的语法和 API，禁止复制不适配当前版本的写法。
- 业务规则不明确时必须询问，不得擅自决定默认值、错误码、自动创建记录等行为。

### 目录结构与分层

```
app/
  main.py          # FastAPI 入口
  core/            # 配置、数据库连接
  models/          # SQLAlchemy 表模型
  schemas/         # Pydantic 请求/响应
  repositories/    # 数据访问层（只做 SQL，不做业务判断）
  services/        # 业务逻辑层（推荐、AI 编排放这）
  api/v1/routes/   # 路由（只做参数校验 + 调 service）
frontend/          # Vue 3 项目
scripts/           # 数据导入脚本
tests/             # pytest 测试
docs/              # 文档（规范细节、架构）
```

- routes 只做参数校验和调用 service，不写业务逻辑。
- repositories 只做数据访问，不写业务判断。
- services 承载业务逻辑、推荐和 AI 编排。

### 代码、安全与验证

- 公共接口和核心业务边界必须有完整类型注解。
- SQLAlchemy 使用 2.0 风格：`Mapped[int] = mapped_column(primary_key=True)`。
- Pydantic 使用 v2 API，例如 `BaseModel` + `model_validator`，不得使用已废弃的 v1 写法。
- 显式导入，禁止 `from x import *`；禁止死代码和未使用导入。
- 密钥、密码和环境相关 URL 必须通过 `.env` / settings 配置，禁止进入源码或 Git。
- 新增第三方依赖必须在 `pyproject.toml` 中声明，并确认与当前 Python 和框架版本兼容。
- 推荐引擎、function calling、数据管道等关键模块必须有 pytest 测试。
- 交付前必须运行适用的 Ruff、mypy 和 pytest，报告通过项、失败项和未验证项。

### 数据与版权

- 音频只使用明确开放授权的数据源（当前为 Jamendo），不得下载或托管版权音频。
- 歌词只做展示，不提供下载，数据不得进入 Git 仓库。
- 引入新的音乐或元数据来源前，必须确认许可范围和使用边界。

## L2 原则上（需说明例外）

- 可选类型使用 `int | None`，模块使用 `from __future__ import annotations`。
- 文件系统路径使用 `pathlib.Path`；第三方 API 明确要求字符串路径时可以在边界转换。
- 存在变量插值时使用 f-string；普通常量字符串不受此限制。
- 公共接口、复杂业务函数和不直观的辅助函数使用中文 docstring，说明作用及必要的参数、返回值。
- 函数保持单一职责；超过 50 行时优先拆分，若保留需保证流程清晰、复杂度可控且便于测试。
- 新功能和架构调整先在 `docs/` 写方案；简单、低风险修复可在交付说明中记录方案。
- 原则上不在既定目录外新增文件；确有需要时先说明架构理由。

## L3 建议（不阻断）

- 函数和变量使用 `snake_case`，类使用 `PascalCase`，表名使用复数，常量使用全大写。
- 保持小步、单一目的提交；通常一次提交控制在几百行内，生成文件和机械性变更除外。
- 优先复用现有模块，避免一次性临时代码和无必要抽象。
- AI 生成的代码应能解释其用途、依赖和主要执行流程。
