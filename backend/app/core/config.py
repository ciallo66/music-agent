"""应用配置：从 .env 读取，使用 pydantic-settings。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """应用配置项。密钥/URL 全部走 .env，禁止硬编码。"""

    app_name: str = "music-agent"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 4320
    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # 演示账号用户名：正常功能（收藏、歌单、反馈、对话、收听记录）照常可用，
    # 只有后台改数据的入口对它只读。长度上限与注册用户名校验（schemas/auth.py
    # 的 Username）保持一致。
    demo_username: str = Field(default="demo", min_length=1, max_length=18)
    # 演示账号密码：登录页的「一键进入演示账号」用它登录，因此必须与前端
    # VITE_DEMO_PASSWORD 一致；换环境时改这里，再用
    # `python -m scripts.ensure_demo_account` 把库里的账号对上。
    demo_password: str = Field(default="demo1234", min_length=4, max_length=18)

    database_url: str = "postgresql+psycopg://postgres:your_password@127.0.0.1:5432/music_agent"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_timeout_seconds: float = 30.0
    agent_context_token_budget: int = 12000
    agent_response_token_budget: int = 2000
    agent_tool_result_max_chars: int = 12000
    agent_tool_timeout_seconds: float = 10.0
    # 工具调用轮数上限：仅作防事故保险丝，正常终止由无进展检测和时间预算决定。
    agent_max_tool_rounds: int = 20
    # 单次对话的时间预算，耗尽后走兜底收尾而不是报错。
    agent_total_timeout_seconds: float = 90.0
    # 连续出现完全相同的工具调用达到该次数，即判定模型在原地打转。
    agent_no_progress_limit: int = 2
    agent_tool_retry_max: int = 2
    agent_tool_retry_backoff_seconds: float = 0.5
    # 高风险工具调用的待确认有效期，超时后必须重新发起。
    agent_confirmation_ttl_seconds: int = 600
    # 历史窗口：只把最近 N 条消息原文交给模型，更早的折叠成一行摘要。
    # 依据：主流对话产品都用「滑动窗口 + 摘要」而不是无限堆历史——历史越长，
    # 模型越容易锚定在旧任务上（实测出现过复读上一轮答案、忽略当前提问的情况）。
    agent_history_max_messages: int = 20
    # 提示词里回顾"最近用过哪些工具"的条数，防止模型重复查同一件事。
    agent_history_tool_notes: int = 6
    # 滚动摘要：历史超过窗口 + 这个阈值时才压缩，避免每轮都调用模型。
    # 只在触发时多花一次模型调用（实测约 1.7-2.2s），前若干轮零开销。
    agent_summary_fold_batch: int = 10

    web_search_enabled: bool = True
    # 搜索源：tavily（官方 API，返回已抽取正文，需 key）/ bing_cn（抓取必应中国，境内可达）
    # / duckduckgo（境外，境内服务器实测全线不可达）。
    web_search_provider: Literal["tavily", "bing_cn", "duckduckgo"] = "bing_cn"
    web_search_region: str = "cn-zh"
    web_search_max_results: int = 5
    web_search_timeout_seconds: int = 8
    # 必应中国的搜索入口与市场参数（跟随 web_search_region 语言）。
    web_search_bing_url: str = "https://cn.bing.com/search"
    web_search_market: str = "zh-CN"
    # Tavily 搜索 API。key 只能来自环境变量（.env / .env.production），绝不写进源码或 Git。
    web_search_api_key: str = ""
    web_search_tavily_url: str = "https://api.tavily.com/search"
    # basic 更快更省额度；advanced 抓取更深但更慢。
    web_search_tavily_depth: Literal["basic", "advanced"] = "basic"

    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_model: str = ""
    embedding_timeout_seconds: float = 30.0
    # 歌曲相似度阈值：用于「找相似歌曲」，口径较松（结构化兜底会再筛）。
    embedding_similarity_threshold: float = 0.35
    # 知识库检索阈值：必须比歌曲那条严。线上定标数据（bge-m3 + 48 条知识）：
    #   该命中的问题首条相似度 0.5962~0.7609（均值 0.7005）
    #   不该命中的问题      0.3354~0.4618（均值 0.3993）
    # 中间有 0.13 的空档，取 0.50 可以 20/20 保留命中、10/10 挡住无关问题；
    # 取 0.35 时"今天天气怎么样""1+1 等于几"都会返回 5 条无关知识。
    embedding_knowledge_threshold: float = 0.50
    # 向量维度必须与 embedding_model 一致（BAAI/bge-m3 = 1024）。
    # 数据库列已按该维度声明，换模型时必须同步改这里并新写一条迁移。
    embedding_dimension: int = 1024

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_secret_key(self) -> Settings:
        """拒绝空值和示例密钥，避免使用默认 JWT 密钥启动。"""
        if not self.secret_key or self.secret_key in {
            "change-me",
            "replace-with-a-random-secret",
        }:
            raise ValueError("SECRET_KEY 必须在 .env 中配置为随机密钥")
        if self.deepseek_timeout_seconds <= 0:
            raise ValueError("DEEPSEEK_TIMEOUT_SECONDS 必须大于 0")
        if self.agent_context_token_budget <= 0:
            raise ValueError("AGENT_CONTEXT_TOKEN_BUDGET 必须大于 0")
        if self.agent_response_token_budget <= 0:
            raise ValueError("AGENT_RESPONSE_TOKEN_BUDGET 必须大于 0")
        if self.agent_tool_result_max_chars <= 0:
            raise ValueError("AGENT_TOOL_RESULT_MAX_CHARS 必须大于 0")
        if self.agent_tool_timeout_seconds <= 0:
            raise ValueError("AGENT_TOOL_TIMEOUT_SECONDS 必须大于 0")
        if self.agent_max_tool_rounds <= 0:
            raise ValueError("AGENT_MAX_TOOL_ROUNDS 必须大于 0")
        return self

    @model_validator(mode="after")
    def validate_embedding_limits(self) -> Settings:
        """确保 Embedding 相关配置有效（两条阈值分别校验）。"""
        if self.embedding_timeout_seconds <= 0:
            raise ValueError("EMBEDDING_TIMEOUT_SECONDS 必须大于 0")
        if not 0 <= self.embedding_similarity_threshold <= 1:
            raise ValueError("EMBEDDING_SIMILARITY_THRESHOLD 必须在 0 到 1 之间")
        if not 0 <= self.embedding_knowledge_threshold <= 1:
            raise ValueError("EMBEDDING_KNOWLEDGE_THRESHOLD 必须在 0 到 1 之间")
        return self

    @model_validator(mode="after")
    def validate_agent_limits(self) -> Settings:
        """确保 Agent 兜底与工具重试配置有效。"""
        if self.agent_total_timeout_seconds <= 0:
            raise ValueError("AGENT_TOTAL_TIMEOUT_SECONDS 必须大于 0")
        if self.agent_no_progress_limit <= 0:
            raise ValueError("AGENT_NO_PROGRESS_LIMIT 必须大于 0")
        if self.agent_tool_retry_max < 0:
            raise ValueError("AGENT_TOOL_RETRY_MAX 不能小于 0")
        if self.agent_tool_retry_backoff_seconds < 0:
            raise ValueError("AGENT_TOOL_RETRY_BACKOFF_SECONDS 不能小于 0")
        if self.agent_confirmation_ttl_seconds <= 0:
            raise ValueError("AGENT_CONFIRMATION_TTL_SECONDS 必须大于 0")
        if self.agent_history_max_messages < 2:
            raise ValueError("AGENT_HISTORY_MAX_MESSAGES 至少为 2（一轮问答）")
        if self.agent_history_tool_notes < 0:
            raise ValueError("AGENT_HISTORY_TOOL_NOTES 不能小于 0")
        if self.agent_summary_fold_batch <= 0:
            raise ValueError("AGENT_SUMMARY_FOLD_BATCH 必须大于 0")
        return self

    @model_validator(mode="after")
    def validate_web_search(self) -> Settings:
        """确保联网搜索配置有效。"""
        if self.web_search_max_results <= 0:
            raise ValueError("WEB_SEARCH_MAX_RESULTS 必须大于 0")
        if self.web_search_timeout_seconds <= 0:
            raise ValueError("WEB_SEARCH_TIMEOUT_SECONDS 必须大于 0")
        if not self.web_search_bing_url.startswith("http"):
            raise ValueError("WEB_SEARCH_BING_URL 必须是 http(s) 地址")
        return self


@lru_cache
def get_settings() -> Settings:
    """返回全局单例配置。"""
    return Settings()


settings = get_settings()
