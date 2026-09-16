# 面试问答准备 —— 基于 music-agent 项目真实实现

> 本文件只服务于一个目的：让你**用自己项目里的真实代码**回答面试问题。
> 每条都标注了对应文件，面试前对照代码看一遍，就能说出细节而不是背概念。

---

## 一、项目一分钟介绍

> 一个多用户的 AI 音乐智能体平台。技术栈是 Vue 3 + FastAPI + PostgreSQL + pgvector + DeepSeek。
>
> 音乐库、歌单、收藏这些是**产品承载层**，核心是让 AI Agent 能理解音乐数据、调用业务工具、分析音乐特征，并用自然语言对话。
>
> 目前已经上线运行，有完整的 CI/CD：push 到 GitHub 后自动构建镜像并部署到服务器。

**如果被问"为什么要做音乐"**：音乐数据天然带结构化特征（BPM、调性、能量、情绪），适合做数据分析和 Agent 工具调用；而且音频版权是红线，正好能体现合规意识。

---

## 二、RAG / 向量检索（最高频，必须答好）

对应代码：`backend/app/services/rag_service.py`（91 行）

### Q：RAG 是什么？你项目里怎么实现的？

**RAG = 先检索资料，再让模型基于资料回答**，解决模型"不知道你私有数据"和"瞎编"的问题。

我的实现在 `rag_service.py`，流程是**向量优先、文本兜底**：

1. 用户问题 → 调 embedding 服务转成向量
2. 用 pgvector 在 `music_knowledge` 表做余弦相似度检索
3. 用**阈值**过滤掉不相关的（`embedding_similarity_threshold`）
4. 把命中的资料连同问题一起喂给模型
5. 检索不到时用 `relevant: false` 标记，**提示模型不要硬答**

### Q：为什么用 pgvector 而不是专门的向量数据库？

因为**业务数据和向量可以放在同一个 PostgreSQL 里**，不引入额外中间件（不用再部署维护一套 Milvus/Chroma）。我的数据量是千级，pgvector 完全够用，架构上也更简单。

### Q：相似度怎么算的？

用**余弦距离**，然后转成相似度：

```python
"similarity": round(max(0.0, min(1.0, 1 - distance)), 4)
```

`1 - distance` 把距离转成相似度，再用 `max/min` 裁剪到 0~1 区间，避免浮点误差导致越界。

### Q：怎么降低幻觉？

两个手段：
1. **相似度阈值**过滤——低于阈值的不返回
2. **`relevant` 标记**——检索为空时明确告诉模型"没找到相关资料"，让它说"我不知道"而不是编造

```python
return {"items": [], "count": 0, "relevant": False, "mode": mode}
```

### Q：如果 embedding 服务挂了/没配置怎么办？

**降级到关键词检索**，保证功能不中断：

```python
if self.embedding_provider is not None and self.embedding_provider.is_configured:
    vector_result = self._search_vector(...)
    if vector_result is not None and vector_result["items"]:
        return vector_result
return self._search_lexical(normalized_query, limit)
```

**这个降级我实测对比过**：同一个知识库，关键词模式问"这是什么流派"完全找不到（因为库里内容里没有"流派"这两个字），而向量模式能正确命中。这正好说明**语义检索的价值**。

### Q：向量查询失败了会不会污染主事务？

不会。我用了**保存点**（savepoint）：

```python
with self.repository.db.begin_nested():
    matches = self.repository.search_vector(...)
```

`begin_nested()` 开一个保存点，向量查询出错只回滚这一段，主事务可以继续走降级路径。

---

## 三、embedding / 向量是什么

对应代码：`backend/app/services/embedding_provider.py`

### Q：embedding 是什么？

把文字**翻译成一串数字**（向量），让计算机能计算"语义相似度"。意思相近的文本，向量方向也接近。

比如：
- "摇滚" → `[0.8, -0.3, 0.5, ...]`
- "重金属" → `[0.79, -0.28, 0.52, ...]`（很接近）
- "古典乐" → `[-0.5, 0.9, -0.1, ...]`（差很远）

### Q：向量怎么生成的？成本多少？

