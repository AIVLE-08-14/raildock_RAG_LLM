"""규정 문서 임베딩 스크립트 (PDF 지원)"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from pypdf import PdfReader
from app.services.vector_service import vector_service
from app.config import settings


def extract_text_from_pdf(pdf_path: Path) -> str:
    """PDF에서 텍스트 추출"""
    reader = PdfReader(str(pdf_path))
    text_parts = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)

    return "\n".join(text_parts)


def load_regulation_files(regulations_dir: Path) -> list:
    """규정 문서 파일 로드 (PDF + TXT 지원)"""
    documents = []

    # PDF 파일 처리
    for file_path in regulations_dir.glob("*.pdf"):
        print(f"  PDF 로드 중: {file_path.name}")
        content = extract_text_from_pdf(file_path)
        documents.append({
            'source': file_path.name,
            'content': content
        })

    # TXT 파일도 지원 (기존 호환성)
    for file_path in regulations_dir.glob("*.txt"):
        print(f"  TXT 로드 중: {file_path.name}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            documents.append({
                'source': file_path.name,
                'content': content
            })

    return documents


def main():
    print("=" * 50)
    print("규정 문서 임베딩 (ChromaDB)")
    print("=" * 50)

    # 규정 문서 경로 (scenario_document 폴더)
    regulations_dir = Path(__file__).parent.parent / settings.regulations_path
    regulations_dir = regulations_dir.resolve()

    print(f"\n규정 문서 경로: {regulations_dir}")

    if not regulations_dir.exists():
        print(f"[ERROR] 규정 문서 폴더가 없습니다: {regulations_dir}")
        print("  → scenario_document 폴더에 규정 PDF 파일을 추가해주세요.")
        return 1

    # 문서 로드
    print("\n문서 로드 중...")
    documents = load_regulation_files(regulations_dir)

    if not documents:
        print("[WARNING] 규정 문서가 없습니다.")
        print("  → scenario_document 폴더에 규정 PDF 파일을 추가해주세요.")
        return 0

    print(f"\n발견된 문서: {len(documents)}개")
    for doc in documents:
        print(f"  - {doc['source']} ({len(doc['content'])} 글자)")

    # 임베딩
    total_chunks = 0
    for doc in documents:
        print(f"\n처리 중: {doc['source']}")
        chunk_count = vector_service.add_regulation_document(
            document_text=doc['content'],
            source=doc['source']
        )
        print(f"  → {chunk_count}개 청크 추가됨")
        total_chunks += chunk_count

    # 결과
    print("\n" + "=" * 50)
    print(f"[SUCCESS] 임베딩 완료!")
    print(f"  - 문서 수: {len(documents)}")
    print(f"  - 총 청크 수: {total_chunks}")
    print("=" * 50)

    # 통계 출력
    stats = vector_service.get_collection_stats()
    print(f"\nChromaDB 상태:")
    print(f"  - 총 청크: {stats['total_chunks']}")
    print(f"  - 규정 수: {stats['total_regulations']}")

    return 0


if __name__ == "__main__":
    exit(main())
