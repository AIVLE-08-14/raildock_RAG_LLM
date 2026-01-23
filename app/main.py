"""FastAPI 메인 애플리케이션 - LLM + RAG 문서 AI 시스템"""

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.routers import document, pipeline
from app.config import settings
from app.utils.pdf_loader import pdf_loader
from app.services.vector_service import vector_service

app = FastAPI(
    title="철도 문서 AI 시스템",
    description="Vision 결과 기반 문서 생성/검토 시스템 (LLM + RAG)",
    version="0.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(document.router, prefix="/document", tags=["Document"])
app.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline"])


@app.get("/")
async def root():
    return {
        "message": "철도 문서 AI 시스템 (LLM + RAG)",
        "version": "0.2.0",
        "endpoints": {
            "pipeline": {
                "process_zip": "POST /pipeline/process-zip (ZIP 파일 업로드 → 자동 처리)",
                "process_folder": "POST /pipeline/process-folder (로컬 폴더 처리)",
                "download_pdf": "GET /pipeline/download-pdf/{filename}",
                "list_pdfs": "GET /pipeline/list-pdfs"
            },
            "document": {
                "generate": "POST /document/generate",
                "review": "POST /document/review",
                "query": "POST /document/query",
                "regulations": "GET /document/regulations"
            },
            "regulations": {
                "load_pdfs": "POST /regulations/load-pdfs",
                "clear": "DELETE /regulations/clear"
            }
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.delete("/regulations/clear")
async def clear_regulations():
    """ChromaDB 컬렉션 초기화 (모든 임베딩 삭제)"""
    try:
        result = vector_service.clear_collection()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"초기화 실패: {str(e)}")


@app.post("/regulations/load-pdfs")
async def load_regulation_pdfs():
    """
    규정 PDF 파일들을 ChromaDB에 임베딩

    - scenario_document: [규정 ID] 기준 청킹 (시나리오별 규정)
    - maintenance_document: 전체 문서 통째로 저장 (핵심 참조 문서)
    """
    try:
        # 여러 경로 지원
        paths = [p.strip() for p in settings.regulations_paths.split(",")]

        results = []
        total_chunks = 0
        loaded_paths = []

        for reg_path in paths:
            regulations_path = Path(reg_path)

            # 상대 경로인 경우 현재 작업 디렉토리 기준으로 변환
            if not regulations_path.is_absolute():
                regulations_path = Path.cwd() / regulations_path

            if not regulations_path.exists():
                continue

            loaded_paths.append(str(regulations_path))

            # PDF 파일 로드
            pdfs = pdf_loader.load_directory(str(regulations_path))

            # 폴더 유형 판별
            is_maintenance = "maintenance" in str(regulations_path).lower()

            for pdf in pdfs:
                if is_maintenance:
                    # maintenance_document: 전체 문서 통째로 저장
                    chunks_added = vector_service.add_whole_document(
                        document_text=pdf['content'],
                        source=pdf['filename']
                    )
                    doc_type = "maintenance (전체 저장)"
                else:
                    # scenario_document: [규정 ID] 기준 청킹
                    chunks_added = vector_service.add_regulation_document(
                        document_text=pdf['content'],
                        source=pdf['filename']
                    )
                    doc_type = "scenario (청킹)"

                results.append({
                    "filename": pdf['filename'],
                    "content_length": len(pdf['content']),
                    "chunks_added": chunks_added,
                    "doc_type": doc_type
                })
                total_chunks += chunks_added

        if not results:
            return {
                "message": "PDF 파일을 찾을 수 없습니다.",
                "paths": loaded_paths,
                "chunks_added": 0
            }

        # 최종 통계
        stats = vector_service.get_collection_stats()

        return {
            "message": f"규정 PDF {len(results)}개 로드 완료",
            "total_chunks_added": total_chunks,
            "paths": loaded_paths,
            "files": results,
            "collection_stats": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 로드 실패: {str(e)}")
