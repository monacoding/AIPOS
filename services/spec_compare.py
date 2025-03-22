import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # PyMuPDF
import re
from rapidfuzz import process, fuzz
from database import get_standard_spec_paragraphs
from difflib import ndiff

def extract_text_from_pdf(pdf_path):
    """PDF에서 전체 텍스트 추출"""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text("text") + "\n"
    except Exception as e:
        print(f"❌ PDF 읽기 오류: {e}")
        return None
    return text

def split_into_paragraphs(text):
    """빈 줄 기준으로 문단 분리"""
    return [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]

def group_by_section(paragraphs):
    """문단들을 섹션 단위로 묶기"""
    sections = []
    current_section = None
    section_paragraphs = []
    section_pattern = re.compile(r'^\d+\.\d+(\.\d+)?\s+.+$')  # 예: 5.6, 5.6.1 등

    for para in paragraphs:
        if section_pattern.match(para):
            if current_section:
                sections.append((current_section, section_paragraphs))
            current_section = para.strip()
            section_paragraphs = []
        else:
            section_paragraphs.append(para.strip())

    if current_section:
        sections.append((current_section, section_paragraphs))

    return sections if sections else [(None, paragraphs)]

def highlight_diff(std_text, proj_text):
    """ndiff로 변경된 부분 강조 (빨간색 + 볼드)"""
    std_text_token = std_text.replace('\n', ' <NEWLINE> ')
    proj_text_token = proj_text.replace('\n', ' <NEWLINE> ')

    diff = list(ndiff(std_text_token.split(), proj_text_token.split()))
    highlighted_text = []

    for token in diff:
        sign = token[:2]
        word = token[2:]

        if word == '<NEWLINE>':
            highlighted_text.append("<br>")
        elif sign == '+ ':
            highlighted_text.append(f"<span style='color:red; font-weight:bold'>{word}</span>")
        elif sign == '- ':
            continue  # 삭제는 표준 쪽에만 반영할 거니까 여긴 무시
        else:
            highlighted_text.append(word)

    return " ".join(highlighted_text).replace(' <br> ', '<br>')

def compare_project_spec_with_standard(ship_type, proj_pdf_path, similarity_threshold=70):
    """
    프로젝트 사양서 PDF를 표준 사양서(DB)와 비교하여 차이점 리스트 반환
    """
    std_specs = get_standard_spec_paragraphs(ship_type)
    std_paragraphs = [(s.section or "No Section", s.paragraph) for s in std_specs]

    if not std_paragraphs:
        print(f"⚠️ DB에 등록된 표준 사양서 문단이 없습니다: ship_type = {ship_type}")
        return []

    proj_text = extract_text_from_pdf(proj_pdf_path)
    if not proj_text:
        return []

    proj_paragraphs = split_into_paragraphs(proj_text)
    proj_sections = group_by_section(proj_paragraphs)

    differences = []

    for proj_section, proj_paras in proj_sections:
        for proj_para in proj_paras:
            choices = [p for _, p in std_paragraphs]
            if not choices:
                continue

            match_result = process.extractOne(
                proj_para,
                choices,
                scorer=fuzz.ratio
            )

            if not match_result:
                continue

            match, score, idx = match_result

            if score >= similarity_threshold:
                std_section, std_para = std_paragraphs[idx]
                diff_html = highlight_diff(std_para, proj_para)
                if std_para.strip() != proj_para.strip():
                    differences.append({
                        "section": std_section,
                        "표준 사양서": std_para,
                        "프로젝트 사양서": proj_para,
                        "비교 결과": diff_html
                    })
            else:
                differences.append({
                    "section": proj_section,
                    "표준 사양서": "",
                    "프로젝트 사양서": proj_para,
                    "비교 결과": f"<span style='color:red; font-weight:bold'>{proj_para}</span>"
                })

    return differences

if __name__ == "__main__":
    ship_type = "174K LNGC"
    test_pdf_path = "/Users/gimtaehyeong/Desktop/코딩/개발/AIPOS/DB/SPEC/STD_SPEC_4.pdf"

    print("🚀 테스트 시작")

    if not os.path.exists(test_pdf_path):
        print(f"❌ PDF 경로 존재하지 않음: {test_pdf_path}")
    else:
        print(f"📄 PDF 존재 확인: {test_pdf_path}")

    results = compare_project_spec_with_standard(ship_type, test_pdf_path)

    if not results:
        print("⚠️ 비교 결과가 없습니다. DB에 표준 사양서가 없거나, 유사도가 낮아 매칭이 안 됐을 수 있습니다.")
    else:
        print(f"🔍 비교된 항목 수: {len(results)}")
        for i, diff in enumerate(results[:5], 1):
            print(f"\n[{i}] 섹션: {diff['section']}")
            print(f"📘 표준: {diff['표준 사양서']}")
            print(f"📕 프로젝트: {diff['프로젝트 사양서']}")
            print(f"📌 비교 결과: {diff['비교 결과'][:80]}...")
