"""RAILDOCK 챗봇 서비스"""

# import google.generativeai as genai
from google import genai
from google.genai import types
from typing import Dict, Any, List, Optional

from chatbot.config import chatbot_settings
from chatbot.services.report_vector_service import report_vector_service
from app.services.vector_service import vector_service  # 규정 RAG


# ================================================================================
# RAILDOCK 시스템 프롬프트
# ================================================================================
SYSTEM_PROMPT = """당신은 RAILDOCK(레일독), 철도 시설물 점검 보고서 전문 AI 어시스턴트입니다.

【역할】
- 점검 보고서 내용 기반 질의응답
- 위험도 등급(E/O/X1/X2/S) 설명 및 조치 안내
- 결함 현황 요약 및 분석
- 권장 조치사항 안내

【위험도 등급 기준】
┌───────┬─────────────────┬─────────────────────┐
│ 등급  │ 상태           │ 조치 기한           │
├───────┼─────────────────┼─────────────────────┤
│ E     │ 정상           │ 정기 점검 유지      │
│ O     │ 요주의         │ 모니터링 (교체 불필요) │
│ X1    │ 중장기 위험    │ 1개월 이내 교체     │
│ X2    │ 단기 위험      │ 10일 이내 교체      │
│ S     │ 즉시 위험      │ 즉시 교체 (당일)    │
└───────┴─────────────────┴─────────────────────┘

【정보 우선순위】
1순위: 규정 (철도 안전 기준, 시나리오) - 위험도 판정 시 필수
2순위: 점검 보고서 (점검 결과, 결함 현황)
3순위: 웹검색 (일반 기술 정보, 최신 뉴스)

【응답 규칙】
1. 규정/보고서에 있는 정보는 그대로 답변합니다.
2. 위험도 등급 판정은 반드시 규정만 참고합니다. (웹검색 사용 금지)
3. 규정/보고서에 없는 일반 지식은 웹검색 결과를 참고하며, "웹 검색 결과,"로 시작합니다.
4. 위험도 등급은 항상 명확히 표기합니다.
5. 조치 기한은 등급에 맞게 정확히 안내합니다.
6. 간결하고 명확하게 답변합니다.

【답변 형식 예시】

질문: "오늘 점검한 선로 중 위험한 곳이 있어?"
답변:
네, 오늘 점검 결과 중 주의가 필요한 구간이 있습니다.

■ X2등급 (10일 이내 교체 필요)
- 위치: 경부선 KP 125.3
- 결함: 레일 훼손 (신뢰도 78.5%)
- 조치: 훼손된 레일 1개소 10일 이내 교체

■ X1등급 (1개월 이내 교체 필요)
- 위치: 경부선 KP 127.8
- 결함: FAST clip 훼손 2개소
- 조치: 1개월 이내 클립 교체

즉시 조치가 필요한 S등급 결함은 없습니다.

---

질문: "애자 점검 결과 요약해줘"
답변:
오늘 애자 점검 결과 요약입니다.

총 점검: 15건
- E등급 (정상): 10건
- O등급 (요주의): 3건
- X1등급: 1건
- X2등급: 1건
- S등급: 0건

※ X2등급 1건은 균열 발견으로 10일 이내 교체가 필요합니다.
  (위치: 호남선 KP 45.2, 신뢰도 82.3%)

---

질문: "S등급 결함 있어?"
답변:
현재 저장된 보고서 중 S등급(즉시 교체) 결함은 없습니다.

가장 높은 위험도는 X2등급이며, 총 2건입니다:
1. 레일 훼손 - 경부선 KP 125.3
2. 애자 균열 - 호남선 KP 45.2
"""

