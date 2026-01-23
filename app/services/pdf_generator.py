"""PDF 보고서 생성 서비스"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
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
        title = Paragraph("철도 시설물 점검 보고서", self.styles['KoreanTitle'])
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

        # [필드명] 다음 줄들을 값으로 추출
        pattern = r'\[([^\]]+)\]\s*\n(.*?)(?=\n\[|\n---|\Z)'
        matches = re.findall(pattern, content, re.DOTALL)

        for field_name, value in matches:
            key = field_name.replace(' ', '_').strip()
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
                # 첫 줄이 등급일 수 있음
                first_line = info.strip().split('\n')[0]
                parsed['위험도_등급'] = first_line

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
        if len(text) <= max_length:
            return text

        result = []
        while len(text) > max_length:
            result.append(text[:max_length])
            text = text[max_length:]
        result.append(text)
        return '\n'.join(result)

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
            output_filename = f"batch_report_{timestamp}.pdf"

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
                # 페이지 구분선
                elements.append(Spacer(1, 10*mm))
                elements.append(Paragraph("─" * 50, self.styles['KoreanNormal']))
                elements.append(Spacer(1, 10*mm))

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
        title = Paragraph(f"철도 시설물 점검 보고서", self.styles['KoreanTitle'])
        elements.append(title)
        elements.append(Spacer(1, 3*mm))

        # 파일명
        file_info = Paragraph(f"파일: {image_file}", self.styles['KoreanSmall'])
        elements.append(file_info)
        elements.append(Spacer(1, 5*mm))

        # 문서 내용 파싱
        parsed_data = self._parse_document_content(document_content)

        # Paragraph로 감싸서 자동 줄바꿈 적용
        def make_cell(text, is_header=False):
            if is_header:
                return Paragraph(f"<b>{text}</b>", self.styles['KoreanSmall'])
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

        # 결함 정보 테이블
        defect_data = [
            [make_cell('항목', True), make_cell('내용', True)],
            [make_cell('결함유형'), make_cell(parsed_data.get('결함유형', '-'))],
            [make_cell('결함상태'), make_cell(parsed_data.get('결함상태', '-'))],
            [make_cell('위험도 등급'), make_cell(parsed_data.get('위험도_등급', '-'))],
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

        # 작업이력 테이블 (빈칸으로 유지)
        history_data = [
            [make_cell('항목', True), make_cell('내용', True)],
            [make_cell('조치결과'), make_cell('')],
            [make_cell('작업일자'), make_cell('')],
            [make_cell('작업내용'), make_cell('')],
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
