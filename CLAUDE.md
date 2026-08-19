# CLAUDE.md — 项目开发规范

> 本文件是项目的最高开发守则。**每次开发前必须读取并严格遵守。** 违反规范的代码会被 ruff/mypy/pre-commit 拦截。

## 项目简介
「AI 音乐发现平台」——多用户音乐平台，核心能力：
- 推荐引擎（协同过滤 + 基于内容 + 混合）
- AI 辅助（function calling：可解释推荐、口味分析、自然语言找歌）
- RAG 音乐知识问答
- 播放 + 滚动歌词（Jamendo 音频 + LRC）
- 数据管道（Jamendo API 抓 1 万条进 MySQL）

## 技术栈
- 后端：FastAPI + SQLAlchemy 2.0 + PostgreSQL + DeepSeek API
- 向量库：pgvector（PostgreSQL 内置扩展，业务数据 + 向量一个库）
- 前端：Vue 3 (Composition API) + Vite + Pinia + Element Plus
- 部署：Docker + Nginx
- 工具：ruff（格式+lint）、mypy（类型）、pytest（测试）、pre-commit（强制检查）

## <critical> 目录结构（必须遵守，不许乱放）
```
app/
  main.py          # FastAPI 入口
  core/            # 配置、数据库连接
  models/          # SQLAlchemy 表模型
  schemas/         # Pydantic 请求/响应
  repositories/    # 数据访问层（只做 SQL，不做业务判断）
  services/        # 业务逻辑层（推荐、AI 编排放这）
  api/v1/routes/   # 路由（只做参数校验 + 调 service，不写业务逻辑）
frontend/          # Vue 3 项目
scripts/           # 数据导入脚本
tests/             # pytest 测试
docs/              # 文档（规范细节、架构）
```
禁止：一个文件堆几百行、在 routes 里写业务逻辑、在 repositories 里写业务判断。

## <critical> 现代写法（必须遵守，禁止旧写法）
- 类型注解：`def f(x: int) -> str`，可选用 `int | None`（不要 `Optional[int]`）
- SQLAlchemy 2.0 风格：`Mapped[int] = mapped_column(primary_key=True)`（不要旧版 `Column()`）
- Pydantic v2：`BaseModel` + `model_validator`（不要 v1 老语法）
- 路径：`pathlib.Path`（不要 `os.path.join`）
- 字符串：f-string（不要 `%s` / `.format()`）
- 文件头：`from __future__ import annotations`
- 导入：显式导入，禁止 `from x import *`

## 可维护性规范
- **一个函数只干一件事**，超过 50 行就要拆
- **禁止硬编码**：密钥/URL/密码全部走 `.env`（settings 读取）
- **禁止死代码**：不留注释掉的代码、不留未使用的导入
- **每个函数有 docstring**（中文，说明作用 + 参数 + 返回）
- 命名：函数/变量 `snake_case`，类 `PascalCase`，表名复数，常量全大写

## 开发流程
1. **先规划再写**：新功能先在 CLAUDE.md 或 docs/ 里写清方案，再动手
2. **小步提交**：一次 commit 别超过几百行，信息清晰
3. **关键模块必须带测试**：推荐引擎、function calling、数据管道要写 pytest
4. **AI 生成的代码要能讲清**：不理解的部分不要合入主分支

## 禁止事项
- ❌ 不建规范外的目录/文件
- ❌ 不在代码里硬编码密钥、IP、API 地址
- ❌ 不写一次性临时代码
- ❌ 不引入未在 pyproject.toml 声明的依赖
- ❌ 音频版权：绝不下载/托管版权音频，只用合法数据源

## 数据与版权
- 数据源：Jamendo API（CC 授权）、Spotify 元数据、网易云元数据（只展示）
- 歌词只做展示，不提供下载，数据不进 Git 仓库（在服务器 MySQL 生成）
- 音频只用有开放授权（Jamendo），主流歌用官方外链 iframe，绝不下载托管
