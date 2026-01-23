"""규정 PDF 파일들을 ChromaDB에 임베딩하는 스크립트"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.pdf_loader import pdf_loader
from app.services.vector_service import vector_service
from app.config import settings


def embed_regulations():
    """규정 PDF 파일들을 ChromaDB에 임베딩"""
    regulations_path = Path(settings.regulations_path)

    # 상대 경로인 경우 프로젝트 루트 기준으로 변환
    if not regulations_path.is_absolute():
        regulations_path = project_root / regulations_path

    print(f"규정 문서 경로: {regulations_path}")

    if not regulations_path.exists():
        print(f"경로가 존재하지 않습니다: {regulations_path}")
        return

    # 기존 데이터 확인
    stats = vector_service.get_collection_stats()
    print(f"현재 저장된 청크 수: {stats['total_chunks']}")
    print(f"현재 저장된 규정 수: {stats['total_regulations']}")

    # PDF 파일 로드
    print("\nPDF 파일 로드 중...")
    pdfs = pdf_loader.load_directory(str(regulations_path))

    if not pdfs:
        print("PDF 파일을 찾을 수 없습니다.")
        return

    print(f"발견된 PDF 파일: {len(pdfs)}개")

    # 각 PDF 임베딩
    total_chunks = 0
    for pdf in pdfs:
        print(f"\n처리 중: {pdf['filename']}")
        print(f"  - 내용 길이: {len(pdf['content'])}자")

        # 규정 문서 추가
        chunks_added = vector_service.add_regulation_document(
            document_text=pdf['content'],
            source=pdf['filename']
        )

        print(f"  - 추가된 청크: {chunks_added}개")
        total_chunks += chunks_added

    # 최종 통계
    print("\n" + "=" * 50)
    print(f"임베딩 완료!")
    print(f"총 추가된 청크: {total_chunks}개")

    final_stats = vector_service.get_collection_stats()
    print(f"\n최종 통계:")
    print(f"  - 전체 청크 수: {final_stats['total_chunks']}")
    print(f"  - 전체 규정 수: {final_stats['total_regulations']}")
    print(f"  - 규정 ID 목록: {final_stats['regulation_ids']}")


if __name__ == "__main__":
    embed_regulations()
