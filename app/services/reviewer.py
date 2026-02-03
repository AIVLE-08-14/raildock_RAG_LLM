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

    def _fix_line_breaks(self, text: str) -> str:
        """숫자/퍼센트/괄호 관련 잘못된 줄바꿈 수정 - 강화 버전"""

        # ===== 1단계: 숫자 중간 줄바꿈 수정 =====
        # "75.\n6%" → "75.6%"
        text = re.sub(r'(\d+)\.\s*\n\s*(\d+)', r'\1.\2', text)

        # ===== 2단계: 괄호 관련 줄바꿈 제거 =====
        # 여는 괄호 직후 줄바꿈 제거
        text = re.sub(r'\(\s*\n\s*', '(', text)
        # 닫는 괄호 직전 줄바꿈 제거
        text = re.sub(r'\s*\n\s*\)', ')', text)

        # 괄호 안 모든 줄바꿈 제거 (여러 번 반복)
        def fix_parentheses(match):
            return re.sub(r'\s*\n\s*', ' ', match.group(0))
        for _ in range(5):
            text = re.sub(r'\([^)]*\n[^)]*\)', fix_parentheses, text)

        # ===== 3단계: 닫는 괄호 뒤 줄바꿈 + 한글 =====
        # "26.1°C)\n는" → "26.1°C)는"
        text = re.sub(r'\)\s*\n\s*([가-힣])', r')\1', text)

        # ===== 4단계: 숫자/단위 뒤 줄바꿈 + 한글 (핵심) =====
        # "26.1°C\n는" → "26.1°C는"
        text = re.sub(r'(\d+\.?\d*°C)\s*\n\s*([가-힣])', r'\1\2', text)
        # "58%\n는" → "58%는"
        text = re.sub(r'(\d+\.?\d*%)\s*\n\s*([가-힣])', r'\1\2', text)
        # "26.1\n°C" → "26.1°C"
        text = re.sub(r'(\d+\.?\d*)\s*\n\s*(°C)', r'\1\2', text)

        # ===== 5단계: 한글 뒤 줄바꿈 + 숫자 =====
        # "온도\n26.1" → "온도 26.1"
        text = re.sub(r'([가-힣])\s*\n\s*(\d)', r'\1 \2', text)
        # "온도,\n26.1" → "온도, 26.1"
        text = re.sub(r'([가-힣]),\s*\n\s*(\d)', r'\1, \2', text)

        # ===== 6단계: 숫자 뒤 줄바꿈 + 한글 (일반) =====
        # "10일\n이내" → "10일 이내"
        text = re.sub(r'(\d+일)\s*\n\s*([가-힣])', r'\1 \2', text)
        # "1개월\n이내" → "1개월 이내"
        text = re.sub(r'(\d+개월)\s*\n\s*([가-힣])', r'\1 \2', text)
        # "2개소\n교체" → "2개소 교체"
        text = re.sub(r'(\d+개소?)\s*\n\s*([가-힣])', r'\1 \2', text)

        # ===== 7단계: 특수 패턴 =====
        # "신뢰도\n75.6%" → "신뢰도 75.6%"
        text = re.sub(r'신뢰도\s*\n\s*(\d)', r'신뢰도 \1', text)
        # "68.3%,\n66.9%" → "68.3%, 66.9%"
        text = re.sub(r'(\d+\.?\d*%)\s*,\s*\n\s*(\d)', r'\1, \2', text)
        # "(60.9%~\n69.2%)" → "(60.9%~69.2%)"
        text = re.sub(r'(\d+\.?\d*%)\s*~\s*\n\s*(\d)', r'\1~\2', text)

        # ===== 8단계: 콜론/쉼표 뒤 줄바꿈 =====
        # "날씨:\n흐림" → "날씨: 흐림"
        text = re.sub(r':\s*\n\s*([가-힣])', r': \1', text)
        # ",\n26.1" → ", 26.1"
        text = re.sub(r',\s*\n\s*(\d)', r', \1', text)

        # ===== 9단계: 리스트 항목 줄바꿈 =====
        # "- \n항목" → "- 항목"
        text = re.sub(r'-\s*\n\s*(\w)', r'- \1', text)

        # ===== 10단계: 연속 빈 줄 정리 =====
        text = re.sub(r'\n{3,}', '\n\n', text)

        # ===== 11단계: 최종 safety net - 숫자 앞뒤 줄바꿈 전부 제거 =====
        # 숫자 바로 앞 줄바꿈 (한글 뒤): "현재\n26" → "현재 26"
        text = re.sub(r'([가-힣a-zA-Z])\s*\n\s*(\d+\.?\d*)', r'\1 \2', text)
        # 숫자+단위 바로 뒤 줄바꿈 (한글 앞): "26.1°C\n의" → "26.1°C의"
        text = re.sub(r'(\d+\.?\d*[°%]?C?)\s*\n\s*([가-힣])', r'\1\2', text)

        return text

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

        # 후처리: 줄바꿈 수정
        revised_document = self._fix_line_breaks(revised_document)

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