调 embedding 服务的 `/embeddings` 接口生成。我的实现是标准 OpenAI 兼容协议，**不绑定具体供应商**，换服务商只改三个环境变量：

```
EMBEDDING_API_KEY / EMBEDDING_BASE_URL / EMBEDDING_MODEL
```

成本很低：931 首歌 + 48 条知识，约 7.5 万 token。embedding 单价是对话模型的几十分之一，**一次生成永久复用**，只在新增数据时才需要增量生成。

### Q：怎么保证批量请求的可靠性？

`embedding_provider.py` 里做了几层校验：

- 按响应里的 `index` **重新排序**，保证和输入顺序一致
- 校验**返回数量**和输入数量一致
- 校验**所有向量维度一致**（防止服务端返回异常）
- 空输入直接返回 `[]`，不发请求

### Q：批量向量化怎么做幂等？

`embedding_batch_service.py` 只处理**还没有向量的记录**（`list_without_embeddings`），所以重复执行不会重复花钱。而且分批处理（默认 32 条一批），控制单次请求大小和内存。

另外 service 层只 `flush()` 不 `commit()`，**事务提交由调用边界负责**——这是项目的分层约定。

---

## 四、推荐系统与冷启动

对应代码：`backend/app/services/recommendation_service.py`

### Q：推荐系统怎么设计的？（重点：冷启动）

我设计了**三条路径**，核心是保证冷启动一定有结果：

| 用户状态 | 走哪条路径 | 返回什么 |
|---|---|---|
| 未登录游客 | 热门兜底 | `strategy="popular_fallback"` |
| 登录且有行为数据 | 内容推荐 | 按音乐特征距离匹配 |
| 登录但数据不足 | 热门兜底 | 同上 |

```python
# 游客直接热门
if user_id is None:
    popular = self.repository.list_popular(set(), limit)

# 有数据走内容推荐
profile = self.repository.feature_profile(user_id)
candidates = self.repository.list_candidates(genres, excluded_ids, limit, profile)

# 兜底
popular = self.repository.list_popular(excluded_ids, limit)
strategy = "popular_fallback"
```

### Q：为什么用热门兜底解决冷启动？

协同过滤依赖用户行为数据，新用户没有任何记录，**找不到相似用户，直接失效**。所以新用户走热门兜底——保证"一定有结果可看"，等积累行为数据后再切个性化路径。

### Q：内容推荐具体怎么算相似？

用音乐的结构化特征做距离排序：**BPM、Energy、Valence、Danceability**。用户的历史行为聚合成偏好画像（`feature_profile`），再算候选歌曲和画像的距离。

### Q：推荐结果怎么做到"可解释"？

每条推荐都带一个理由，理由**来自真实的结构化数据**，不是编造的：

```python
reason=self._content_reason(song, profile)
```

比如"匹配你常听的流行风格""节奏接近你近期的偏好"。

### Q：为什么没做协同过滤？（诚实回答，这是加分项）

因为**数据量不足**。目前只有 931 首歌，用户行为记录很少。协同过滤在数据稀疏时效果无法验证，强行上线只能得到一个不可信的结果。

所以我选择：**内容推荐 + 热门兜底作为主路径，协同过滤规划在积累真实行为数据后做离线评测对比再决定**。

（如果被追问：我准备了评测思路——用 Precision@K、NDCG 等指标离线对比热门/内容/协同过滤三条路径。）

---

## 五、AI Agent / Function Calling

对应代码：`backend/app/services/agent/`（orchestrator、provider、registry、music_tools）

### Q：Function Calling 循环怎么走的？

1. 把用户消息 + **工具定义清单**发给模型
2. 模型返回工具调用意图
3. **校验参数** → 执行工具 → 把结构化结果回喂给模型
4. 模型综合结果推理，**SSE 流式**返回最终回答

### Q：工具是怎么注册和管控的？

用 **Tool Registry** 统一注册，每个工具带名称、中文描述、JSON Schema 参数定义和执行函数。目前有 5 个核心只读工具：

