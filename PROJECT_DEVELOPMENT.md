# 项目开发步骤与流程 —— AI 音乐智能体（music-agent）

> 本文档是项目的**开发步骤与流程总纲**：按《AI项目技术栈.md》的技术栈分层、完成标准与开发路线组织，并吸收《Music_Agent_项目开发书_最终版.md》的 Agent 核心设计（核心工具、Agent 工作流、UI 方向、多人在线、数据与音频方案）。
> 配套文档：开发规范见 `AGENTS.md` / `CLAUDE.md`；当前进度状态见本文档「九、分阶段开发步骤与流程」与「十、开发顺序与时间线建议」。

---

## 一、项目定位

### 1. 一句话定位

> 一个以 **AI 音乐智能体**为核心的多人在线 Web 应用。音乐库、播放器、收藏、歌单等基础音乐功能作为产品承载层，用于提供真实的音乐数据和交互场景；核心能力是让 Agent 理解音乐数据、调用业务工具、分析音乐，并与用户进行自然语言对话。

**不是**“做一个网易云”，而是“做一个真正能理解音乐数据、分析音乐并与用户对话的 AI Agent”。

### 2. 核心链路

```text
音乐数据 → Agent → Tool Calling → 数据分析 → 推理 → 自然语言回答
```

### 3. 用户可以提出的问题

- “分析一下这首歌为什么听起来比较忧郁。”
- “这首歌的节奏和情绪有什么特点？”
- “找几首和它风格相近、但是节奏更快的歌。”
- “我最近听的歌有什么共同特征？”
- “这首歌和另一首歌最大的区别是什么？”
- “推荐适合深夜听的歌。”

### 4. 项目核心能力

- 音乐结构化数据管理（歌曲、歌手、音乐特征）
- 音乐特征分析（BPM / Key / Energy / Valence / Danceability / Loudness / 乐器 / 结构）
- Agent 多轮对话 + 上下文与记忆
- Function Calling / Tool Use（工具注册中心 + 白名单 + 参数校验 + 超时 + 最大轮数）
- 音乐搜索 / 筛选
- 相似歌曲检索（结构化特征 + pgvector 向量）
- 用户听歌数据分析（口味画像）
- 内容推荐 + 热门兜底 + 可解释推荐
- RAG / 向量检索（音乐知识问答）
- SSE 流式输出
- 多人在线（session 隔离 → JWT 用户体系）

### 5. 产品定位边界

音乐库、播放器、收藏、歌单、播放历史等功能**存在但不是技术核心**，它们给 AI Agent 提供真实的音乐产品场景。

> **最终目标：让音乐 UI 服务于 Agent，而不是让 Agent 服务于音乐播放器。**

---

## 二、技术栈（按《AI项目技术栈.md》要求）

技术栈按完成优先级分层：**基础必做**保证项目能运行，**基本完成度**形成业务闭环，**进阶**拉开差异，**困难项**不作为秋招前硬目标。

### 1. 基础必做：项目能运行

| 技术/能力 | 作用 | 难度 | 完成标准 |
|---|---|---:|---|
| Vue 3 + Vite + TypeScript | 音乐库、歌单、播放、Agent 页面 | 低 | 页面可访问、组件可复用 |
| Vue Router + Pinia | 路由、登录状态、播放器与 Agent 状态 | 低 | 登录后页面和状态正常切换 |
| FastAPI + Pydantic v2 | 业务 API 与参数校验 | 低-中 | API 文档可用，错误响应统一 |
| SQLAlchemy 2.0 + psycopg | ORM 与 PostgreSQL 数据访问 | 中 | 核心表可迁移、增删改查可用 |
| PostgreSQL + pgvector | 用户、歌曲、歌单、收藏、播放记录、向量 | 中 | 数据关系和索引设计清晰 |
| JWT + 基础权限 | 登录认证和管理员接口保护 | 中 | 未登录返回 401，用户不能修改他人数据 |
| HTML5 Audio | 播放合法外部音频链接 | 低-中 | 播放、暂停、进度、音量和切歌正常 |
| Jamendo 数据导入脚本 | 获取并清洗可播放音乐元数据 | 中 | 可重复执行且不产生重复数据 |

