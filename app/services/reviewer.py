"""문서 검토 LLM 서비스 (Gemini)"""

import re
import google.generativeai as genai
from typing import Dict, Any, List

from app.config import settings
from app.services.vector_service import vector_service


class DocumentReviewer:
    """Google Gemini 기반 문서 검토 서비스"""

    def __init__(self):
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    def review(
        self,
        document: str,
        vision_result: Dict[str, Any]
    ) -> str:
        """
        문서 검토 및 권장 조치내용 직접 수정

        Args:
            document: 검토할 문서
            vision_result: 원본 Vision 결과

        Returns:
            수정된 문서 전체
        """
        # 관련 규정 검색 (검토용)
        detections = vision_result.get('detections', [])
        query = self._build_review_query(detections)
        chunks = vector_service.search(query, top_k=3)

        # 프롬프트 구성
        prompt = self._build_review_prompt(document, vision_result, chunks)

        # Gemini API 호출
        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=8000
            )
        )

        revised_document = response.text

        # 수정된 문서 정리
        revised_document = self._clean_revised_document(revised_document)

        return revised_document

    def _build_review_query(self, detections: List[Dict]) -> str:
        """검토용 RAG 쿼리 생성"""
        query_parts = []
        for det in detections:
            cls_name = det.get('cls_name', '')
            detail = det.get('detail', '')
            if cls_name and detail:
                query_parts.append(f"{cls_name} {detail} 조치 기준")
        return " ".join(query_parts) if query_parts else "철도 결함 점검 기준"

    def _build_review_prompt(
        self,
        document: str,
        vision_result: Dict,
        chunks: List[Dict]
    ) -> str:
        """검토 프롬프트 구성"""
        detections = vision_result.get('detections', [])

        # 규정 컨텍스트
        regulation_context = ""
        if chunks:
            reg_parts = []
            for chunk in chunks:
                reg_id = chunk.get('regulation_id', 'Unknown')
                content = chunk.get('content', '')[:500]
                reg_parts.append(f"[{reg_id}]\n{content}")
            regulation_context = "\n\n".join(reg_parts)

        prompt = f"""당신은 철도 안전 규정 전문가입니다.
아래 점검 보고서를 검토하고, [권장 조치내용] 부분을 규정에 맞게 수정해주세요.

## 검토 기준:
1. 결함 분석이 정확한가?
2. 위험도 평가(E/O/X1/X2/S)가 적절한가?
3. 권장 조치가 규정에 부합하는가?
4. 누락된 조치 사항이 있는가?

## Vision AI 탐지 결과:
"""
        for det in detections:
            prompt += f"- {det.get('cls_name', 'Unknown')}: {det.get('detail', 'Unknown')} (신뢰도: {det.get('confidence', 0):.1%})\n"

        if regulation_context:
            prompt += f"""

## 관련 규정:
{regulation_context}
"""

        prompt += f"""

## 검토 대상 문서:
{document}

---

## 지시사항:
1. 위 문서를 검토하고 [권장 조치내용] 부분을 규정에 맞게 보완/수정해주세요.
2. 다른 섹션(일련번호, 철도분류, 부품명, 노선정보, 결함정보, 위험도평가)은 그대로 유지해주세요.
3. [조치결과]와 [작업이력]은 비워두세요.
4. 전체 문서를 동일한 형식으로 다시 출력해주세요.

## 출력 형식 (이 형식을 정확히 따라주세요):

[일련번호]
(기존 값 유지)

[철도분류]
(기존 값 유지)

[부품명]
(기존 값 유지)

[노선정보]
(기존 값 유지)

[결함정보]
(기존 값 유지)

[위험도평가]
(기존 값 유지)

[권장 조치내용]
(규정에 맞게 수정된 조치 내용)

[조치결과]

[작업이력]
작업일자:
작업내용:
"""

        return prompt

    def _clean_revised_document(self, document: str) -> str:
        """수정된 문서 정리"""
        # 마크다운 코드 블록 제거
        document = re.sub(r'```[a-z]*\n?', '', document)
        document = document.strip()

        # ## 철도 시설물 점검 보고서 제목 제거 (있으면)
        document = re.sub(r'^##?\s*철도\s*시설물\s*점검\s*보고서\s*\n*', '', document)

        return document.strip()


# 싱글톤 인스턴스
document_reviewer = DocumentReviewer()