# ================================================================================
# 일반 안내용 프롬프트 (보고서 없을 때)
# ================================================================================
GENERAL_PROMPT = """당신은 RAILDOCK(레일독), 철도 시설물 점검 전문 AI 어시스턴트입니다.

현재 저장된 점검 보고서가 없습니다. 하지만 철도 시설물 점검에 관한 일반적인 안내는 해드릴 수 있습니다.

【위험도 등급 기준】
┌───────┬─────────────────┬─────────────────────┐
│ 등급  │ 상태           │ 조치 기한           │
├───────┼─────────────────┼─────────────────────┤
│ E     │ 정상           │ 정기 점검 유지      │
│ O     │ 요주의         │ 모니터링 (교체 불필요) │
│ X1    │ 중장기 위험    │ 1개월 이내 교체     │
│ X2    │ 단기 위험      │ 10일 이내 교체      │
│ S     │ 즉시 위험      │ 즉시 교체 (당일)    │
└───────┴─────────────────┴─────────────────────┘

【점검 대상 시설물】
1. 선로(rail): 침목, 레일, 볼트너트, 용접부, 이음매판, 레일체결장치 등
2. 애자(insulator): 애자류, 클램프류, 행거류, 프로텍터류 등
3. 둥지(nest): 조류 둥지로 인한 설비 간섭 위험

【응답 규칙】
1. 점검 결과에 대한 질문은 "현재 저장된 점검 보고서가 없습니다"라고 안내합니다.
2. 위험도 등급, 조치 기준 등 일반적인 질문에는 친절히 답변합니다.
3. 점검 방법, 시스템 사용법에 대해 안내합니다.
4. 철도 관련 일반 지식이 필요한 경우 웹검색 결과를 참고하며, "웹 검색 결과,"로 시작합니다.

【사용자 질문】
{question}

【지시사항】
- 점검 결과 조회 질문이면: "현재 저장된 점검 보고서가 없습니다. /pipeline/process-zip API로 점검을 먼저 진행해주세요." 안내
- 일반 정보 질문이면: 위험도 등급, 조치 기준 등 일반적인 정보 제공
- 친절하고 명확하게 답변
"""


