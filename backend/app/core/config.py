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
    # 演示账号用户名：该账号登录后仍可读全部数据，但所有写操作都会被拒绝。
    # 长度上限与注册用户名校验（schemas/auth.py 的 Username）保持一致。
    demo_username: str = Field(default="demo", min_length=1, max_length=18)

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

    web_search_enabled: bool = True
    web_search_region: str = "cn-zh"
    web_search_max_results: int = 5
    web_search_timeout_seconds: int = 8

    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_model: str = ""
    embedding_timeout_seconds: float = 30.0
    embedding_similarity_threshold: float = 0.35

    jamendo_client_id: str = ""
    jamendo_base_url: str = "https://api.jamendo.com/v3.0"
    jamendo_timeout_seconds: float = 30.0
    jamendo_max_retries: int = 3
    jamendo_retry_base_seconds: float = 1.0

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
        if self.embedding_timeout_seconds <= 0:
            raise ValueError("EMBEDDING_TIMEOUT_SECONDS 必须大于 0")
        if not 0 <= self.embedding_similarity_threshold <= 1:
            raise ValueError("EMBEDDING_SIMILARITY_THRESHOLD 必须在 0 到 1 之间")
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
        return self

    @model_validator(mode="after")
    def validate_web_search(self) -> Settings:
        """确保联网搜索配置有效。"""
        if self.web_search_max_results <= 0:
            raise ValueError("WEB_SEARCH_MAX_RESULTS 必须大于 0")
        if self.web_search_timeout_seconds <= 0:
            raise ValueError("WEB_SEARCH_TIMEOUT_SECONDS 必须大于 0")
        return self

    @model_validator(mode="after")
    def validate_jamendo_timeout(self) -> Settings:
        """确保 Jamendo 请求、重试配置有效。"""
        if self.jamendo_timeout_seconds <= 0:
            raise ValueError("JAMENDO_TIMEOUT_SECONDS 必须大于 0")
        if self.jamendo_max_retries < 0:
            raise ValueError("JAMENDO_MAX_RETRIES 不能小于 0")
        if self.jamendo_retry_base_seconds < 0:
            raise ValueError("JAMENDO_RETRY_BASE_SECONDS 不能小于 0")
        return self


@lru_cache
def get_settings() -> Settings:
    """返回全局单例配置。"""
    return Settings()


settings = get_settings()