### 2. 基本完成度：形成可展示闭环

| 技术/能力 | 作用 | 难度 | 完成标准 |
|---|---|---:|---|
| 搜索和筛选 | 按歌名、歌手、风格、语言、标签找歌 | 低-中 | 支持分页、空结果和组合条件 |
| 歌单、收藏和播放记录 | 构成真实音乐业务流程 | 中 | 用户数据隔离，操作可追踪 |
| 内容推荐 + 热门兜底 | 冷启动也有稳定结果 | 中 | 新用户和老用户都有结果 |
| 推荐解释 | 展示命中的标签、偏好和依据 | 中 | 理由来自真实结构化数据 |
| SSE 流式输出 | 流式返回 AI 回复 | 中 | 前端能处理开始、内容、结束和错误事件 |
| Function Calling | 让 AI 调用搜索、分析、推荐工具 | 中-高 | 工具白名单、参数校验、超时和最大调用轮数齐全 |
| Agent 多轮对话 | Agent 与用户自然语言对话 | 中-高 | 上下文管理 + 会话记忆可用 |
| Docker Compose | 一键运行前端、后端和数据库 | 中 | 新环境可按 README 启动 |
| 基础测试 | 验证认证、权限、推荐和关键 API | 中 | 至少覆盖核心成功和失败路径 |

### 3. 困难项：秋招前不建议作为硬目标

| 技术/能力 | 不推荐作为硬目标的原因 |
|---|---|
| 复杂深度学习推荐模型 | 需要更多真实行为数据，难以证明效果优于简单基线 |
| 实时在线训练和实时特征平台 | 工程规模与当前项目不匹配 |
| 全自动 Agent 自主规划 | 难测试、难控制，容易变成模型演示而非业务能力 |
| 大规模混合召回和重排 | 需要数据量、离线评测和服务化基础 |
| Kubernetes | 服务少，增加运维成本但没有实际收益 |
| WebSocket | AI 单向流式输出用 SSE 已够用 |
| 多模型路由和本地大模型 | 与业务目标无关，增加部署与调试成本 |

### 4. 进阶扩展：基本完成后再做

| 技术/能力 | 作用 | 难度 | 进阶价值 |
|---|---|---:|---|
| pgvector 相似度检索 | 歌曲 / 知识文档向量检索 | 中-高 | 展示向量检索和统一数据存储 |
| 协同过滤 | 利用相似用户或歌曲行为推荐 | 中-高 | 用于离线对比，不作为冷启动主路径 |
| 推荐评测 | 比较热门、内容、协同过滤效果 | 中 | 有评测基线，面试能讲清收益 |
| ECharts 数据可视化 | 音乐特征 / 听歌数据看板 | 中 | 数据产品观感，体现音乐数据分析 |
| 滚动歌词（LRC） | 歌词逐行高亮同步 | 中 | 播放体验完整 |
| RAG 音乐知识问答 | 基于知识库回答歌手 / 风格问题 | 中-高 | AI 岗硬技能 |
| GitHub Actions + Docker | 构建镜像推 GHCR，服务器 pull 部署 | 中 | 工程能力完整 |

### 5. 实际技术栈版本（已从项目文件确认）

| 层 | 技术 | 版本 / 说明 |
|---|---|---|
| 后端 | FastAPI | `fastapi==0.139.2`（`backend/pyproject.toml`） |
| 后端 | SQLAlchemy | `sqlalchemy==2.0.46`（Mapped / mapped_column 写法） |
| 后端 | Alembic | `alembic==1.19.1` |
| 后端 | PostgreSQL 驱动 | `psycopg[binary]>=3.2` |
| 后端 | 向量扩展 | `pgvector>=0.3.6`（歌曲 / 知识向量字段与检索已接入，批量向量化待做） |
| 后端 | 认证 | `PyJWT==2.13.0` + `pwdlib[argon2]==0.3.1`（双 Token + Argon2id） |
| 后端 | 配置 | `pydantic-settings==2.13.1` + `python-dotenv==1.2.2` |
| AI | 大模型 | DeepSeek API（基于现有 `httpx` 直连 OpenAI-compatible Chat Completions，无额外 SDK） |
| 前端 | Vue | Vue 3 + Vite + TypeScript + Element Plus + Pinia + vue-router + axios + ESLint + Prettier（`frontend/package.json`） |
| 质量 | 工具 | `ruff==0.6.9` + `mypy==1.10.1` + `pytest==9.0.2` + pre-commit |
| 部署 | 编排 | Docker + Nginx（待做） |

