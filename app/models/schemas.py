"""Pydantic 스키마 정의"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# ============================================
# Vision 결과 관련 (실제 Vision 모델 출력 형식)
# ============================================

class Detection(BaseModel):
    """탐지 결과"""
    cls_id: int
    rail_type: str              # 고속철도 / 일반철도 / 공통
    cls_name: str               # 레일, 애자 류, 조류둥지 등
    detail: str                 # 훼손, 마모, 균열 파손, 탐지 등
    confidence: float
    bbox_xyxy: List[float]


class VisionResult(BaseModel):
    """Vision 모델 결과"""
    source_mp4: str
    frame_index: int
    timestamp_ms: float
    image_file: str
    detections: List[Detection]
    is_anomaly: bool
    # 추가 메타데이터 (선택)
    노선: Optional[str] = None
    위치: Optional[str] = None


# ============================================
# 문서 생성/검토 관련
# ============================================

class DocumentGenerateRequest(BaseModel):
    """문서 생성 요청"""
    vision_result: VisionResult
    use_rag: Optional[bool] = True


class DocumentGenerateResponse(BaseModel):
    """문서 생성 응답"""
    document: str                       # 생성된 문서
    referenced_regulations: List[str]   # 참조된 규정 ID 목록
    rag_used: bool


class DocumentReviewRequest(BaseModel):
    """문서 검토 요청"""
    document: str                       # 검토할 문서
    vision_result: VisionResult         # 원본 Vision 결과


class DocumentReviewResponse(BaseModel):
    """문서 검토 응답"""
    is_valid: bool
    feedback: str
    suggestions: List[str]


# ============================================
# RAG 관련
# ============================================

class RAGQueryRequest(BaseModel):
    """RAG 질의 요청"""
    query: str
    top_k: Optional[int] = 5


class RAGQueryResponse(BaseModel):
    """RAG 질의 응답"""
    results: List[Dict[str, Any]]