class RaildockChatbot:
    """RAILDOCK 챗봇 서비스"""

    def __init__(self):
        # genai.configure(api_key=chatbot_settings.google_api_key)
        # self.model = genai.GenerativeModel(chatbot_settings.chatbot_model)
        self.client = genai.Client(api_key=chatbot_settings.google_api_key)
        self.model_name = chatbot_settings.chatbot_model

    def ask(
        self,
        question: str,
        folder_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        사용자 질문에 답변

        Args:
            question: 사용자 질문
            folder_filter: 폴더 필터 (rail, insulator, nest)

        Returns:
            답변 및 참조 보고서 정보
        """
        # 1. 관련 규정 검색 (RAG - 최우선 참고)
        regulation_chunks = vector_service.search(
            query=question,
            top_k=3  # 규정은 상위 3개
        )
        regulation_context = self._build_regulation_context(regulation_chunks)
        referenced_regulations = [
            c.get('regulation_id', '') for c in regulation_chunks if c.get('regulation_id')
        ]

        # 2. 관련 보고서 검색
        related_reports = report_vector_service.search(
            query=question,
            top_k=chatbot_settings.report_top_k,
            folder_filter=folder_filter
        )

        # 3. 검색 결과가 없는 경우 - 일반 안내 모드
        if not related_reports:
            return self._ask_general(question)

        # 4. 보고서 컨텍스트 구성
        report_context = self._build_context(related_reports)

        # 5. 프롬프트 구성 (규정 + 보고서)
        prompt = self._build_prompt(question, report_context, regulation_context)

        # 6. Gemini API 호출 (Google Search Retrieval 포함)
        # response = self.model.generate_content(
        #     prompt,
        #     generation_config=genai.types.GenerationConfig(
        #         temperature=0.3,
        #         max_output_tokens=2000
        #     ),
        #     # tools=[{
        #     #     "google_search_retrieval": {
        #     #         "dynamic_retrieval_config": {
        #     #             "mode": "MODE_DYNAMIC",
        #     #             "dynamic_threshold": 0.7  # 높을수록 검색 덜 함 (규정/보고서 우선)
        #     #         }
        #     #     }
        #     # }]
        #     tools=[{
        #         "google_search": {}
        #     }]
        # )
        need_search = any(k in question for k in ["최신", "최근", "뉴스", "버전", "정책", "공식", "가격"])

        tools = [types.Tool(google_search=types.GoogleSearch())] if need_search else None

        config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=2000,
            tools=tools
        )

        resp = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )

        answer_text = resp.text or ""

        # 7. 참조 보고서 정보 정리
        referenced_reports = [
            {
                "report_id": r["report_id"],
                "folder": r["metadata"].get("folder", ""),
                "filename": r["metadata"].get("filename", ""),
                "risk_grade": r["metadata"].get("risk_grade", ""),
                "defect_types": r["metadata"].get("defect_types", "")
            }
            for r in related_reports
        ]

        return {
            # "answer": response.text,
            "answer": answer_text,
            "related_reports": referenced_reports,
            "report_count": len(referenced_reports),
            "referenced_regulations": list(set(referenced_regulations))  # 참조한 규정 ID
        }

    def _ask_general(self, question: str) -> Dict[str, Any]:
        """보고서 없을 때 일반 안내 답변"""
        prompt = GENERAL_PROMPT.format(question=question)

        # response = self.model.generate_content(
        #     prompt,
        #     generation_config=genai.types.GenerationConfig(
        #         temperature=0.3,
        #         max_output_tokens=1500
        #     ),
        #     # tools=[{
        #     #     "google_search_retrieval": {
        #     #         "dynamic_retrieval_config": {
        #     #             "mode": "MODE_DYNAMIC",
        #     #             "dynamic_threshold": 0.7
        #     #         }
        #     #     }
        #     # }]
        #     tools=[{
        #         "google_search": {}
        #     }]
        # )
        need_search = any(k in question for k in ["최신", "최근", "뉴스", "버전", "정책", "공식", "가격"])

        tools = [types.Tool(google_search=types.GoogleSearch())] if need_search else None

        config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=1500,
            tools=tools
        )

        resp = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )

        answer_text = resp.text or ""

        return {
            "answer": answer_text,
            "related_reports": [],
            "report_count": 0,
            "mode": "general"
        }

        # return {
        #     "answer": response.text,
        #     "related_reports": [],
        #     "report_count": 0,
        #     "mode": "general"  # 일반 안내 모드 표시
        # }

    def _build_context(self, reports: List[Dict]) -> str:
        """보고서 컨텍스트 구성"""
        context_parts = []

        for i, report in enumerate(reports, 1):
            meta = report.get("metadata", {})
            content = report.get("content", "")

            context_parts.append(f"""
=== 보고서 {i} ===
- 보고서 ID: {report.get('report_id', '')}
- 유형: {meta.get('folder', '')}
- 파일: {meta.get('filename', '')}
- 위험도: {meta.get('risk_grade', '')}
- 결함: {meta.get('defect_types', '')}
- 점검일시: {meta.get('datetime', '')}

{content}
""")

        return "\n".join(context_parts)

    def _build_regulation_context(self, chunks: List[Dict]) -> str:
        """규정 컨텍스트 구성"""
        if not chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            reg_id = chunk.get('regulation_id', 'Unknown')
            content = chunk.get('content', '')[:1000]  # 최대 1000자
            context_parts.append(f"""
=== 규정 {i}: [{reg_id}] ===
{content}
""")

        return "\n".join(context_parts)

    def _build_prompt(self, question: str, report_context: str, regulation_context: str = "") -> str:
        """프롬프트 구성"""
        prompt = f"""{SYSTEM_PROMPT}

================================================================================
【관련 규정 (최우선 참고)】
================================================================================
{regulation_context if regulation_context else "(규정 검색 결과 없음)"}

================================================================================
【검색된 점검 보고서】
================================================================================
{report_context}

================================================================================
【사용자 질문】
{question}

================================================================================
【지시사항】
1. 위 규정을 최우선으로 참고하여 답변하세요.
2. 점검 보고서 내용을 기반으로 답변하세요.
3. 보고서에 없는 내용은 답변하지 마세요.
4. 위험도 등급 판정 시 어떤 규정(시나리오 번호)을 참고했는지 명시하세요.
"""
        return prompt

    def get_summary(self) -> Dict[str, Any]:
        """전체 보고서 요약"""
        stats = report_vector_service.get_stats()
        reports = report_vector_service.get_all_reports(limit=100)

        # 등급별 통계
        grade_stats = {"E": 0, "O": 0, "X1": 0, "X2": 0, "S": 0, "Unknown": 0}
        for report in reports:
            grade = report.get("risk_grade", "Unknown")
            if grade in grade_stats:
                grade_stats[grade] += 1
            else:
                grade_stats["Unknown"] += 1

        return {
            "total_reports": stats["total_reports"],
            "by_folder": stats["by_folder"],
            "by_grade": grade_stats
        }


# 싱글톤 인스턴스
raildock_chatbot = RaildockChatbot()
