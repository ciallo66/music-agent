# 开发流程步骤文档 —— AI 音乐发现平台（music-agent）

> 本文档是项目的完整开发路线图。按阶段顺序推进，每个阶段有明确目标、任务、产出和验收标准。
> 开发规范见 `CLAUDE.md`（Claude）和 `AGENTS.md`（Codex），所有代码必须遵守。

---

## 一、项目概述

多用户 AI 音乐平台，核心能力：
- **推荐引擎**：基于内容 + 热门兜底（可解释）；协同过滤已实现（冷启动下不作为线上主路径）
- **AI 辅助**：function calling（口味分析、自然语言找歌、推荐理由、周报）
- **RAG 知识问答**：基于音乐知识库回答歌手/风格问题
- **播放 + 滚动歌词**：Jamendo 音频 + LRC 同步
- **数据管道**：Jamendo API 抓 1 万条进 PostgreSQL

## 二、技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy 2.0 + PostgreSQL + pgvector |
| AI | DeepSeek API + function calling + RAG + 向量检索 |
| 前端 | Vue 3 + Vite + Pinia + Element Plus + ECharts |
| 数据源 | Jamendo API（CC 授权）、Spotify 元数据、网易云元数据（仅展示） |
| 部署 | Docker + Nginx + GitHub Actions（CI/CD） |
| 质量 | ruff + mypy + pytest + pre-commit |

## 三、开发总原则（必须遵守）

1. **先规划再写**：新功能先在 docs/ 写方案，再动手
2. **小步提交**：一次 commit 几百行内，信息清晰
3. **关键模块带测试**：推荐引擎、function calling、数据管道必须有 pytest
4. **现代写法**：类型注解、SQLAlchemy 2.0、Pydantic v2（见 CLAUDE.md）
5. **禁止硬编码**：密钥/URL 走 .env
6. **数据版权**：只用合法数据源，音频绝不下载托管，歌词只展示不进 Git

---

## 四、数据库设计（PostgreSQL + pgvector）

### 表结构

| 表 | 关键字段 | 说明 |
|---|---|---|
| `users` | id, username, password_hash, created_at | 用户 |
| `artists` | id, name, avatar_url | 歌手 |
| `songs` | id, title, artist_id, genre, language, duration, audio_url, lyrics, popularity | 歌曲（Jamendo 数据） |
| `playlists` | id, user_id, name, description, created_at | 歌单 |
| `playlist_songs` | playlist_id, song_id, position | 歌单-歌曲关联 |
| `tags` | id, name | 标签 |
| `song_tags` | song_id, tag_id | 歌曲-标签关联 |
| `play_records` | id, user_id, song_id, played_at | 播放记录 |

### 向量（pgvector）

- `songs.embedding vector(n)`：歌曲特征向量（风格/语言/标签 → embedding），用于相似歌曲检索
- `knowledge_chunks` 表：音乐知识库切片 + embedding，用于 RAG

---

## 五、分阶段开发计划

### 阶段 0：环境搭建
- **目标**：本地能启动 FastAPI 骨架
- **任务**：
  1. Python 3.10+ 创建 venv，`pip install -e ".[dev]"`
  2. 安装 PostgreSQL + pgvector（见 `docs/pgvector-install.md`）
  3. 复制 `.env.example` 为 `.env`，填数据库/DeepSeek/Jamendo 配置
  4. `pre-commit install`
- **产出**：进入 `backend/` 后执行 `uvicorn app.main:app --reload` 能启动，`/health` 返回 ok
- **验收**：`/health` 200；pre-commit 生效

### 阶段 1：数据库建模
- **目标**：表结构建好，能连库
- **任务**：
  1. 写 SQLAlchemy 2.0 models（users/artists/songs/playlists/tags/play_records）
  2. 配置 alembic 迁移
  3. 建库：`CREATE DATABASE music_agent;`
  4. `CREATE EXTENSION vector;`
- **产出**：进入 `backend/` 后执行 `alembic upgrade head` 建表成功
- **验收**：psql 里能看到所有表；pytest 空跑通过

### 阶段 2：基础功能（后端 API）
- **目标**：业务 API 齐全
- **任务**：
  1. 多用户认证：注册/登录/JWT/权限
  2. 歌曲/歌手 CRUD（增删改查）
  3. 歌单 CRUD + 加歌/移歌
  4. 收藏、标签
  5. 播放记录
  6. 搜索筛选（歌手/歌名/风格/语言/标签）
- **产出**：完整 REST API，postman 可调通
- **验收**：接口有 pytest 测试；分层正确（routes→services→repositories→models）

### 阶段 3：前端基础（Vue 3）
- **目标**：前端能调后端
- **任务**：
  1. Vite 创建 Vue 3 项目（frontend/）
  2. 接入 Element Plus + Pinia + Router
  3. 页面：登录/注册、音乐库列表、歌曲详情、歌单、搜索
  4. axios 封装 + 登录态
- **产出**：前端能登录、浏览音乐库、建歌单
- **验收**：前后端联调通过