## 위험도 등급별 권장 조치 기준:
■ E등급: 교체 불필요, 정기 점검 유지
■ O등급: 지속 모니터링 필요, 즉시 교체 불필요
■ X1등급: 1개월 이내 교체 필요
■ X2등급: 10일 이내 교체 필요
■ S등급: 즉시 교체 (당일 교체 원칙)

## 검토 기준:
1. 결함 분석이 정확한가?
2. 위험도 평가(E/O/X1/X2/S)가 적절한가?
3. 권장 조치가 위험도 등급에 맞는 교체 기간을 명시하는가?
4. 규정에 부합하는가?

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

## 지시사항 (필수 준수):

### ★★★ [권장 조치내용] 조치 방법 형식 규칙 ★★★
**모든 조치 항목은 반드시 아래 형식으로 작성:**
```
- [부품명] ([등급], [참조규정ID]): [조치 내용]
```

**필수 규칙:**
1. 모든 부품에 등급(E/O/X1/X2/S)을 반드시 표기
2. 등급은 하나만 표기 (복수 등급 금지: X2/X1 이런 식 금지)
3. [참조규정ID]는 해당 등급 판정에 사용한 규정 시나리오 ID를 표기
4. 신뢰도는 조치 방법에 포함하지 않음
5. 각 항목은 한 줄로 작성

**[상세설명]에 반드시 포함할 내용:**
- 발견된 결함의 구체적 상태 (균열 크기, 마모 정도, 변형 상태 등)
- 해당 결함이 왜 위험한지 (안전 영향, 기능 저하, 사고 위험 등)
- 조치 기한과 그 이유 (왜 10일/1개월/즉시인지)
- 구체적인 조치 방법 (어떻게 교체/보수해야 하는지)
- 추가 권장 사항 (인접 부품 점검, 사후 검사 등)

**올바른 예시 (상세 설명 포함):**
- 레일 훼손 (X2, SCENARIO_rail_1): 레일 표면에 깊이 2mm 이상의 균열이 발견되어 하중 분산 기능 저하 우려. 열차 통과 시 진동으로 균열 확대 가능성이 있으므로 10일 이내 해당 구간 레일 교체 필요.
- FAST clip 훼손 (X1, SCENARIO_rail_1): 체결장치 클립에서 탄성 저하 및 변형 확인. 현재 레일 고정력은 유지되나 장기간 방치 시 레일 이탈 위험. 1개월 이내 동일 규격 클립으로 교체 권장.
- 침목 훼손 (O, SCENARIO_rail_1): 침목 표면에 경미한 마모 흔적 발견. 구조적 강도에는 영향 없으나 향후 열화 진행 가능성 있음. 다음 정기 점검 시 상태 변화 모니터링 필요.
- 조류둥지 (S, SCENARIO_nest_1): 둥지가 전차선 애자와 직접 접촉하여 절연 파괴 및 단락 사고 위험. 즉시 열차 운행 중지 후 둥지 제거 작업 시행.

**잘못된 예시 (절대 금지):**
- 레일 훼손 (X2/X1): ...     ← 복수 등급 금지
- 조류둥지: ...              ← 등급 누락 금지
- 애자 (신뢰도 80.8%): ...   ← 신뢰도 표기 금지
- 레일 (X2): ...             ← 참조규정ID 누락 금지
- 애자 균열 (X2): 10일 이내 교체합니다.  ← 설명 없이 결과만 서술 금지

