import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Spec, SessionLocal, SPEC_FOLDER
from services.spec_compare import extract_text_from_pdf, split_into_paragraphs, group_by_section
import os

def upload_spec_pdf_to_db(ship_type, filename):
    filepath = os.path.join(SPEC_FOLDER, filename)
    text = extract_text_from_pdf(filepath)
    if not text:
        print("❌ PDF 읽기 실패")
        return

    paragraphs = split_into_paragraphs(text)
    sections = group_by_section(paragraphs)

    session = SessionLocal()
    for section, paras in sections:
        for para in paras:
            spec = Spec(ship_type=ship_type, section=section, paragraph=para)
            session.add(spec)
    session.commit()
    session.close()
    print("✅ 표준 사양서 업로드 완료")

if __name__ == "__main__":
    upload_spec_pdf_to_db("174K LNGC", "STD_SPEC_4.pdf")