> 新增任何后端依赖必须先改 `backend/pyproject.toml` 并说明原因，禁止编造不存在的依赖 / API。

---

## 三、数据库设计

### 1. 现有表（✅ 已完成；迁移见 `backend/migrations/versions/`）

| 表 | 关键字段 | 说明 |
|---|---|---|
| `users` | id, username, password_hash, role, status, created_at | 用户 + RBAC（user/admin + active/disabled） |
| `refresh_sessions` | id, user_id, token_hash, expires_at | Refresh Token 会话（SHA-256 摘要） |
| `artists` | id, name, avatar_url, source, source_id | 歌手；外部来源组合键用于幂等导入 |
| `songs` | id, title, artist_id, album, genre, language, duration, audio_url, lyrics, popularity, bpm, music_key, energy, valence, danceability, loudness, instruments, song_structure, embedding, source, source_id | 歌曲元数据 + 音乐特征 + 可选向量 |
| `playlists` | id, user_id, name, description, created_at | 歌单 |
| `playlist_songs` | playlist_id, song_id, position | 歌单-歌曲多对多 |
| `tags` | id, name | 标签 |
| `song_tags` | song_id, tag_id | 歌曲-标签多对多 |
| `play_records` | id, user_id, song_id, played_at | 播放记录 |

### 2. 向量相关表 / 字段

| 表 / 字段 | 关键字段 | 说明 |
|---|---|---|
| `songs.embedding vector(n)` | 歌曲特征向量 | 相似歌曲检索（pgvector）；维度由 Embedding 服务配置 |
| `chat_sessions` | id, user_id, created_at | Agent 多轮对话会话（已迁移） |
| `chat_messages` | id, session_id, role, content, created_at | Agent 消息历史（已迁移） |
| `music_knowledge` | id, content, source, embedding | RAG 音乐知识库（表已迁移，向量导入待做） |

### 3. Song 数据结构（《Music_Agent_项目开发书》第十五章 + 实际 model）

```text
Song
├── title / artist / album
├── genre / language / duration
├── bpm / key / energy / valence / danceability / loudness
├── instruments / structure
├── audio_url / lyrics
└── embedding（可选，迁移已完成）
```

> 数据库当前迁移版本：`20260831_10`（会话、知识库、歌曲向量、目录来源幂等标识和数据导入任务表已应用）；全新环境先执行 `cd backend && alembic upgrade head`。
> 大部分歌曲不需要实际音频，只有少量具有明确合法授权的音频用于播放器 Demo 与音频分析演示。

### 4. 向量检索（pgvector）

- `songs.embedding`：歌曲特征向量，用于“找相似歌曲”（结构化特征 + 向量余弦相似度结合）。
- `music_knowledge.embedding`：音乐知识库切片向量，用于 RAG 问答。
- 原则：先用离线评测证明收益，再决定是否作为核心卖点。

---

## 四、核心 Agent Tools（第一阶段只做 5 个）

| Tool | 用途 | 输入 → 返回 |
|---|---|---|
| `search_songs` | 歌曲 / 歌手搜索、Genre / 标签筛选 | 关键词、genre、tags → 歌曲列表 |
| `analyze_song` | 音乐数据分析 | 歌曲 ID → BPM、Key、Energy、Valence、Danceability、Loudness、Genre、Instruments、Structure |
| `find_similar_songs` | 相似歌曲检索 | 歌曲 ID → 向量优先，结构化特征兜底 |
| `analyze_user_taste` | 用户音乐分析 | 用户 → 最近播放、收藏、Genre / BPM / Energy 偏好 |
| `search_music_knowledge` | 音乐知识检索（RAG） | 问题 → 音乐理论、术语、乐器、Genre 特征 |

