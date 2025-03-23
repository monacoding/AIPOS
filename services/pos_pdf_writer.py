import os
import fitz  # PyMuPDF
from database import POS_FOLDER
from dotenv import load_dotenv

# ✅ 환경 변수 불러오기
load_dotenv()

# ✅ 다운로드 폴더 설정
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "download")

# ✅ 텍스트 정규화 함수
def normalize_text(text):
    return ' '.join(text.strip().split())

def apply_differences_to_pos_pdf(ship_type, differences, project_number, pos_filename):
    # ✅ POS 경로 설정
    source_pdf_path = os.path.join(POS_FOLDER, ship_type, pos_filename)
    if not os.path.exists(source_pdf_path):
        print(f"❌ 원본 POS 파일 없음: {source_pdf_path}")
        return None

    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    # ✅ 결과 파일 경로 설정
    result_filename = pos_filename.replace("STD", project_number)
    result_pdf_path = os.path.join(DOWNLOAD_FOLDER, result_filename)

    change_log = []

    try:
        doc = fitz.open(source_pdf_path)
        for diff in differences:
            std_text = diff["표준 사양서"]
            proj_text = diff["프로젝트 사양서"]

            # ✅ 변경 문장은 사전에 비교된 프로젝트 문장으로 바로 반영
            new_text = proj_text.strip()

            found = False
            for page in doc:
                text_instances = page.search_for(normalize_text(std_text))
                if text_instances:
                    for inst in text_instances:
                        page.add_redact_annot(inst, fill=(1, 1, 1))
                    page.apply_redactions()
                    # ✅ 빨간색 볼드로 삽입
                    page.insert_text(
                        text_instances[0].tl,
                        new_text,
                        fontsize=11,
                        color=(1, 0, 0),  # 빨간색
                        fontname="helv",
                        render_mode=3  # 볼드
                    )
                    change_log.append({
                        "기존": std_text,
                        "수정": new_text
                    })
                    found = True
                    break

            if not found:
                print(f"⚠️ '{std_text[:30]}...' 문구를 POS PDF에서 찾을 수 없음")
                print("📄 페이지 텍스트:")
                print(page.get_text())

        doc.save(result_pdf_path)
        doc.close()
        print(f"✅ 저장 완료: {result_pdf_path}")
        return result_pdf_path, change_log

    except Exception as e:
        print(f"❌ PDF 반영 중 오류: {e}")
        return None, []