| 工具 | 用途 |
|---|---|
| `search_songs` | 搜索歌曲/歌手，按风格标签筛选 |
| `analyze_song` | 分析音乐特征（BPM/调性/能量/情绪等） |
| `find_similar_songs` | 相似歌曲检索（向量优先，结构化兜底） |
| `analyze_user_taste` | 分析用户听歌偏好 |
| `search_music_knowledge` | RAG 音乐知识检索 |

**工具全部是只读的**，禁止让模型直接生成 SQL 或操作数据库。

### Q：安全边界怎么做的？（面试官很爱问）

多层防护：

1. **工具白名单**——只注册允许的工具，模型无法调用未注册的能力
2. **参数校验**——每个工具有 Pydantic Schema，调用前校验
3. **超时控制**——`agent_tool_timeout_seconds`
4. **最大轮数**——`agent_max_tool_rounds` 防死循环
5. **无进展检测**——`agent_no_progress_limit`：连续出现**完全相同的工具调用**就判定模型在原地打转，主动终止
6. **总时间预算**——`agent_total_timeout_seconds`，耗尽后走兜底收尾而不是报错
7. **高风险操作需用户确认**——写操作（如创建歌单）会返回 `confirmation_required` 事件，等用户批准，且有 `agent_confirmation_ttl_seconds` 有效期

### Q：为什么要做"无进展检测"？

因为模型有时会**反复调用同一个工具、传同样的参数**，陷入死循环。我统计连续完全相同的调用次数，达到阈值（默认 2 次）就判定卡住并终止。这比单纯限制轮数更精准——正常的多步推理不会被误杀。

### Q：Token 预算怎么控制的？

- `agent_context_token_budget`（12000）——上下文预算
- `agent_response_token_budget`（2000）——单次回答预算
- `agent_tool_result_max_chars`（12000）——工具结果限长

工具返回的内容可能很长，超过限制会截断，避免把上下文撑爆。

### Q：为什么用 SSE 而不是 WebSocket？

因为**AI 回答是单向流式输出**，SSE 完全够用，而且：
- 基于 HTTP，不用额外协议升级
- 自动重连
- 实现和调试都更简单

WebSocket 适合双向实时通信（聊天室、协同编辑），我这里是单向推送，属于过度设计。

---

## 六、架构与工程能力

### Q：项目怎么分层的？

```
routes      只做参数校验 + 调用 service，不写业务逻辑
services    承载业务逻辑、推荐算法、AI 编排
repositories 只做数据访问，不写业务判断
models      SQLAlchemy 2.0 的 Mapped / mapped_column
```

严格单向依赖：`routes → services → repositories → models`。

### Q：认证怎么做的？

- **双 Token**：Access Token（1 小时）+ Refresh Token（3 天）
- Refresh Token 存数据库，只存 **SHA-256 摘要**，不存明文
- 密码用 **Argon2id** 哈希
- **RBAC**：user/admin 角色 + active/disabled 状态，实时鉴权

### Q：部署怎么做的？

三个容器：PostgreSQL(pgvector) + FastAPI + Nginx（同时托管前端静态文件和反代 `/api`）。

**CI/CD 完整自动化**：
1. push 到 GitHub master 触发 Actions
2. 构建前后端镜像 → 推到镜像仓库
3. SSH 到服务器同步 compose 文件 → `docker compose pull && up -d`
4. 容器健康检查 + 自动执行数据库迁移（`alembic upgrade head`）

**服务器不需要源码**——代码在镜像里，服务器只跑镜像。这是标准的容器化部署方式。

### Q：前端 Nginx 配置有什么讲究？（能答出这条很加分）

前端是 SPA，Nginx 配置里有两个关键点：

```nginx
# 带内容哈希的构建产物：找不到就 404，绝不回退
location /assets/ {
    try_files $uri =404;
    add_header Cache-Control "public, max-age=31536000, immutable";
}

# index.html 是资源清单，必须每次验证
location = /index.html {
    add_header Cache-Control "no-cache, must-revalidate";
}

# 前端路由回退
location / {
    try_files $uri $uri/ /index.html;
}
```

---

## 七、你踩过的坑（"最大难点"的标准答案）

### SPA 部署的资源版本错配（version skew）