> 第一阶段不做几十个 Tool，先把核心 Tool 做好；工具全部为**只读**，禁止让模型直接生成 SQL 或操作数据库。

---

## 五、Agent 工作流程

```text
用户
  ↓
自然语言提问
  ↓
Agent Router（判断用户真实意图）
  ↓
是否需要调用 Tool？
  ↙           ↘
否             是
↓              ↓
直接回答     选择 Tool → 参数生成 → 后端执行 → 返回结构化数据
  ↓                    ↓
  └────── Agent 综合推理 ┘
                ↓
          SSE 流式输出
                ↓
              用户
```

### Function Calling 循环要点

1. 用户提问 → 后端把消息 + 工具定义清单发给大模型。
2. 大模型返回工具调用 → 校验参数 → 执行工具（service / repository）→ 回喂结果。
3. Agent 综合工具结果推理 → SSE 流式返回最终回答。
4. **安全边界**：工具白名单、参数校验、超时、最大调用轮数、错误降级；只读工具 + 审计。

---

## 六、多人在线设计

### 第一阶段：session 隔离（先跑通 Agent）

```text
用户 A → session_A → Agent 对话
用户 B → session_B → Agent 对话
```

- 公共音乐数据统一读取。
- 用 `session_id` 隔离不同用户的 Agent 对话，不急着做完整注册系统。

### 第二阶段：JWT 用户体系

- 注册 / 登录 / JWT（复用现有双 Token 机制）。
- 用户收藏、播放历史、歌单、聊天历史、用户音乐画像、个性化 Agent。
- 用户数据严格隔离：只能读写自己的歌单 / 收藏 / 播放记录 / 对话。

---

## 七、音乐数据与音频方案（版权红线）

### 数据源

| 数据源 | 内容 | 用途 |
|---|---|---|
| Jamendo API（主库） | 音乐、授权信息、genre / language / mood 等元数据 | **先验证**授权条款、链接有效期、跨域和播放限制后作为主库 |
| Spotify 音频特征 / 元数据数据集 | 歌曲特征或元数据 | 进阶实验，不作为首版依赖 |
| 网易云元数据 | 补充主流歌元数据 | 只抓元数据，**不碰音频** |

### 播放方案

| 方案 | 做法 | 合法性 |
|---|---|---|
| 主播放：授权数据源自定义播放器 | HTML5 audio 播放外部授权链接，播放器 / UI 全自己写 | 按数据源授权条款使用，不下载、不托管音频 |
| 滚动歌词 | Jamendo 带 CC 授权歌词；LRC 解析逐行高亮（无音频用模拟播放） | 歌词只展示、不进 Git 仓库 |
| 演示点缀：官方外链 iframe | 页面放一两个官方外链播放器 | 用官方分享功能，不自行托管 |

### 版权原则

- 不因为“免费”就默认可以在线播放；每个实际播放音频都核验 License。
- 保存来源、作者、许可证信息；不自行抓取或托管未经授权的商业歌曲。
- 歌词是文字作品，只展示、不提供下载、不进 Git 仓库；**音频是版权作品，绝不下载托管**。
- 使用第三方平台歌曲时，优先使用其官方提供的分享 / 嵌入方式。
- GitHub 仓库只放代码，数据在服务器 PostgreSQL 由导入脚本生成。

---

## 八、UI / UX 方向

