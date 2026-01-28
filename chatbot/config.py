"""RAILDOCK 챗봇 설정"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatbotSettings(BaseSettings):
    # Google Gemini (챗봇용)
    google_api_key: str = ""
    chatbot_model: str = "gemini-2.5-flash"

    # 보고서 Vector DB
    report_db_path: str = "./data/report_db"

    # 검색 설정
    report_top_k: int = 5
    report_threshold: float = 0.3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # .env의 다른 필드 무시
    )


chatbot_settings = ChatbotSettings()
