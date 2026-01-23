"""문서 생성/검토 API 라우터"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from app.models.schemas import (
    DocumentGenerateRequest,
    DocumentGenerateResponse,
    DocumentReviewRequest,
    DocumentReviewResponse,
    RAGQueryRequest,
    RAGQueryResponse
)
from app.services.generator import document_generator
from app.services.reviewer import document_reviewer
from app.services.vector_service import vector_service
from app.config import settings

router = APIRouter()


@router.post("/generate", response_model=DocumentGenerateResponse)
async def generate_document(request: DocumentGenerateRequest):
    """
    문서 초안 생성

    1. Vision 결과 분석
    2. RAG 사용 여부 결정 (threshold 기반)
    3. 관련 규정 검색 (RAG)
    4. Gemini로 초안 생성
    """
    try:
        vision_result = request.vision_result.model_dump()

        draft, referenced_regulations, rag_used = document_generator.generate(
            vision_result=vision_result,
            use_rag=request.use_rag
        )

        return DocumentGenerateResponse(
            document=draft,
            referenced_regulations=referenced_regulations,
            rag_used=rag_used
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 생성 실패: {str(e)}")


@router.post("/review", response_model=DocumentReviewResponse)
async def review_document(request: DocumentReviewRequest):
    """
    문서 초안 검토

    1. 초안과 Vision 결과 분석
    2. 관련 규정 검색 (RAG)
    3. Gemini로 규정 준수 여부 검토
    """
    try:
        vision_result = request.vision_result.model_dump()

        is_valid, feedback, suggestions = document_reviewer.review(
            document=request.document,
            vision_result=vision_result
        )

        return DocumentReviewResponse(
            is_valid=is_valid,
            feedback=feedback,
            suggestions=suggestions
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 검토 실패: {str(e)}")


@router.post("/query", response_model=RAGQueryResponse)
async def query_regulations(request: RAGQueryRequest):
    """
    RAG 질의응답

    규정 문서에서 관련 내용 검색
    """
    try:
        chunks = vector_service.search(
            query=request.query,
            top_k=request.top_k or settings.rag_top_k
        )

        # 검색 결과 포맷팅
        sources = []
        context_parts = []

        for chunk in chunks:
            sources.append({
                "regulation_id": chunk.get('regulation_id'),
                "content_preview": chunk.get('content', '')[:200] + "...",
                "distance": chunk.get('distance')
            })
            context_parts.append(chunk.get('content', ''))

        return RAGQueryResponse(
            results=sources
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")


@router.get("/regulations")
async def list_regulations():
    """저장된 규정 목록 조회"""
    stats = vector_service.get_collection_stats()
    return stats


@router.post("/regulations/add")
async def add_regulation_document(
    document_text: str,
    source: Optional[str] = "manual"
):
    """규정 문서 추가 (청킹 → 임베딩 → 저장)"""
    try:
        chunk_count = vector_service.add_regulation_document(
            document_text=document_text,
            source=source
        )

        return {
            "message": f"규정 문서 추가 완료",
            "chunks_added": chunk_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 추가 실패: {str(e)}")