- 整体风格：**现代 AI 产品 + 音乐产品 + 数据分析 Dashboard**（不是复刻网易云）。深色为主、大面积留白、卡片化、轻量渐变、圆角、微弱玻璃拟态、数据可视化、AI 对话感。
- 布局：经典三段式（顶部导航 + 左侧导航 + 主区域 + 全局底部播放器）。
- **AI Agent 主界面（最重要页面）**：Hero 区“和你的音乐 Agent 聊聊”、快捷问题（分析这首歌 / 分析节奏 / 分析情绪 / 找相似歌曲）、Chat UI；**展示工具调用状态**（✓ 正在读取歌曲数据 / ✓ 正在分析音乐特征 / ● 正在生成回答），体现“这是 Agent 而不是普通聊天机器人”。
- **音乐库**：不只展示歌名 / 歌手 / 专辑，展示 BPM / Key / Energy / Valence / Genre，一眼看出是音乐数据分析产品。
- **歌曲详情页**：形成“播放器 → 音乐数据 → 数据可视化 → AI 分析 → Agent 对话”完整闭环。
- **全局播放器**：播放 / 暂停、上一首 / 下一首、进度、音量、收藏、当前歌曲；保持简洁，不是项目核心。
- **个人区域**：收藏、最近播放、歌单；后续加个人音乐画像（常听 Genre、平均 BPM、平均 Energy），可交给 Agent 分析。

---

## 九、分阶段开发步骤与流程（核心）

> 原则：**先规划再写**（新功能先在 `docs/` 写方案）、**小步提交**、关键模块带测试、禁止硬编码、版权合规。
> 状态标记：✅ 已完成 / 🔶 部分完成 / ⬜ 未开始。

### 阶段 0：环境搭建 ✅ 已完成
- **目标**：本地能启动 FastAPI 骨架。
- **任务**：✅ 全部完成（Python venv、`pip install -e ".[dev]"`、PostgreSQL、`.env`、pre-commit）。
- **验收**：✅ `/health` 200；pre-commit 生效。

### 阶段 1：数据库建模 ✅ 已完成
- **目标**：核心表建好，能连库。
- **任务**：✅ 全部完成（SQLAlchemy 2.0 models + Alembic 迁移，见 `backend/migrations/versions/`）。
- **验收**：✅ `alembic upgrade head` 成功；`backend/tests/test_models.py`、`test_database.py` 通过。

### 阶段 2：后端基础功能 ✅ 已完成
- **目标**：业务 API 齐全，分层正确。
- **任务**：✅ 全部完成
  - 双 Token 认证（Access 1h + Refresh 3d，SHA-256 摘要，Argon2id 密码哈希）
  - RBAC（user/admin 角色 + active/disabled 状态 + 实时鉴权）
  - 管理员独立登录入口 + 管理员歌曲 / 歌手管理接口
  - 歌曲 / 歌手目录 CRUD + 搜索筛选（分页、组合条件）
  - 用户歌单、歌单歌曲、收藏接口与用户数据隔离
- **验收**：✅ pytest 覆盖认证、权限、目录接口；分层 routes → services → repositories → models。

### 阶段 3：前端基础（Vue 3）✅ 已完成
- **目标**：前端能调后端，音乐业务页面可用。
- **已完成** ✅
  - Vite + Vue 3 + TypeScript + Element Plus + Pinia + vue-router
  - axios 封装 + 登录态（Token 自动注入 + 401 刷新重放）
  - 登录 / 注册页面、路由守卫
  - 音乐库列表、歌曲详情、搜索、歌单、歌单详情、收藏、首页、全局播放器组件
- **待完成** ⬜
  - 播放器真实音频联动（产品体验阶段继续增强）
  - ECharts 听歌数据看板（歌曲详情页基础特征雷达图已完成）
- **验收**：前后端联调通过；登录后页面和播放状态正常切换。

### 阶段 4：数据管道（Jamendo）🔶 代码链路已完成，等待真实凭证验收
- **目标**：库里真有几万条歌。
- **任务**
  - [x] `backend/scripts/import_jamendo.py`：分页抓取 + 清洗（去重 / 字段映射）+ 幂等批量写入
  - [x] 管理接口触发导入（`POST /api/v1/admin/imports/jamendo`）及任务查询
  - [x] 持久化任务进度、成功/跳过/失败原因；同源任务并发保护
  - [x] 网络错误、限流和临时服务端错误的指数退避重试
  - [x] `source + source_id` 幂等更新，不产生重复歌曲或歌手
  - [x] 补充歌曲音乐特征字段（bpm / energy / valence 等）
