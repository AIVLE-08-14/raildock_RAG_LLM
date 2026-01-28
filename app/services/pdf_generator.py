"""PDF 보고서 생성 서비스"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class PDFGenerator:
    """점검 보고서 PDF 생성"""

    def __init__(self):
        self.output_dir = Path("./data/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 한글 폰트 등록
        self._register_korean_font()

        # 스타일 설정
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _register_korean_font(self):
        """한글 폰트 등록"""
        # Windows 기본 한글 폰트 경로들
        font_paths = [
            "C:/Windows/Fonts/malgun.ttf",      # 맑은 고딕
            "C:/Windows/Fonts/gulim.ttc",       # 굴림
            "C:/Windows/Fonts/batang.ttc",      # 바탕
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Linux
        ]

        font_registered = False
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('Korean', font_path))
                    font_registered = True
                    self.korean_font = 'Korean'
                    break
                except Exception as e:
                    continue

        if not font_registered:
            # 기본 폰트 사용 (한글 깨질 수 있음)
            self.korean_font = 'Helvetica'
            print("경고: 한글 폰트를 찾을 수 없습니다. 한글이 깨질 수 있습니다.")

    def _setup_styles(self):
        """스타일 설정"""
        self.styles.add(ParagraphStyle(
            name='KoreanTitle',
            fontName=self.korean_font,
            fontSize=16,
            leading=20,
            alignment=1,  # 가운데 정렬
            spaceAfter=10
        ))

        self.styles.add(ParagraphStyle(
            name='KoreanNormal',
            fontName=self.korean_font,
            fontSize=10,
            leading=14,
            spaceAfter=6
        ))

        self.styles.add(ParagraphStyle(
            name='KoreanSmall',
            fontName=self.korean_font,
            fontSize=8,
            leading=10
        ))

    def generate_report(
        self,
        document_content: str,
        vision_result: Dict[str, Any],
        review_result: Dict[str, Any] = None,
        image_path: str = None,
        output_filename: str = None
    ) -> str:
        """
        점검 보고서 PDF 생성

        Args:
            document_content: 생성된 문서 내용
            vision_result: Vision AI 결과
            review_result: 검토 결과 (선택)
            image_path: 이미지 경로 (선택)
            output_filename: 출력 파일명 (선택)

        Returns:
            생성된 PDF 파일 경로
        """
        # 파일명 생성
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_file = vision_result.get('image_file', 'unknown')
            base_name = Path(image_file).stem
            output_filename = f"report_{base_name}_{timestamp}.pdf"

        output_path = self.output_dir / output_filename

        # PDF 문서 생성
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )

        # 컨텐츠 구성
        elements = []

        # 제목
        title = Paragraph("철도 시설물 탐지 보고서", self.styles['KoreanTitle'])
        elements.append(title)
        elements.append(Spacer(1, 10*mm))

        # 문서 내용을 파싱해서 테이블로 구성
        parsed_data = self._parse_document_content(document_content)

        # 기본 정보 테이블
        info_data = [
            ['항목', '내용'],
            ['일련번호', parsed_data.get('일련번호', '-')],
            ['철도분류', parsed_data.get('철도분류', '-')],
            ['부품명', parsed_data.get('부품명', '-')],
            ['노선', parsed_data.get('노선', '-')],
            ['위치', parsed_data.get('위치', '-')],
        ]

        info_table = Table(info_data, colWidths=[40*mm, 120*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, 0), colors.grey),
            ('BACKGROUND', (1, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 5*mm))

        # 결함 정보 테이블
        defect_data = [
            ['항목', '내용'],
            ['결함유형', parsed_data.get('결함유형', '-')],
            ['결함상태', self._wrap_text(parsed_data.get('결함상태', '-'), 80)],
            ['위험도 등급', parsed_data.get('위험도_등급', '-')],
            ['위험도등급 판정근거', self._wrap_text(parsed_data.get('판정근거', '-'), 80)],
        ]

        defect_table = Table(defect_data, colWidths=[40*mm, 120*mm])
        defect_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, 0), colors.grey),
            ('BACKGROUND', (1, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(defect_table)
        elements.append(Spacer(1, 5*mm))

        # 권장 조치내용
        action_text = parsed_data.get('권장_조치내용', '-')
        if action_text and action_text != '-':
            action_text = self._format_action_text(action_text)
        action_paragraph = Paragraph(
            f"<b>권장 조치내용:</b><br/>{action_text}",
            self.styles['KoreanNormal']
        )
        elements.append(action_paragraph)
        elements.append(Spacer(1, 5*mm))

        # 검토 결과 (있는 경우)
        if review_result:
            review_section = Paragraph(
                f"<b>검토 결과:</b> {'적합' if review_result.get('is_valid') else '부적합'}<br/>"
                f"<b>피드백:</b> {review_result.get('feedback', '-')}",
                self.styles['KoreanNormal']
            )
            elements.append(review_section)
            elements.append(Spacer(1, 5*mm))

        # 이미지 (있는 경우)
        if image_path and os.path.exists(image_path):
            try:
                img = Image(image_path, width=150*mm, height=100*mm)
                elements.append(Paragraph("<b>탐지 이미지:</b>", self.styles['KoreanNormal']))
                elements.append(Spacer(1, 2*mm))
                elements.append(img)
            except Exception as e:
                print(f"이미지 추가 실패: {e}")

        # 작업이력
        history_data = [
            ['항목', '내용'],
            ['조치결과', parsed_data.get('조치결과', '미조치')],
            ['작업일자', parsed_data.get('작업일자', '-')],
            ['작업내용', parsed_data.get('작업내용', '-')],
        ]

        history_table = Table(history_data, colWidths=[40*mm, 120*mm])
        history_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, 0), colors.grey),
            ('BACKGROUND', (1, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(Spacer(1, 5*mm))
        elements.append(history_table)

        # PDF 생성
        doc.build(elements)

        return str(output_path)

    def _parse_document_content(self, content: str) -> Dict[str, str]:
        """문서 내용 파싱"""
        parsed = {}

        # 정규식으로 [필드명] 패턴 파싱
        import re

        # 먼저 --- 구분자와 _ 반복 패턴 제거 (모든 위치에서)
        content = re.sub(r'-{3,}', '', content)   # --- 제거 (어디서든)
        content = re.sub(r'_{3,}', '', content)   # ___ 제거 (어디서든)
        content = re.sub(r'─{3,}', '', content)   # ─── 제거 (박스 문자)
        content = re.sub(r'━{3,}', '', content)   # ━━━ 제거 (굵은 선)
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # 연속 빈줄 정리

        # [필드명] 다음 줄들을 값으로 추출 (줄바꿈이 없어도 처리)
        # 패턴 1: [필드명]\n내용
        pattern1 = r'\[([^\]]+)\]\s*\n(.*?)(?=\n\[|\Z)'
        matches = re.findall(pattern1, content, re.DOTALL)

        for field_name, value in matches:
            key = field_name.replace(' ', '_').strip()
            parsed[key] = value.strip()

        # 패턴 2: [필드명]내용 (줄바꿈 없이 바로 이어지는 경우)
        pattern2 = r'\[([^\]]+)\]([^\[\n]+)'
        matches2 = re.findall(pattern2, content)
        for field_name, value in matches2:
            key = field_name.replace(' ', '_').strip()
            if key not in parsed or not parsed[key]:  # 기존 값이 없거나 빈 경우만
                parsed[key] = value.strip()

        # 노선정보 내부의 노선/위치 추출
        if '노선정보' in parsed:
            info = parsed['노선정보']
            if '노선:' in info:
                노선_match = re.search(r'노선:\s*(.+?)(?:\n|$)', info)
                if 노선_match:
                    parsed['노선'] = 노선_match.group(1).strip()
            if '위치:' in info:
                위치_match = re.search(r'위치:\s*(.+?)(?:\n|$)', info)
                if 위치_match:
                    parsed['위치'] = 위치_match.group(1).strip()

        # 환경정보 내부 추출 (다음 필드명 전까지만 추출)
        if '환경정보' in parsed:
            info = parsed['환경정보']
            # 각 필드를 다음 필드명 전까지만 추출
            fields = ['지역', '촬영일시', '날씨', '온도', '습도']
            for field in fields:
                # 다음 필드들의 패턴 생성 (현재 필드 이후의 모든 필드)
                next_fields = '|'.join([f'{f}:' for f in fields if f != field])
                if next_fields:
                    pattern = rf'{field}:\s*(.+?)(?={next_fields}|\n|$)'
                else:
                    pattern = rf'{field}:\s*(.+?)(?:\n|$)'
                match = re.search(pattern, info)
                if match:
                    parsed[field] = match.group(1).strip()

        # 결함정보 내부 추출
        if '결함정보' in parsed:
            info = parsed['결함정보']
            if '결함유형:' in info:
                match = re.search(r'결함유형:\s*(.+?)(?:\n|$)', info)
                if match:
                    parsed['결함유형'] = match.group(1).strip()
            if '결함상태:' in info:
                match = re.search(r'결함상태:\s*(.+?)(?:\n\n|\n결함유형|\Z)', info, re.DOTALL)
                if match:
                    parsed['결함상태'] = match.group(1).strip()

        # 위험도평가 내부 추출
        if '위험도평가' in parsed:
            info = parsed['위험도평가']
            if '위험도 등급:' in info:
                match = re.search(r'위험도 등급:\s*(.+?)(?:\n|$)', info)
                if match:
                    parsed['위험도_등급'] = match.group(1).strip()
            elif info.strip():
                # 첫 줄이 등급일 수 있음 (E, O, X1, X2, S 패턴)
                first_line = info.strip().split('\n')[0].strip()
                # 등급 패턴 매칭
                grade_match = re.search(r'^(E|O|X1|X2|S)(?:\s|$)', first_line)
                if grade_match:
                    parsed['위험도_등급'] = grade_match.group(1)
                else:
                    parsed['위험도_등급'] = first_line

        # 위험도등급 판정근거 추출 (여러 형식 지원)
        if '위험도등급_판정근거' in parsed and parsed['위험도등급_판정근거'].strip():
            parsed['판정근거'] = parsed['위험도등급_판정근거'].strip()
        # 다른 키 이름으로 저장됐을 수 있음
        if '판정근거' not in parsed or not parsed.get('판정근거'):
            for key in ['위험도_등급_판정근거', '판정_근거', '위험도등급판정근거']:
                if key in parsed and parsed[key].strip():
                    parsed['판정근거'] = parsed[key].strip()
                    break
        # 위험도평가 내부에서 추출 시도
        if ('판정근거' not in parsed or not parsed.get('판정근거')) and '위험도평가' in parsed:
            info = parsed['위험도평가']
            if '판정 근거:' in info or '판정근거:' in info:
                match = re.search(r'판정\s*근거:\s*(.+?)(?:\n\[|\Z)', info, re.DOTALL)
                if match:
                    parsed['판정근거'] = match.group(1).strip()

        # 참조 규정 추출 (여러 형식 지원)
        if '참조_규정' in parsed and parsed['참조_규정'].strip():
            pass  # 이미 있음
        else:
            for key in ['참조규정', '참조_규정', '참고_규정', '참고규정']:
                if key in parsed and parsed[key].strip():
                    parsed['참조_규정'] = parsed[key].strip()
                    break

        # 작업이력 내부 추출
        if '작업이력' in parsed:
            info = parsed['작업이력']
            if '작업일자:' in info:
                match = re.search(r'작업일자:\s*(.+?)(?:\n|$)', info)
                if match:
                    parsed['작업일자'] = match.group(1).strip()
            if '작업내용:' in info:
                match = re.search(r'작업내용:\s*(.+?)(?:\n|$)', info)
                if match:
                    parsed['작업내용'] = match.group(1).strip()

        return parsed

    def _wrap_text(self, text: str, max_length: int) -> str:
        """긴 텍스트 줄바꿈"""
        # 먼저 잘못된 줄바꿈 수정
        text = self._fix_line_breaks(text)

        if len(text) <= max_length:
            return text

        result = []
        while len(text) > max_length:
            result.append(text[:max_length])
            text = text[max_length:]
        result.append(text)
        return '\n'.join(result)

    def _fix_line_breaks(self, text: str) -> str:
        """숫자/퍼센트 관련 잘못된 줄바꿈 수정 (PDF용) - 최강화 버전"""
        import re

        if not text:
            return text

        # ===== 0단계: 줄바꿈 정규화 =====
        # Windows 줄바꿈(\r\n) → Unix 줄바꿈(\n)
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        # 연속된 줄바꿈 정리 (2개 이상 → 1개)
        text = re.sub(r'\n{2,}', '\n', text)

        # ===== 1단계: 괄호 안 모든 줄바꿈 제거 (가장 먼저!) =====
        def fix_paren(m):
            return re.sub(r'\s*\n+\s*', ' ', m.group(0))
        for _ in range(10):
            prev = text
            text = re.sub(r'\([^)]*\n[^)]*\)', fix_paren, text)
            if prev == text:
                break

        # ===== 2단계: 숫자 중간 줄바꿈 =====
        text = re.sub(r'(\d+)\.\s*\n\s*(\d+)', r'\1.\2', text)

        # ===== 3단계: 신뢰도 관련 =====
        text = re.sub(r'신뢰도\s*\n+\s*(\d)', r'신뢰도 \1', text)

        # ===== 4단계: 퍼센트+쉼표 뒤 줄바꿈 =====
        text = re.sub(r'(\d+\.?\d*%)\s*,\s*\n+\s*(\d)', r'\1, \2', text)

        # ===== 5단계: 한글+쉼표 뒤 줄바꿈 =====
        text = re.sub(r'([가-힣]),\s*\n+\s*(\d)', r'\1, \2', text)

        # ===== 6단계: 온도/습도 특수 패턴 =====
        # "온도는\n26.1" → "온도는 26.1" (명시적)
        text = re.sub(r'온도는?\s*\n+\s*(\d)', r'온도는 \1', text)
        # "습도는\n58" → "습도는 58" (명시적)
        text = re.sub(r'습도는?\s*\n+\s*(\d)', r'습도는 \1', text)
        # "26.1°C,\n58%" → "26.1°C, 58%"
        text = re.sub(r'(\d+\.?\d*°C)\s*,\s*\n+\s*(\d)', r'\1, \2', text)
        # "26.1\n°C" → "26.1°C"
        text = re.sub(r'(\d+\.?\d*)\s*\n+\s*(°C)', r'\1\2', text)

        # ===== 7단계: 한글 뒤 줄바꿈 + 숫자 (일반) =====
        # "~는\n26" → "~는 26"
        text = re.sub(r'([가-힣])\s*\n+\s*(\d)', r'\1 \2', text)

        # ===== 8단계: 숫자+단위 뒤 줄바꿈 + 한글 =====
        text = re.sub(r'(\d+\.?\d*°C)\s*\n+\s*([가-힣])', r'\1\2', text)
        text = re.sub(r'(\d+\.?\d*%)\s*\n+\s*([가-힣])', r'\1\2', text)
        text = re.sub(r'(\d+\.?\d*)\s*\n+\s*([가-힣])', r'\1\2', text)

        # ===== 9단계: 닫는 괄호 관련 =====
        text = re.sub(r'\)\s*\n+\s*([가-힣])', r')\1', text)
        text = re.sub(r'\)\s*\n+\s*(은|는|이|가|을|를|의|에|와|과)', r')\1', text)

        # ===== 10단계: 콜론 뒤 줄바꿈 =====
        text = re.sub(r':\s*\n+\s*([가-힣])', r': \1', text)

        # ===== 11단계: 쉼표 뒤 줄바꿈 =====
        text = re.sub(r',\s*\n+\s*(\d)', r', \1', text)
        text = re.sub(r',\s*\n+\s*([가-힣])', r', \1', text)

        # ===== 12단계: 핵 옵션 - 문장 중간 줄바꿈 제거 =====
        # 번호(1. 2. 3.)나 대시(-) 항목이 아닌 줄바꿈은 공백으로 변환
        # 줄바꿈 뒤에 숫자+점(1.)이나 대시(-)가 아니면 공백으로 변환
        text = re.sub(r'\n(?!\d+\.\s)(?!-\s)(?!$)', ' ', text)

        # ===== 13단계: 최종 정리 =====
        text = re.sub(r'  +', ' ', text)

        return text

    def _format_action_text(self, text: str) -> str:
        """권장 조치내용 텍스트 포맷팅 - 완전 재작성"""
        import re

        if not text:
            return text

        # ===== 1단계: 모든 줄바꿈 정규화 =====
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        text = text.replace('\u2028', '\n')  # Line Separator
        text = text.replace('\u2029', '\n')  # Paragraph Separator
        text = text.replace('\u0085', '\n')  # NEL

        # ===== 2단계: -- 패턴 제거 =====
        text = re.sub(r'--([^-]+)--', r'\1', text)
        text = re.sub(r'--+', '', text)

        # ===== 3단계: * 기호를 - 기호로 통일 =====
        text = text.replace('*', '-')

        # ===== 4단계: 리스트 항목 마커 임시 보호 =====
        # "1. ", "2. ", "- " 패턴을 임시 마커로 변환
        text = re.sub(r'^(\d+\.)\s+', r'###LISTNUM\1### ', text)  # 맨 앞
        text = re.sub(r'\n(\d+\.)\s+', r'\n###LISTNUM\1### ', text)  # 줄바꿈 뒤
        # ** 중요: 공백 뒤에 오는 번호 항목도 처리 (LLM이 줄바꿈 없이 출력할 때 대응) **
        text = re.sub(r' (\d+\.)\s+', r' ###LISTNUM\1### ', text)  # 공백 뒤 번호
        text = re.sub(r'^-\s+', r'###DASH### ', text)  # 맨 앞 대시
        text = re.sub(r'\n-\s+', r'\n###DASH### ', text)  # 줄바꿈 뒤 대시

        # ===== 5단계: 모든 줄바꿈을 공백으로 변환 =====
        text = re.sub(r'\s*\n+\s*', ' ', text)

        # ===== 6단계: 마커 복원하면서 <br/> 추가 =====
        text = re.sub(r'###LISTNUM(\d+\.)###', r'<br/>\1', text)
        text = re.sub(r'###DASH###', r'<br/>-', text)

        # ===== 7단계: 연속 공백 정리 =====
        text = re.sub(r'  +', ' ', text)

        # ===== 8단계: 연속된 <br/> 정리 =====
        text = re.sub(r'(<br/>)+', '<br/>', text)

        # ===== 9단계: 맨 앞 <br/> 제거 =====
        text = re.sub(r'^<br/>', '', text)

        return text.strip()

    def _format_defect_status(self, text: str) -> str:
        """결함상태 텍스트 포맷팅 - 완전 재작성"""
        import re

        if not text or text == '-':
            return text

        # ===== 1단계: 모든 줄바꿈 정규화 =====
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        text = text.replace('\u2028', '\n')
        text = text.replace('\u2029', '\n')
        text = text.replace('\u0085', '\n')

        # ===== 2단계: 대시 항목 마커 임시 보호 =====
        text = re.sub(r'^-\s+', r'###DASH### ', text)
        text = re.sub(r'\n-\s+', r'\n###DASH### ', text)

        # ===== 3단계: 모든 줄바꿈을 공백으로 변환 =====
        text = re.sub(r'\s*\n+\s*', ' ', text)

        # ===== 4단계: 마커 복원하면서 <br/> 추가 =====
        text = re.sub(r'###DASH###', r'<br/>-', text)

        # ===== 5단계: 문장 끝 + 대시 패턴 처리 =====
        text = re.sub(r'([다니요]\.)\s*-\s+', r'\1<br/>- ', text)

        # ===== 6단계: 연속 공백 및 <br/> 정리 =====
        text = re.sub(r'  +', ' ', text)
        text = re.sub(r'(<br/>)+', '<br/>', text)
        text = re.sub(r'^<br/>', '', text)

        return text.strip()

    def generate_batch_report(
        self,
        reports: List[Dict[str, Any]],
        output_filename: str = None
    ) -> str:
        """
        여러 보고서를 하나의 PDF로 생성

        Args:
            reports: 보고서 리스트 [{document_content, vision_result, review_result, image_path}, ...]
            output_filename: 출력 파일명

        Returns:
            생성된 PDF 파일 경로
        """
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"rail_report_{timestamp}.pdf"

        output_path = self.output_dir / output_filename

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )

        elements = []

        for i, report in enumerate(reports):
            if i > 0:
                # 새 페이지에서 시작
                elements.append(PageBreak())

            # 개별 보고서 요소 추가
            report_elements = self._generate_single_report_elements(
                report.get('document_content', ''),
                report.get('vision_result', {}),
                report.get('review_result'),
                report.get('image_path')
            )
            elements.extend(report_elements)

        doc.build(elements)
        return str(output_path)

    def _generate_single_report_elements(
        self,
        document_content: str,
        vision_result: Dict[str, Any],
        review_result: Dict[str, Any] = None,
        image_path: str = None
    ) -> list:
        """단일 보고서 요소 생성 (내부용)"""
        elements = []

        # 제목
        image_file = vision_result.get('image_file', 'unknown')
        title = Paragraph(f"철도 시설물 탐지 보고서", self.styles['KoreanTitle'])
        elements.append(title)
        elements.append(Spacer(1, 3*mm))

        # 파일명
        file_info = Paragraph(f"파일: {image_file}", self.styles['KoreanSmall'])
        elements.append(file_info)
        elements.append(Spacer(1, 5*mm))

        # 문서 내용 파싱
        parsed_data = self._parse_document_content(document_content)

        # Paragraph로 감싸서 자동 줄바꿈 적용
        def make_cell(text, is_header=False, allow_blank=False):
            if is_header:
                return Paragraph(f"<b>{text}</b>", self.styles['KoreanSmall'])
            if allow_blank:
                return Paragraph(str(text) if text else '', self.styles['KoreanSmall'])
            return Paragraph(str(text) if text else '-', self.styles['KoreanSmall'])

        # 기본 정보 테이블 (2열 레이아웃)
        info_data = [
            [make_cell('항목', True), make_cell('내용', True)],
            [make_cell('일련번호'), make_cell(parsed_data.get('일련번호', '-'))],
            [make_cell('철도분류'), make_cell(parsed_data.get('철도분류', '-'))],
            [make_cell('부품명'), make_cell(parsed_data.get('부품명', '-'))],
            [make_cell('노선'), make_cell(parsed_data.get('노선', '-'))],
            [make_cell('위치'), make_cell(parsed_data.get('위치', '-'))],
        ]

        info_table = Table(info_data, colWidths=[35*mm, 130*mm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 5*mm))

        # 환경정보 테이블 (메타데이터)
        env_data = [
            [make_cell('환경정보', True), make_cell('값', True)],
            [make_cell('지역'), make_cell(parsed_data.get('지역', '-'))],
            [make_cell('촬영일시'), make_cell(parsed_data.get('촬영일시', '-'))],
            [make_cell('날씨'), make_cell(parsed_data.get('날씨', '-'))],
            [make_cell('온도'), make_cell(parsed_data.get('온도', '-'))],
            [make_cell('습도'), make_cell(parsed_data.get('습도', '-'))],
        ]

        env_table = Table(env_data, colWidths=[35*mm, 130*mm])
        env_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(env_table)
        elements.append(Spacer(1, 5*mm))

        # 결함 정보 테이블
        # 결함상태는 "-"로 시작하는 각 항목을 줄바꿈 처리
        defect_status_text = parsed_data.get('결함상태', '-')
        defect_status_formatted = self._format_defect_status(defect_status_text)

        # 판정근거 포맷팅
        judgment_reason = parsed_data.get('판정근거', '-')
        if judgment_reason and judgment_reason != '-':
            judgment_reason = self._fix_line_breaks(judgment_reason)
            judgment_reason = judgment_reason.replace('\n', '<br/>')

        # 참조 규정 포맷팅
        ref_regulation = parsed_data.get('참조_규정', '-')
        if ref_regulation and ref_regulation != '-':
            ref_regulation = self._fix_line_breaks(ref_regulation)
            ref_regulation = ref_regulation.replace('\n', '<br/>')

        defect_data = [
            [make_cell('항목', True), make_cell('내용', True)],
            [make_cell('결함유형'), make_cell(parsed_data.get('결함유형', '-'))],
            [make_cell('결함상태'), Paragraph(defect_status_formatted, self.styles['KoreanSmall'])],
            [make_cell('위험도 등급'), make_cell(parsed_data.get('위험도_등급', '-'))],
            [make_cell('위험도등급 판정근거'), Paragraph(judgment_reason, self.styles['KoreanSmall'])],
            [make_cell('참조 규정'), Paragraph(ref_regulation, self.styles['KoreanSmall'])],
        ]

        defect_table = Table(defect_data, colWidths=[35*mm, 130*mm])
        defect_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(defect_table)
        elements.append(Spacer(1, 5*mm))

        # 권장 조치내용
        action_text = parsed_data.get('권장_조치내용', '-')
        if action_text and action_text != '-':
            # 텍스트 포맷팅 적용
            action_text = self._format_action_text(action_text)
            action_paragraph = Paragraph(
                f"<b>권장 조치내용:</b><br/>{action_text}",
                self.styles['KoreanNormal']
            )
            elements.append(action_paragraph)
            elements.append(Spacer(1, 5*mm))

        # 이미지 (있는 경우)
        if image_path and os.path.exists(image_path):
            try:
                img = Image(image_path, width=140*mm, height=90*mm)
                elements.append(Paragraph("<b>탐지 이미지:</b>", self.styles['KoreanNormal']))
                elements.append(Spacer(1, 2*mm))
                elements.append(img)
                elements.append(Spacer(1, 5*mm))
            except Exception as e:
                print(f"이미지 추가 실패: {e}")

        # 작업이력 테이블 (내용은 완전히 빈칸)
        history_data = [
            [make_cell('항목', True), make_cell('내용', True)],
            [make_cell('조치결과'), make_cell('', allow_blank=True)],
            [make_cell('작업일자'), make_cell('', allow_blank=True)],
            [make_cell('작업내용'), make_cell('', allow_blank=True)],
        ]

        history_table = Table(history_data, colWidths=[35*mm, 130*mm])
        history_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(history_table)

        return elements


# 싱글톤 인스턴스
pdf_generator = PDFGenerator()
