"""데이터베이스 초기화 스크립트"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.db_service import db_service


def main():
    print("=" * 50)
    print("MySQL 데이터베이스 초기화")
    print("=" * 50)

    try:
        db_service.init_tables()
        print("[SUCCESS] 테이블 생성 완료!")
        print("  - vision_metadata")
        print("  - generated_documents")
    except Exception as e:
        print(f"[ERROR] 초기화 실패: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
