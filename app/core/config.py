import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # DeepSeek API
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # FastGPT API（兼容 OpenAI 接口）
    FASTGPT_API_KEY: str = ""
    FASTGPT_BASE_URL: str = "https://cloud.fastgpt.cn/api/v1"
    FASTGPT_APP_ID: str = ""

    # JWT 配置
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production-min-32-chars"

    # MySQL 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "campus_assistant"

    # App
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    @property
    def DATABASE_URL(self) -> str:
        """动态构建数据库连接URL"""
        if self.DB_PASSWORD:
            return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        else:
            return f"mysql+pymysql://{self.DB_USER}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
