#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
철도 문서 AI 시스템 실행 스크립트

사용법:
    python run.py              # 서버만 실행
    python run.py --setup      # 의존성 설치 + 서버 실행
    python run.py --init-db    # DB 초기화 + PDF 임베딩 + 서버 실행
"""

import subprocess
import sys
import os
from pathlib import Path


def install_dependencies():
    """의존성 설치"""
    print("=" * 50)
    print("  [1/4] 의존성 설치 중...")
    print("=" * 50)

    requirements_path = Path(__file__).parent / "requirements.txt"
    if requirements_path.exists():
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r",
            str(requirements_path), "-q"
        ])
        print("  ✓ 의존성 설치 완료\n")
    else:
        print("  ⚠ requirements.txt를 찾을 수 없습니다.\n")


def check_env():
    """환경변수 확인"""
    print("=" * 50)
    print("  [2/4] 환경 설정 확인 중...")
    print("=" * 50)

    env_path = Path(__file__).parent / ".env"
    env_example_path = Path(__file__).parent / ".env.example"

    if not env_path.exists():
        if env_example_path.exists():
            import shutil
            shutil.copy(env_example_path, env_path)
            print("  ⚠ .env 파일 생성됨. GOOGLE_API_KEY를 설정하세요!")
            print(f"    파일 위치: {env_path}")
            return False
        else:
            print("  ⚠ .env 파일이 없습니다.")
            return False

    # API 키 확인
    from dotenv import load_dotenv
    load_dotenv(env_path)

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key or api_key == "xxxx":
        print("  ⚠ GOOGLE_API_KEY가 설정되지 않았습니다!")
        return False

    print("  ✓ 환경 설정 확인 완료\n")
    return True


def setup_directories():
    """필요한 디렉토리 생성"""
    print("=" * 50)
    print("  [3/4] 디렉토리 설정 중...")
    print("=" * 50)

    base_path = Path(__file__).parent

    dirs = [
        base_path / "data" / "chroma_db",
        base_path / "data" / "reports",
        base_path / "data" / "report_db",  # 챗봇용 보고서 Vector DB
    ]

    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)

    print("  ✓ 디렉토리 설정 완료\n")


def init_database():
    """PDF 임베딩 초기화"""
    print("=" * 50)
    print("  [추가] ChromaDB 초기화 및 PDF 임베딩...")
    print("=" * 50)

    try:
        from app.services.vector_service import vector_service
        from app.utils.pdf_loader import pdf_loader
        from app.config import settings

        # 기존 데이터 초기화
        vector_service.clear_collection()
        print("  ✓ 기존 데이터 초기화 완료")

        # PDF 로드
        paths = [p.strip() for p in settings.regulations_paths.split(",")]
        total_chunks = 0

        for reg_path in paths:
            regulations_path = Path(reg_path)
            if not regulations_path.is_absolute():
                regulations_path = Path.cwd() / regulations_path

            if not regulations_path.exists():
                continue

            pdfs = pdf_loader.load_directory(str(regulations_path))
            is_maintenance = "maintenance" in str(regulations_path).lower()

            for pdf in pdfs:
                if is_maintenance:
                    chunks = vector_service.add_whole_document(
                        document_text=pdf['content'],
                        source=pdf['filename']
                    )
                else:
                    chunks = vector_service.add_regulation_document(
                        document_text=pdf['content'],
                        source=pdf['filename']
                    )
                total_chunks += chunks
                print(f"    - {pdf['filename']}: {chunks}개 청크")

        stats = vector_service.get_collection_stats()
        print(f"  ✓ 총 {stats['total_chunks']}개 청크 임베딩 완료\n")

    except Exception as e:
        print(f"  ⚠ 임베딩 실패: {e}\n")


def run_server():
    """서버 실행"""
    print("=" * 50)
    print("  [4/4] 서버 시작...")
    print("=" * 50)
    print()
    print("  📡 API 문서: http://localhost:8000/docs")
    print("  🔧 서버 종료: Ctrl+C")
    print()
    print("=" * 50)

    subprocess.call([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
    ])


def main():
    # 작업 디렉토리 설정
    os.chdir(Path(__file__).parent)

    args = sys.argv[1:]

    print()
    print("╔" + "═" * 48 + "╗")
    print("║        철도 문서 AI 시스템 (LLM + RAG)          ║")
    print("╚" + "═" * 48 + "╝")
    print()

    # --setup: 의존성 설치 포함
    if "--setup" in args:
        install_dependencies()

    # 환경 확인
    if not check_env():
        print("환경 설정을 완료한 후 다시 실행하세요.")
        return

    # 디렉토리 설정
    setup_directories()

    # --init-db: DB 초기화 및 PDF 임베딩
    if "--init-db" in args:
        init_database()

    # 서버 실행
    run_server()


if __name__ == "__main__":
    main()
