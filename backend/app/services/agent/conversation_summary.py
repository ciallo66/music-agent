"""会话滚动摘要：把滑出窗口的历史压成要点。

为什么需要：历史按条数窗口裁剪后，更早的内容只剩一句"已折叠 N 条"的计数，
模型拿不到任何信息。长对话里最容易被丢掉的是**用户最初提的限制条件**和**已有结论**，
于是"接着刚才的条件再筛一下"这类追问就会答偏。

设计要点（对齐业界做法）：
- **阈值触发**：只有历史超过窗口才压缩，前 N 轮零开销；
- **增量**：记录摘要覆盖到哪条消息，只压缩新增的滑出部分，不每轮重算；
- **保真**：强制保留首条用户消息原文，并要求摘要保留限制条件、结论与未完成事项；
- **不静默丢历史**：摘要为空或调用失败时返回 None，调用方退回原有窗口行为。
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import ChatMessage, ChatSession
from app.repositories.chat_repository import ChatRepository
from app.services.agent.provider import ChatProvider, DeepSeekProvider, LLMProviderError

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = (
    "你在为一个对话式 AI 助手压缩较早的对话记录。请输出要点，供后续对话继续使用。\n"
    "必须保留：\n"
    "1) 用户提出的需求与限制条件（风格、时长、BPM、只要器乐等具体数值与措辞）；\n"
    "2) 已经得到的结论与关键数据；\n"
    "3) 涉及的具体对象（歌曲/歌单的名称与 id）；\n"
    "4) 尚未完成的事项。\n"
    "要求：不编造、不添加新信息；用简短条目；不要客套话与解释。"
)

# 摘要请求的输出上限。deepseek-flash 是推理模型，思考内容同样计入 max_tokens：
# 实测 300 与 900 都会被思考链吃光、正文返回空（日志里能看到"摘要返回为空"），
# 因此这里给足额度，并同时关闭思考链（摘要属于搬运信息的机械任务，不需要推理）。
SUMMARY_MAX_TOKENS = 2000


class ConversationSummarizer:
    """按需把较早的会话消息压缩成滚动摘要。"""

    def __init__(self, db: Session, provider: ChatProvider | None = None) -> None:
        """绑定数据库会话与模型供应商；未注入时使用默认 DeepSeek 客户端。"""
        self.db = db
        self.chats = ChatRepository(db)
        self.provider = provider or DeepSeekProvider()

    def prepare(self, chat_session: ChatSession) -> tuple[str | None, list[ChatMessage]]:
        """返回（滚动摘要, 需要逐字保留的最近消息）。

        只有消息条数超过窗口 + 折叠阈值时才压缩；压缩失败不影响正常回答。
        """
        messages = self.chats.list_messages(chat_session.id)
        window = settings.agent_history_max_messages
        if len(messages) <= window + settings.agent_summary_fold_batch:
            return chat_session.chat_summary, messages

        # 需要折叠的界线：保留最近 window 条，其余进入摘要。
        boundary_index = len(messages) - window
        cutoff_id = messages[boundary_index - 1].id
        summarized_through = chat_session.summarized_through_id or 0
        if cutoff_id <= summarized_through:
            # 没有新的内容滑出窗口：直接用已有摘要，不再调用模型。
            return chat_session.chat_summary, messages[boundary_index:]

        to_fold = [
            message
            for message in messages
            if summarized_through < message.id <= cutoff_id
            and message.role in {"user", "assistant"}
        ]
        # 够一批才压缩：滑出几条就调用一次模型属于浪费（代价是每轮多一次 2 秒左右的调用）。
        # 不够一批时沿用已有摘要，窗口本身仍在保护上下文。
        if len(to_fold) < settings.agent_summary_fold_batch:
            return chat_session.chat_summary, messages[boundary_index:]

        summary = self._summarize(chat_session, to_fold, cutoff_id)
        if summary is None:
            # 摘要失败：退回原窗口行为，不阻塞本轮，也不写坏数据。
            return chat_session.chat_summary, messages
        return summary, messages[boundary_index:]

    def _summarize(
        self, chat_session: ChatSession, to_fold: list[ChatMessage], cutoff_id: int
    ) -> str | None:
        """调用模型生成增量摘要并落库；失败或空摘要返回 None。"""
        transcript = "\n".join(
            f"{'用户' if message.role == 'user' else '助手'}：{message.content}"
            for message in to_fold
        )
        parts = [
            f"【已有的较早对话摘要】\n{chat_session.chat_summary}"
            if chat_session.chat_summary
            else "",
            f"【本次需要并入摘要的对话】\n{transcript}",
        ]
        prompt = "\n\n".join(part for part in parts if part)
        try:
            response = self.provider.complete(
                [
                    {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                tools=[],
                max_tokens=SUMMARY_MAX_TOKENS,
                disable_reasoning=True,
            )
        except LLMProviderError as error:
            logger.warning("会话摘要生成失败，沿用现有窗口：%s", error)
            return None

        summary = (response.content or "").strip()
        if not summary:
            # 推理模型可能把 max_tokens 全用在推理上，此时 content 为空。
            # 宁可退回计数式窗口，也不能把历史摘要成空。
            logger.warning("会话摘要返回为空，保留原窗口行为（会话 %s）", chat_session.id)
            return None

        chat_session.chat_summary = summary
        chat_session.summarized_through_id = cutoff_id
        self.db.flush()
        return summary
