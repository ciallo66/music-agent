"""应用配置：从 .env 读取，使用 pydantic-settings。"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置项。密钥/URL 全部走 .env，禁止硬编码。"""

    app_name: str = "music-agent"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-me"

    database_url: str = "postgresql+psycopg://postgres:your_password@127.0.0.1:5432/music_agent"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    jamendo_client_id: str = ""
    jamendo_base_url: str = "https://api.jamendo.com/v3.0"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """返回全局单例配置。"""
    return Settings()


settings = get_settings()