**这是你的王牌素材**，能讲 5-10 分钟，完整展示了排查能力。

**现象**：网站来回跳转路由 2-3 次后，整个页面完全卡死，点什么都没反应，只能滚动。

**排查过程**（重点讲这个）：

1. 先排除后端——实测接口响应正常（200，2.3 秒），数据库连接数正常，日志无错误
2. 排除网络——499/502/504 都没有异常
3. **关键线索**：日志里发现一个 `index-sj1xjws5.js` 被请求了 26 次、全部返回 200，但**服务器上根本没有这个文件**
4. 进一步实测：请求一个不存在的 JS → 返回的是 **200 + HTML**（813 字节，正是 index.html 的大小）

**根因**：两个配置问题叠加

| 问题 | 后果 |
|---|---|
| `index.html` 没设 `Cache-Control` | 浏览器按"启发式缓存"自己猜了缓存时长，期间**不问服务器**，一直用旧的资源清单 |
| Nginx 的 `try_files ... /index.html` 兜底 | 旧清单指向的文件已被新构建删除，**Nginx 却返回 HTML 而不是 404** |

**因果链**：
```
前端重新构建 → 所有 chunk 哈希变了
  ↓
浏览器用旧 index.html（旧清单）→ 去要旧文件名
  ↓
服务器上旧文件已被删除
  ↓
Nginx 不说"404"，而是返回 HTML + 200
  ↓
浏览器把 HTML 当 JS 解析 → SyntaxError
  ↓
Vue Router 的动态 import 失败，导航永久挂起
  ↓
路由切换是串行的，队列被堵死 → 完全卡死
```

**为什么"2-3 次"才死**：每次跳转要加载多个 chunk（页面 JS + CSS + 依赖），每个失败的 import 都占住一次导航，累积几次队列就堵死了。

**修复**：
1. `/assets/` 缺失文件返回 404，不兜底
2. `index.html` 设 `no-cache`
3. 前端 `router.onError` 检测到 chunk 加载失败时**自动刷新一次**（10 秒冷却防无限刷新），让已缓存旧清单的用户自动恢复

**为什么以前没遇到**：前端镜像从来没更新过，chunk 哈希不变，旧清单指向的文件一直存在，所以不会触发。

**这个坑的通用价值**：这是**SPA 部署的经典问题**，业界叫 version skew。核心认知是——**带哈希的静态资源可以永久缓存，但 `index.html` 作为"资源清单"必须永不缓存**，两者缓存策略必须配套。

---

## 八、快速自测清单

面试前对着这几个问题自问，能脱口而出就稳了：

- [ ] RAG 流程？为什么用 pgvector？
- [ ] 相似度怎么算？阈值干嘛的？
- [ ] 怎么降低幻觉？
- [ ] embedding 是什么？成本多少？
- [ ] 冷启动怎么解决？为什么不用协同过滤？
- [ ] Function Calling 循环？安全边界有哪几层？
- [ ] 为什么要"无进展检测"？
- [ ] 为什么用 SSE 不用 WebSocket？
- [ ] 项目怎么分层的？
- [ ] 认证用了什么方案？
- [ ] 你踩过最大的坑是什么？（讲 SPA 缓存那个）
- [ ] 部署流程？为什么服务器上不需要源码？

---

## 九、诚实边界（别硬撑）

面试官问到这些，直接承认"还没做"，并说明理由：

| 问题 | 应答 |
|---|---|
| 协同过滤做了吗？ | 没做。数据量不足（931 首歌、用户行为少），效果无法验证。规划在有数据后做离线评测对比。 |
| 推荐效果怎么评测的？ | 还没做正式评测。指标会选 Precision@K / NDCG，对比热门、内容、协同过滤三条路径。 |
| RAG 效果怎么评测？ | 检索链路已完成并实测过降级对比，但**检索质量的系统评测**（召回率、重排）还没做。 |
| 有做重排（rerank）吗？ | 没有。当前是单路向量检索 + 阈值过滤，重排是后续优化方向。 |
| 音轨播放情况？ | 按版权合规要求，只使用明确授权的音频，大量歌曲只有元数据用于分析。 |