- **产出**：先用 `--limit 100` 完成小批量验收，再扩展到全量
- **验收**：自动化测试已覆盖幂等、重试、鉴权和并发冲突；真实 100 条抓取需配置有效的 `JAMENDO_CLIENT_ID` 后执行。

### 阶段 5：推荐闭环（内容推荐 + 热门兜底 + 可解释）🔶 部分完成
- **目标**：新用户和老用户都有可解释推荐结果。
- **任务**
  - [x] `backend/app/services/recommendation_service.py`：按用户行为和风格推荐
  - [x] 热门推荐兜底（popularity 排序，冷启动路径）
  - [x] 推荐依据组装（来自真实结构化数据）
  - [x] 接口 `GET /api/v1/recommendations`
  - [ ] 标签/音乐特征相似度增强
  - [ ] 协同过滤实现 / 评测（进阶，离线对比，不作为线上主路径）
- **验收**：新用户有兜底结果；老用户推荐有变化；推荐理由可解释；pytest 覆盖。

### 阶段 6：AI Agent（Agent 对话 + SSE + Tool Registry + Function Calling）✅ 已完成
- **目标**：对话里 Agent 能调用核心工具并流式回答。
- **任务**
  - [x] DeepSeek OpenAI-compatible Provider（基于现有 `httpx`，无需新增 SDK）
  - [x] `backend/app/services/agent/`：Agent Orchestrator（模型驱动主流程）
  - [x] Tool Registry（工具注册中心）及五个只读音乐工具
  - [x] Function Calling 循环：工具定义 → 参数校验 → 执行 → 回喂 → 综合推理
  - [x] SSE 流式输出（StreamingResponse）：token 增量、工具、错误、结束事件
  - [x] 多轮上下文管理（chat_sessions / chat_messages）
  - [x] Token 预算、工具结果限长与历史上下文压缩
  - [x] Provider 超时映射、SSE 客户端取消和工具异常恢复
  - [x] 对话接口（session_id 用户隔离）
  - [x] 前端 Agent 对话页：Chat UI + 加载状态展示 + SSE 增量渲染
- **产出**：能说“推荐适合深夜听的歌”“分析这首歌为什么忧郁”，Agent 调工具返回真实结果。
- **验收**：能讲清 function calling 循环 + 安全设计；工具白名单 / 参数校验 / 超时 / 最大轮数齐全；pytest 覆盖。

### 阶段 7：RAG + 向量检索（pgvector）🔶 基础闭环完成，进阶评测待做
- **目标**：相似歌曲 + 音乐知识问答。
- **任务**
  - [x] 新增 `songs.embedding` 可选字段迁移；模型维度随 Embedding 服务配置
  - [x] Embedding Provider 抽象和 OpenAI-compatible `/embeddings` 客户端
  - [x] pgvector 余弦检索编排；无向量或服务不可用时回退结构化 / 文本检索
  - [x] 检索阈值和 `relevant` 标记，提示模型在无关时不要硬答
  - [x] 批量歌曲 / 知识切片向量化与幂等写入（`scripts.embed_catalog`）
  - [ ] 检索质量评测、重排和线上 RAG 效果验收
- **验收**：问“City Pop 是什么”AI 基于知识库回答；相似歌曲结果合理；能讲清检索流程。

### 阶段 8：产品体验（可视化 + 播放 + 歌词 + 画像）🔶 基础播放与歌词完成
- **目标**：体验完整，数据产品感强。
- **任务**
  - [ ] ECharts 听歌数据看板（总时长 / TOP 歌手风格 / 时段分布 / 月度趋势）
  - [x] 歌曲详情页音乐特征可视化（雷达图 / 柱状图）
  - [x] HTML5 播放器与阶段 4 音频联动
  - [x] LRC 歌词解析 + 逐行高亮同步（无音频用模拟播放）
  - [ ] 个人音乐画像（常听 Genre / 平均 BPM / 平均 Energy）
- **验收**：演示流畅；能听歌、看歌词、看统计、看画像。

