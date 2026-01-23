"""규정 문서 청킹 유틸리티"""

import re
from typing import List, Dict


class RegulationChunker:
    """
    [규정 ID] 단위로 문서를 청킹하는 클래스

    - 분리 기준: [규정 ID]: RAIL-MNT-XXX 패턴
    - 청크 크기: 500자 (기본)
    - 오버랩: 200자 (기본)
    """

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 200,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        # [규정 ID]: RAIL-MNT-XXX 패턴
        self.regulation_pattern = re.compile(r'(\[규정 ID\]:\s*[\w-]+)')

    def chunk(self, text: str) -> List[Dict]:
        """
        문서를 [규정 ID] 단위로 청킹

        Args:
            text: 전체 규정 문서 텍스트

        Returns:
            청크 리스트 [{regulation_id, content, chunk_index}, ...]
        """
        # 1. [규정 ID]: 패턴으로 분리
        parts = self.regulation_pattern.split(text)

        # 2. 규정별로 묶기
        regulations = []
        i = 1
        while i < len(parts):
            reg_id_line = parts[i].strip()  # [규정 ID]: RAIL-MNT-XXX
            content = parts[i + 1] if i + 1 < len(parts) else ""

            # 규정 ID 추출 (RAIL-MNT-XXX 부분)
            reg_id = reg_id_line.replace("[규정 ID]:", "").strip()

            full_content = f"{reg_id_line}\n{content}".strip()

            regulations.append({
                "regulation_id": reg_id,
                "content": full_content
            })
            i += 2

        # 3. 오버랩 적용
        chunks = self._apply_overlap(regulations)

        return chunks

    def _apply_overlap(self, regulations: List[Dict]) -> List[Dict]:
        """청크 간 오버랩 적용"""
        chunks = []

        for idx, reg in enumerate(regulations):
            content = reg["content"]

            # 이전 규정의 마지막 N자 추가 (앞 오버랩)
            if idx > 0:
                prev_content = regulations[idx - 1]["content"]
                overlap_text = prev_content[-self.overlap:]
                content = f"...{overlap_text}\n\n{content}"

            # 다음 규정의 처음 N자 추가 (뒤 오버랩)
            if idx < len(regulations) - 1:
                next_content = regulations[idx + 1]["content"]
                overlap_text = next_content[:self.overlap]
                content = f"{content}\n\n{overlap_text}..."

            chunks.append({
                "regulation_id": reg["regulation_id"],
                "content": content,
                "chunk_index": idx,
                "total_chunks": len(regulations)
            })

        return chunks

    def extract_metadata(self, chunk_content: str) -> Dict:
        """
        청크에서 메타데이터 동적 추출

        모든 [필드명]: 값 패턴을 자동으로 파싱
        - [점검 대상]: → 점검_대상
        - [결함 등급]: → 결함_등급
        - [전기 안전 조치]: → 전기_안전_조치
        등 어떤 필드든 추출 가능
        """
        metadata = {}

        # 모든 [필드명]: 값 패턴을 동적으로 찾기
        # (?=\n\[|\n\n|$) : 다음 필드, 빈 줄, 또는 끝까지
        pattern = r'\[([^\]]+)\]:\s*(.+?)(?=\n\[|\n\n|$)'
        matches = re.findall(pattern, chunk_content, re.DOTALL)

        for field_name, value in matches:
            # 필드명에서 공백을 언더스코어로 변환
            key = field_name.replace(" ", "_")
            # 규정 ID는 별도 처리되므로 제외
            if key != "규정_ID":
                metadata[key] = value.strip()

        return metadata