### 阶段 4：数据管道（Jamendo）
- **目标**：库里真有几万条歌
- **任务**：
  1. developer.jamendo.com 免费申请 Client ID
  2. `backend/scripts/import_jamendo.py`：分页抓取 + 清洗（去重/字段映射）+ 批量写入
  3. 抓取 1 万条（含 genre/语言/音频链接/歌词）
- **产出**：`SELECT count(*) FROM songs;` 返回 10000+
- **验收**：导入脚本幂等（重复跑不产生重复数据）；带歌词的能查

### 阶段 5：推荐引擎
- **目标**：能推荐 + 能讲
- **任务**：
  1. 基于内容：歌曲特征向量（风格/语言/标签）→ 余弦相似度（**线上主路径**）
  2. 协同过滤：用户-物品矩阵 → 相似用户/物品（**已实现**，配脚本生成的模拟播放数据可跑评测；真实用户行为稀疏，不作为线上主路径）
  3. 混合推荐：内容相似 + 向量检索 + 热门兜底（冷启动）加权融合，每次推荐带可解释理由
  4. 评测：准召/准确率基线对比（基于内容 vs 热门 vs 混合）
- **产出**：推荐接口 `GET /api/v1/recommendations`
- **验收**：新用户冷启动有推荐（热门兜底）；老用户推荐有变化；能讲清算法 + 评测 + 为什么 CF 不上线

### 阶段 6：AI 辅助（function calling）
- **目标**：对话里 AI 能调工具
- **任务**：
  1. 工具注册中心（Tool Registry）
  2. function calling 循环（DeepSeek）
  3. 工具：search_song / recommend / analyze_taste / generate_playlist
  4. 流式输出（SSE）
- **产出**：对话界面能说"推荐适合深夜听的歌"，AI 调工具返回真实结果
- **验收**：能讲清循环 + 安全设计；多轮对话可用

### 阶段 7：RAG + 向量检索
- **目标**：知识问答 + 相似歌曲
- **任务**：
  1. 歌曲 embedding 存入 pgvector（songs.embedding）
  2. 相似歌曲接口（向量余弦相似度）
  3. 音乐知识库（歌手/风格资料）切片 + embedding + 检索 → RAG 问答
- **产出**：问"City Pop 是什么"AI 基于知识库回答
- **验收**：能讲清检索流程 + 幻觉处理

### 阶段 8：看板 + 播放 + 滚动歌词
- **目标**：体验完整
- **任务**：
  1. ECharts 听歌数据看板（总时长/TOP/时段/趋势）
  2. 自定义 HTML5 播放器（Jamendo 音频）
  3. LRC 歌词解析 + 逐行高亮同步
- **产出**：页面能听歌、看歌词滚动、看统计
- **验收**：演示流畅；能讲歌词同步原理

### 阶段 9：Docker 部署 + CI/CD
- **目标**：一键部署到服务器
- **任务**：
  1. 后端 Dockerfile + 前端 Dockerfile + Nginx 配置
  2. docker-compose.yml（后端+前端+PostgreSQL）
  3. GitHub Actions：构建镜像 → 推 GHCR → 服务器 pull
  4. 服务器首次跑 import 脚本灌数据
- **产出**：服务器 `docker compose up -d` 一键起
- **验收**：公网 IP 能访问；面试能讲 CI/CD 全流程

### 阶段 10：简历 + 面试准备
- **目标**：能讲透整个项目
- **任务**：
  1. 简历写项目描述（见下）
  2. 对照面试问题清单逐个自测（见 docs/interview-questions.md）
- **产出**：每个核心模块能不看任何东西讲 3 分钟

---

## 六、简历描述（写完可直接用）

> 设计并实现了多用户 AI 音乐发现平台：FastAPI + PostgreSQL + pgvector + Vue 3 + DeepSeek，构建了可解释的混合推荐系统（内容相似 + 向量检索 + 热门兜底），通过 function calling 让 LLM 自主完成口味分析、自然语言找歌与歌单生成；接入 Jamendo 等 CC 授权数据源，支持 1 万+ 首音乐播放、滚动歌词与多维度筛选；GitHub Actions + Docker 自动化部署。

## 七、面试准备清单（每个阶段完成后要能答）

- 推荐系统：为什么混合？冷启动？评测？
- function calling：循环流程？安全？错误处理？
- RAG/向量：为什么 pgvector？检索质量？幻觉？
- 数据管道：1 万条怎么导的？清洗？幂等？
- 版权：数据源合法性？歌词/音频边界？
- 部署：Docker 镜像？CI/CD 流程？Secrets？

（完整问题清单见 `docs/interview-questions.md`）

---

## 八、时间线建议（相对顺序）

> 阶段 0-3 可并行/穿插；阶段 4（数据管道）和阶段 5-7 互相独立，数据到了推荐才有真实效果。
> 建议：0→1→2→3→5（推荐，用种子数据跑通）→6（AI）→4（灌真实数据）→7→8→9。

**里程碑**：
- M1（骨架跑通）：阶段 0-1
- M2（基础可用）：阶段 2-3
- M3（AI 有亮点）：阶段 5-6
- M4（完整 + 上线）：阶段 7-9
