"""문서 생성 LLM 서비스 (Gemini)"""

import google.generativeai as genai
from typing import List, Dict, Any, Tuple
from datetime import datetime
import uuid

from app.config import settings
from app.services.vector_service import vector_service


class DocumentGenerator:
    """Google Gemini 기반 문서 생성 서비스"""

    def __init__(self):
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.threshold = settings.rag_threshold

    def generate(
        self,
        vision_result: Dict[str, Any],
        use_rag: bool = True
    ) -> Tuple[str, List[str], bool]:
        """
        문서 생성

        Args:
            vision_result: Vision 모델 결과
            use_rag: RAG 사용 여부

        Returns:
            (생성된 문서, 참조된 규정 ID 목록, RAG 사용 여부)
        """
        detections = vision_result.get('detections', [])
        referenced_regulations = []
        rag_context = ""

        # RAG로 관련 규정 검색
        if use_rag and detections:
            query = self._build_rag_query(vision_result)
            chunks = vector_service.search(query, top_k=settings.rag_top_k)

            if chunks:
                rag_context = self._format_rag_context(chunks)
                referenced_regulations = list(set(
                    c['regulation_id'] for c in chunks if c.get('regulation_id')
                ))

        # 프롬프트 구성
        prompt = self._build_prompt(vision_result, rag_context)

        # Gemini API 호출
        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=8000
            )
        )

        document = response.text

        return document, referenced_regulations, bool(rag_context)

    def _build_rag_query(self, vision_result: Dict) -> str:
        """RAG 검색용 쿼리 생성"""
        detections = vision_result.get('detections', [])
        query_parts = []

        for det in detections:
            cls_name = det.get('cls_name', '')
            detail = det.get('detail', '')
            rail_type = det.get('rail_type', '')

            if cls_name and detail:
                query_parts.append(f"{cls_name} {detail}")
            if rail_type:
                query_parts.append(rail_type)

        return " ".join(query_parts) if query_parts else "철도 결함 점검"

    def _format_rag_context(self, chunks: List[Dict]) -> str:
        """RAG 검색 결과를 컨텍스트 문자열로 포맷"""
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            reg_id = chunk.get('regulation_id', 'Unknown')
            content = chunk.get('content', '')
            context_parts.append(f"[규정 {reg_id}]\n{content}")

        return "\n\n".join(context_parts)

    def _build_prompt(self, vision_result: Dict, rag_context: str) -> str:
        """LLM 프롬프트 구성"""
        detections = vision_result.get('detections', [])
        image_file = vision_result.get('image_file', 'Unknown')
        is_anomaly = vision_result.get('is_anomaly', False)
        노선 = vision_result.get('노선', '')
        위치 = vision_result.get('위치', '')

        # 파일명에서 정보 추출 (예: rail_고속철도_220916_영암1_frame_000000.jpg)
        file_parts = image_file.replace('.jpg', '').split('_')
        if len(file_parts) >= 4:
            rail_type_from_file = file_parts[1] if len(file_parts) > 1 else ''
            location_from_file = file_parts[3] if len(file_parts) > 3 else ''
            if not 노선:
                노선 = rail_type_from_file
            if not 위치:
                위치 = location_from_file

        # 일련번호 생성
        serial_number = f"RPT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # 철도분류 결정
        rail_types = set(d.get('rail_type', '') for d in detections)
        철도분류 = ', '.join(rail_types) if rail_types else 노선

        # 부품명 목록
        parts = set(d.get('cls_name', '') for d in detections)
        부품명 = ', '.join(parts) if parts else 'Unknown'

        prompt = f"""당신은 철도 시설물 점검 보고서를 작성하는 전문가입니다.
아래 Vision AI 탐지 결과와 관련 규정을 참고하여 점검 보고서를 작성해주세요.

## Vision AI 탐지 결과
- 이미지 파일: {image_file}
- 이상 탐지 여부: {'예' if is_anomaly else '아니오'}
- 탐지된 결함 수: {len(detections)}개

### 탐지 상세:
"""
        for i, det in enumerate(detections, 1):
            prompt += f"""
{i}. 부품: {det.get('cls_name', 'Unknown')}
   - 철도유형: {det.get('rail_type', 'Unknown')}
   - 결함상태: {det.get('detail', 'Unknown')}
   - 신뢰도: {det.get('confidence', 0):.1%}
"""

        if rag_context:
            prompt += f"""

## 관련 규정 (RAG 검색 결과):
{rag_context}
"""

        prompt += f"""

## 보고서 작성 요청

아래 형식에 맞춰 보고서를 작성해주세요.
위험도 등급은 아래 기준을 참고하여 E/O/X1/X2/S 중 하나로 판정해주세요.

■ 분류 등급(E): 파손 진행 없음
 - 안전 영향: 없음
 - 교체 기간: 해당 없음
■ 분류 등급(O): 요주의 결함
 - 안전 영향: 균열 발생, 보강 없이 열차 주행 가능
 - 교체 기간: 모니터링 단계 (즉시 교체 불필요)
■ 분류 등급(X1): 중·장기 파손 발전 결함
 - 안전 영향: 중·장기적으로 파손 발전 가능
 - 교체 기간: 1개월 이내 교체 필요
■ 분류 등급(X2): 단기 파손 발전 결함
 - 안전 영향: 단기간에 파손 발전 가능
 - 교체 기간: 10일 이내 교체 필요
■ 분류 등급(S): 파손 또는 즉각 파손 위험
 - 안전 영향: 파손 상태 또는 짧은 시간 내 복잡한 파손 발전 가능
 - 교체 기간: 즉시 (당일 교체 원칙)

권장 조치내용은 반드시 관련 규정을 참고하여 작성해주세요.

---

[일련번호]
{serial_number}

[철도분류]
{철도분류}

[부품명]
{부품명}

[노선정보]
노선: {노선}
위치: {위치}

[결함정보]
결함유형: (탐지된 결함 유형을 작성)
결함상태: (상세 결함 상태 설명)

[위험도평가]
위험도 등급: (E/O/X1/X2/S 중 선택하고 판정 근거 설명)

[권장 조치내용]
(규정에 따른 권장 조치사항 작성)

[조치결과]
(미조치 - 추후 작성 예정)

[작업이력]
작업일자:
작업내용:

---

위 형식을 정확히 따라 보고서를 작성해주세요."""

        return prompt


# 싱글톤 인스턴스
document_generator = DocumentGenerator()
