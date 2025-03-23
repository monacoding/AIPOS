import os
import fitz  # PyMuPDF
from difflib import SequenceMatcher
from database import SessionLocal, POSParagraph, POSFile, POS_FOLDER

DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "download")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def normalize_text(text):
    return ' '.join(text.strip().replace("\n", " ").split())

def find_best_match(paragraph, page_text):
    paras = page_text.split("\n\n")
    max_ratio = 0
    best_para = None
    for para in paras:
        ratio = SequenceMatcher(None, normalize_text(paragraph), normalize_text(para)).ratio()
        if ratio > max_ratio:
            max_ratio = ratio
            best_para = para
    return best_para if max_ratio > 0.4 else None

def generate_updated_pos_pdf(ship_type, pos_filename):
    session = SessionLocal()

    try:
        pos_file = session.query(POSFile).filter_by(ship_type=ship_type, file_path=pos_filename).first()
        if not pos_file:
            print("❌ POS 파일 정보가 DB에 없음")
            return None

        paragraphs = (
            session.query(POSParagraph)
            .filter_by(pos_file_id=pos_file.id)
            .order_by(POSParagraph.order.asc())
            .all()
        )

        if not paragraphs:
            print("❌ 관련 문단 없음")
            return None

        # ✅ 기존 POS PDF 열기
        original_pdf_path = os.path.join(POS_FOLDER, ship_type, pos_filename)
        if not os.path.exists(original_pdf_path):
            print(f"❌ 원본 POS 파일이 존재하지 않음: {original_pdf_path}")
            return None

        doc = fitz.open(original_pdf_path)

        for para in paragraphs:
            normalized_para = normalize_text(para.content)
            found = False

            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                matched = find_best_match(para.content, page_text)

                if matched:
                    print(f"🔄 문단 수정 (p.{page_num+1})")
                    rects = page.search_for(matched)
                    if rects:
                        for r in rects:
                            page.add_redact_annot(r, fill=(1, 1, 1))
                        page.apply_redactions()
                        page.insert_text(
                            rects[0].tl,
                            para.content.strip(),
                            fontsize=11,
                            color=(0, 0, 0),
                            fontname="helv",
                            render_mode=0
                        )
                        found = True
                        break

            if not found:
                print(f"⚠️ PDF에서 유사 문단 못 찾음: {para.content[:50]}...")

        # ✅ 저장 경로 및 파일명 구성
        output_filename = pos_filename.replace("STD", "updated")
        output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
        doc.save(output_path)
        doc.close()

        print(f"✅ 수정된 POS PDF 저장 완료: {output_path}")
        return output_path

    finally:
        session.close()