### 기타 규칙:
1. **교체 시기는 위험도 등급과 일치:**
   - E등급 → "교체 불필요" | O등급 → "즉시 교체 불필요"
   - X1등급 → "1개월 이내 교체" | X2등급 → "10일 이내 교체"
   - S등급 → "즉시 교체 (당일 교체 원칙)"
2. 다른 섹션(일련번호~위험도평가)은 그대로 유지
3. [조치결과]와 [작업이력]은 비워두기
4. **"--" 구분자 사용 금지** (항목은 "- "로 시작, ":"로 연결)

================================================================================
★★★ 출력 형식 규칙 - 줄바꿈 금지 (필수) ★★★
================================================================================
다음 패턴에서는 절대로 줄바꿈하지 마세요. 반드시 한 줄로 이어서 작성하세요:

1. **숫자와 단위는 절대 분리 금지:**
   - (O) "26.1°C" | (X) "26.1\n°C" 또는 "26.\n1°C"
   - (O) "58%" | (X) "58\n%"

2. **괄호 안 내용은 반드시 한 줄:**
   - (O) "(흐림, 26.1°C, 58%)" | (X) "(흐림,\n26.1°C,\n58%)"
   - (O) "(신뢰도 75.6%)" | (X) "(신뢰도\n75.6%)"

3. **신뢰도 표기는 한 덩어리:**
   - (O) "신뢰도 54.9%, 52.0%" | (X) "신뢰도\n54.9%,\n52.0%"

4. **온도/습도 정보는 한 줄:**
   - (O) "현재 날씨는 흐림, 온도는 26.1°C, 습도는 58%로"
   - (X) "현재 날씨는 흐림, 온도는\n26.1°C, 습도는\n58%로"

5. **한글 뒤에 숫자가 오는 경우 줄바꿈 금지:**
   - (O) "온도는 26.1°C" | (X) "온도는\n26.1°C"
   - (O) "습도는 58%" | (X) "습도는\n58%"

6. **문장 중간에서 절대 줄바꿈 금지:**
   - 줄바꿈은 오직 리스트 항목(1., 2., 3., -)의 시작에서만 허용
================================================================================

## 출력 형식:

[일련번호]
(기존 값 유지)

[철도분류]
(기존 값 유지)

[부품명]
(기존 값 유지)

[노선정보]
(기존 값 유지)

[환경정보]
(기존 값 유지)

[결함정보]
(기존 값 유지)

[위험도평가]
위험도 등급: (E/O/X1/X2/S 중 하나만 표기)

[위험도등급 판정근거]
(판정 이유를 상세히 작성)

[참조 규정]
- 규정 시나리오: (참조한 규정 ID와 시나리오 번호, 예: SCENARIO_rail_1, SCENARIO_insulator_2)
- 적용 근거: (해당 규정의 어떤 부분을 적용했는지 간략히 설명)

[권장 조치내용]
1. 교체 시기: (위험도 등급에 맞는 기간)
2. 조치 방법:
- [부품명] ([등급], [참조규정ID]): [조치 내용]
- [부품명] ([등급], [참조규정ID]): [조치 내용]
3. 주의사항: (환경 조건 고려)

⚠️ 중요: 응답은 반드시 [일련번호]부터 시작하세요.
등급 기준, Vision 결과, 규정 내용 등 참고 정보를 절대 응답에 포함하지 마세요.
오직 수정된 보고서 본문만 출력하세요.

"""

        return prompt

    def _clean_revised_document(self, document: str) -> str:
        """수정된 문서 정리"""
        # 마크다운 코드 블록 제거
        document = re.sub(r'```[a-z]*\n?', '', document)
        document = document.strip()

        # ## 철도 시설물 점검 보고서 제목 제거 (있으면)
        document = re.sub(r'^##?\s*철도\s*시설물\s*점검\s*보고서\s*\n*', '', document)

        # [일련번호] 앞의 모든 내용 제거
        match = re.search(r'\[일련번호\]', document)
        if match:
            document = document[match.start():]

        return document.strip()


# 싱글톤 인스턴스
document_reviewer = DocumentReviewer()
