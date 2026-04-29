import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # DeepSeek API
    DEEPSEEK_API_KEY: str = os.getenv("FASTGPT_APP_ID")
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # FastGPT API（兼容 OpenAI 接口）
    FASTGPT_API_KEY: str = os.getenv("FASTGPT_API_KEY")
    FASTGPT_BASE_URL: str = "https://cloud.fastgpt.cn/api/v1"
    FASTGPT_APP_ID: str = os.getenv("FASTGPT_APP_ID")

    # App
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
