# services/pos_pdf_writer.py

import os
import fitz  # PyMuPDF
from database import get_pos_pdf_path

def apply_differences_to_pos_pdf(ship_type, differences, project_number="1234"):
    pos_pdf_path = get_pos_pdf_path(ship_type)
    if not pos_pdf_path or not os.path.exists(pos_pdf_path):
        print(f"❌ POS PDF 경로가 유효하지 않음: {pos_pdf_path}")
        return None

    try:
        doc = fitz.open(pos_pdf_path)

        for diff in differences:
            target_text = diff["POS 대상"]
            new_text = diff["프로젝트 사양서"]
            red_bold = f"<span style='color:red;font-weight:bold'>{new_text}</span>"

            for page in doc:
                text_instances = page.search_for(target_text)
                for inst in text_instances:
                    page.add_redact_annot(inst, fill=(1, 1, 1))
                    page.apply_redactions()
                    page.insert_textbox(inst, new_text, fontsize=10, color=(1, 0, 0), fontname="helv", overlay=True)

        new_filename = os.path.basename(pos_pdf_path).replace("STD", project_number)
        output_path = os.path.join(os.path.dirname(pos_pdf_path), new_filename)
        doc.save(output_path)
        doc.close()

        print(f"✅ 프로젝트 POS 저장 완료: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ PDF 반영 중 오류 발생: {e}")
        return None