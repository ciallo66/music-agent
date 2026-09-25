"""音乐知识库数据访问。"""

from __future__ import annotations

import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.music_knowledge import MusicKnowledge

# 中文没有空格，按空白切词会把整句当成一个词，导致 "什么是萨克斯" 匹配不到 "萨克斯"。
# 兜底检索因此改用「中文 n-gram」：先试长片段（精确），命中不足再放宽到二字片段（高召回）。
NGRAM_SIZES: tuple[int, ...] = (4, 3, 2)
MAX_TERMS = 24

# 兜底检索里必须过滤掉的高频通用片段。
# 只按单个汉字过滤（"电"/"影"这类）远远不够：实测"推荐几部好看的电影"
# 仍会因 "电影""推荐" 这类二字词匹配到音乐条目。常见问句词与技术词一律排除。
STOP_FRAGMENTS: frozenset[str] = frozenset(
    {
        # 问句壳
        "什么",
        "怎么",
        "如何",
        "为什",
        "哪些",
        "介绍",
        "解释",
        "说说",
        "告诉",
        "请问",
        "可以",
        "能不能",
        "有没有",
        "是否",
        "推荐",
        "建议",
        "帮我",
        "我想",
        "我要",
        # 通用名词（与音乐知识库无关的领域）
        "电影",
        "天气",
        "股票",
        "信用",
        "高铁",
        "红烧",
        "排序",
        "算法",
        "编程",
        "代码",
        "量子",
        "纠缠",
        "开户",
        "申请",
        "好看",
        "几部",
        "等于",
        "多少",
        # 通用连接与助词
        "的是",
        "和",
        "与",
        "及",
        "在",
        "里",
        "了",
        "吗",
        "呢",
        "吧",
        "的区",
        "区别",
    }
)


# 打分：片段越长越可信；2 字片段单独命中（如"电影"）不足以算作相关内容。
TERM_WEIGHTS: dict[int, int] = {2: 3, 3: 6, 4: 8}
MIN_MATCH_SCORE = 6
# 片段在整个知识库里出现得越普遍，越像噪声（"电影""推荐"这类通用词会命中很多条目）。
# 注意分母是**全量条目数**，不是粗召回结果数，否则每个片段都是"100% 命中"。
NOISE_TERM_RATIO = 0.3


def _term_weight(term: str) -> int:
    """按片段长度给匹配质量打分。"""
    if term.isascii():
        return 8
    return TERM_WEIGHTS.get(len(term), 8)


# 长句查询不再补充 2 字片段：2 字片段太泛（"电影""推荐"这类会误命中），
# 而 3/4 字片段对长句已经足够精确。短查询（如"什么是萨克斯"）仍保留 2 字片段保证召回。
SHORT_QUERY_CHARS = 6


def build_terms(query: str) -> list[str]:
    """把查询切成可用于 ILIKE 的检索片段。

    规则：
    - 英文/数字按空白与标点切词（保持原有行为）；
    - 连续中文按 n-gram 切分：长句用 4/3 字片段（精确），短查询额外补 2 字片段（高召回）；
    - 过滤纯标点、纯空白与高频通用片段（见 `STOP_FRAGMENTS`）。
    """
    terms: list[str] = []
    for token in re.split(r"[\s,，。、；;：:!！?？()（）\[\]【】\"'“”‘’]+", query.strip()):
        if not token:
            continue
        if re.fullmatch(r"[A-Za-z0-9+#._-]+", token):
            terms.append(token.lower())
            continue
        sizes = NGRAM_SIZES if len(token) <= SHORT_QUERY_CHARS else (4, 3, 2)
        for size in sizes:
            for start in range(0, max(1, len(token) - size + 1)):
                fragment = token[start : start + size]
                if len(fragment) != size or fragment in terms:
                    continue
                if fragment in STOP_FRAGMENTS:
                    continue
                terms.append(fragment)
    return terms[:MAX_TERMS]