### 阶段 9：多人在线与部署（JWT + Docker + CI/CD）🔶 部署骨架已完成
- **目标**：多用户完整 + 一键部署。
- **任务**
  - [x] 用户系统完善：注册 / 登录 / JWT 完整（复用现有双 Token）、用户数据隔离
  - [x] 收藏、播放历史、歌单、聊天历史的用户级绑定
  - [x] 后端 Dockerfile + 前端 Dockerfile + Nginx 配置
  - [x] `docker-compose.yml`（后端 + 前端 + PostgreSQL）
  - [x] 生产环境变量示例、数据库持久化 volume、容器健康检查和自动迁移
  - [ ] GitHub Actions：构建镜像 → 推 GHCR → 服务器 pull 部署（Secrets 存敏感信息）
- **产出**：服务器 `docker compose up -d` 一键起，公网 IP 可访问。
- **验收**：多用户数据隔离正确；新环境按 README 可启动。

---

## 十、开发顺序与时间线建议

> 阶段 0-3 可并行 / 穿插；阶段 4（数据管道）和阶段 5-7 互相独立，数据到了推荐 / AI 才有真实效果。

**建议顺序**：`0 → 1 → 2 → 3 → 5（推荐，用种子数据跑通）→ 6（AI Agent）→ 4（灌真实数据）→ 7 → 8 → 9`

**里程碑**：
- M1（骨架跑通）：阶段 0-1 ✅
- M2（基础可用）：阶段 2-3 🔶 基本完成
- M3（AI 有亮点）：阶段 5-6 🔶（推荐与 Agent 基础闭环已跑通）
- M4（完整 + 上线）：阶段 7-9 ⬜

---

## 十一、开发规范与质量门禁（L1 必须）

- **分层**：routes 只负责参数校验和调用 service；repositories 只做数据访问；services 承载业务逻辑、推荐与 AI 编排。
- **类型注解**：覆盖公共接口和核心业务边界；可选类型用 `int | None`，模块用 `from __future__ import annotations`。
- **现代写法**：SQLAlchemy 2.0 `Mapped` / `mapped_column`；Pydantic v2。
- **依赖管理**：新增后端依赖必须在 `backend/pyproject.toml` 声明并说明原因（如 DeepSeek SDK）。
- **测试**：推荐引擎、function calling、数据管道等关键模块必须有 pytest；交付前运行 ruff、mypy、pytest 并报告。
- **前端门禁**：ESLint + Prettier（`npm run lint:check` / `npm run format:check`）+ vue-tsc（`npm run typecheck`）；已接入 pre-commit，提交时自动检查前端代码。
- **安全**：密钥 / URL 走 `.env` / settings，禁止写入源码或 Git。
- **版权**：只使用合法授权数据源；歌词只展示且不进 Git；音频不得下载或托管版权作品。
- **Git**：代码进 GitHub，数据不进；`.env` 不进 Git；小步、单一目的提交。

---

## 十二、面试准备清单（每个阶段完成后要能答）

- **推荐系统**：整体设计？几条路径？冷启动？评测？多样性？
- **function calling / AI 编排**：循环流程？工具定义？参数错误？超时 / 轮数？安全边界？为什么不用直接 SQL？
- **向量检索 + RAG**：embedding 原理？为什么 pgvector？切片？检索不相关怎么办？幻觉怎么降？
- **数据管道**：1 万条怎么导？清洗？去重？字段映射？幂等？批量？
- **多用户 / 架构 / 安全**：多用户怎么隔离？分层？表设计？权限？为什么 FastAPI？
- **播放 / 滚动歌词**：播放器实现？音频来源？LRC 同步？版权？
- **通用项目问题**：为什么选音乐？最难的部分？最大坑？不足与改进？亮点？数据版权？

---

## 十三、简历一句话描述（Agent 版）

> 正在实现多用户 AI 音乐智能体平台：Vue 3 + FastAPI + PostgreSQL + pgvector + DeepSeek；已完成认证、音乐库 / 歌单 / 收藏、内容推荐与热门兜底，以及基于 Tool Registry + Function Calling 的 Agent 工具调用和 SSE 流式对话。向量批量生成、RAG 质量评测、Jamendo 数据管道、完整播放器与 Docker / CI/CD 部署仍在后续阶段。
