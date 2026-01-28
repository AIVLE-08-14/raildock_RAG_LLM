"""RAILDOCK 챗봇 API 라우터"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from chatbot.services.chatbot_service import raildock_chatbot
from chatbot.services.report_vector_service import report_vector_service


router = APIRouter()


# ================================================================================
# 요청/응답 스키마
# ================================================================================

class ChatRequest(BaseModel):
    """챗봇 질문 요청"""
    question: str
    folder_filter: Optional[str] = None  # rail, insulator, nest

    class Config:
        json_schema_extra = {
            "example": {
                "question": "오늘 점검한 선로 중 위험한 곳이 있어?",
                "folder_filter": None
            }
        }


class ChatResponse(BaseModel):
    """챗봇 답변 응답"""
    answer: str
    related_reports: List[Dict[str, Any]]
    report_count: int


class ReportListResponse(BaseModel):
    """보고서 목록 응답"""
    total: int
    reports: List[Dict[str, Any]]


class ReportStatsResponse(BaseModel):
    """보고서 통계 응답"""
    total_reports: int
    by_folder: Dict[str, int]
    by_grade: Dict[str, int]


# ================================================================================
# API 엔드포인트
# ================================================================================

@router.post("/ask", response_model=ChatResponse)
async def ask_raildock(request: ChatRequest):
    """
    RAILDOCK에게 질문하기

    점검 보고서를 기반으로 질문에 답변합니다.

    **질문 예시:**
    - "오늘 점검한 선로 중 위험한 곳이 있어?"
    - "애자 점검 결과 요약해줘"
    - "S등급 결함 있어?"
    - "X2등급 결함 목록 알려줘"

    **folder_filter 옵션:**
    - `rail`: 선로 보고서만 검색
    - `insulator`: 애자 보고서만 검색
    - `nest`: 둥지 보고서만 검색
    - `null`: 전체 검색
    """
    try:
        result = raildock_chatbot.ask(
            question=request.question,
            folder_filter=request.folder_filter
        )

        return ChatResponse(
            answer=result["answer"],
            related_reports=result["related_reports"],
            report_count=result["report_count"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 생성 실패: {str(e)}")


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(limit: int = 100):
    """
    저장된 점검 보고서 목록 조회

    챗봇이 참조할 수 있는 보고서 목록을 반환합니다.
    """
    try:
        reports = report_vector_service.get_all_reports(limit=limit)

        return ReportListResponse(
            total=len(reports),
            reports=reports
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"목록 조회 실패: {str(e)}")


@router.get("/stats", response_model=ReportStatsResponse)
async def get_report_stats():
    """
    보고서 통계 조회

    저장된 보고서의 폴더별, 등급별 통계를 반환합니다.
    """
    try:
        summary = raildock_chatbot.get_summary()

        return ReportStatsResponse(
            total_reports=summary["total_reports"],
            by_folder=summary["by_folder"],
            by_grade=summary["by_grade"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@router.delete("/clear")
async def clear_reports():
    """
    보고서 DB 초기화

    저장된 모든 점검 보고서를 삭제합니다.
    """
    try:
        result = report_vector_service.clear()
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"초기화 실패: {str(e)}")