class MusicKnowledgeRepository:
    """封装音乐知识切片的只读检索。"""

    def __init__(self, db: Session) -> None:
        """绑定知识库查询使用的数据库会话。"""
        self.db = db

    def search(self, query: str, limit: int) -> tuple[list[MusicKnowledge], list[str]]:
        """按关键词检索，返回（命中条目, 实际用于匹配的片段）。

        两段式：n-gram 片段先做粗召回，再按「匹配片段长度」打分排序并过滤。
        过滤规则解决了两个互相矛盾的现实需求：
        - "什么是萨克斯" → 命中的是 3 字片段"萨克斯"（得分高）→ 保留；
        - "贝斯在乐队里起什么作用" → 命中的是 2 字实体"贝斯"（得分中）→ 保留，
          否则长问句里的短实体就永远检索不到；
        - "推荐几部好看的电影" → 只命中"电影"这类通用 2 字词（得分低）→ 丢弃。

        片段是否算噪声按**全量知识库**的占比判断：用候选集当分母会让粗召回出来的
        片段比例全都接近 100%，把唯一能命中的片段也剔掉（见下方实现处说明）。

        已知限制（实测数据，改前请先看）：2 字片段权重 3 低于 `MIN_MATCH_SCORE`，
        所以"答案本身就是一个两字术语"的查询（"什么是和声""什么是调性""什么是混响"）
        命中不了。把这个权重提到 6 能补上这些查询（命中 18/31 → 31/31），但会多出
        3 条误命中——跨词边界切出来的假 2 字片段（"上海的高铁"切出的 `的高`、
        "用一段固定旋律"里的 `一段`、"好看的电影"切出的 `的电`）同样能凑到 6 分。
        试过用"片段在文档里的紧邻字符要与它在查询里的紧邻字符一致"来过滤假词，
        结果连真的 2 字词也一起滤掉（命中掉到 15，比现状还差），因为 `和声` 与
        `高铁` 在字符串层面完全同构，差别只在语义（是否音乐术语）。
        结论：不引入分词器或语义判据就无法再优化这条路径。线上该路径有向量检索
        兜底（`rag_service` 优先走向量，实测 20/20 命中），这里只是降级路径。
        """
        terms = build_terms(query)
        if not terms:
            return [], []
        total = self.db.scalar(select(func.count()).select_from(MusicKnowledge)) or 0
        statement = (
            select(MusicKnowledge)
            .where(or_(*[MusicKnowledge.content.ilike(f"%{term}%") for term in terms]))
            .limit(max(limit * 8, 24))
        )
        candidates = list(self.db.scalars(statement))
        if not candidates:
            return [], terms

        # 噪声判定必须用**整个知识库**当分母，不能用 `candidates`：
        # candidates 是按这些片段粗召回出来的，本身就"包含这些片段"，
        # 用候选集当分母会让每个片段的比例都接近 100%，于是唯一能命中的那个片段
        # 也被当成噪声剔除，检索必然空手而归——实测「什么是和声」就是这样漏的：
        # 8 个片段里只有"和声"能命中，它却因 13/13 被判定为噪声。
        contents = [(entry.content or "").lower() for entry in candidates]
        noise = {
            term
            for term in terms
            if total and sum(1 for text in contents if term in text) / total > NOISE_TERM_RATIO
        }
        informative = [term for term in terms if term not in noise]

        scored: list[tuple[int, MusicKnowledge]] = []
        for entry, text in zip(candidates, contents, strict=True):
            score = sum(_term_weight(term) for term in informative if term in text)
            if score >= MIN_MATCH_SCORE:
                scored.append((score, entry))
        scored.sort(key=lambda item: (-item[0], item[1].id))
        return [entry for _score, entry in scored[:limit]], informative or terms

    def search_vector(
        self, embedding: list[float], limit: int, threshold: float
    ) -> list[tuple[MusicKnowledge, float]]:
        """按知识切片向量余弦相似度查询结果。"""
        distance = MusicKnowledge.embedding.cosine_distance(embedding)
        statement = (
            select(MusicKnowledge, distance.label("distance"))
            .where(
                MusicKnowledge.embedding.is_not(None),
                distance <= 1 - threshold,
            )
            .order_by(distance, MusicKnowledge.id)
            .limit(limit)
        )
        return [
            (item, float(distance_value)) for item, distance_value in self.db.execute(statement)
        ]

    def list_without_embeddings(self, limit: int) -> list[MusicKnowledge]:
        """按主键顺序读取尚未生成向量的知识切片。"""
        statement = (
            select(MusicKnowledge)
            .where(MusicKnowledge.embedding.is_(None))
            .order_by(MusicKnowledge.id)
            .limit(limit)
        )
        return list(self.db.scalars(statement))
