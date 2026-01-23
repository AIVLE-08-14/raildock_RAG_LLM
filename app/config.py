"""설정 관리"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Google Gemini (문서 생성 + 검토)
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # ChromaDB
    chroma_persist_path: str = "./data/chroma_db"

    # 규정 문서 경로 (PDF, 쉼표로 여러 경로 지정 가능)
    regulations_paths: str = "./data/regulations"

    # RAG 설정
    chunk_size: int = 500
    chunk_overlap: int = 200
    rag_top_k: int = 5
    rag_threshold: float = 0.1

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
