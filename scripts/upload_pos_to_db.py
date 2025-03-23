import sys
import os
import fitz  # PyMuPDF
import re

# 로컬 실행용 __file__ 예외 처리
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from database import SessionLocal, POSFile, POSParagraph, create_tables, POS_FOLDER

# ✅ 선종별 폴더 매핑
ship_folder_mapping = {
    "174K LNGC": os.path.join(POS_FOLDER, "174K LNGC"),
    "180K LNGC": os.path.join(POS_FOLDER, "180K LNGC"),
    "200K LNGC": os.path.join(POS_FOLDER, "200K LNGC"),
    "88K LPGC": os.path.join(POS_FOLDER, "88K LPGC"),
    "91K LPGC": os.path.join(POS_FOLDER, "91K LPGC"),
}

# ✅ 섹션 헤더 추출
def extract_section_heading(text):
    match = re.match(r"^(\d+\.\d+)\s+", text)
    return match.group(1) if match else None

# ✅ PDF → 문단 파싱 함수
def parse_pdf_to_paragraphs(pdf_path):
    paragraphs = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            lines = page.get_text().split("\n")
            buffer = []
            for line in lines:
                if line.strip() == ".":
                    continue
                buffer.append(line.strip())
                if line.endswith(".") or line.endswith(":"):
                    paragraphs.append(" ".join(buffer))
                    buffer = []
            if buffer:
                paragraphs.append(" ".join(buffer))
        doc.close()
    except Exception as e:
        print(f"❌ PDF 파싱 실패: {pdf_path} - {e}")
    return paragraphs

# ✅ 메인 업로드 함수
def upload_and_cleanup_pos_files():
    create_tables()
    session = SessionLocal()

    existing_files_in_disk = set()

    for ship_type, folder_path in ship_folder_mapping.items():
        if not os.path.exists(folder_path):
            print(f"📁 폴더 없음 (건너뜀): {folder_path}")
            continue

        for file_name in os.listdir(folder_path):
            if not file_name.endswith(".pdf"):
                continue

            full_path = os.path.join(folder_path, file_name)
            existing_files_in_disk.add((ship_type, file_name))

            pos_file = session.query(POSFile).filter_by(ship_type=ship_type, file_path=file_name).first()
            if not pos_file:
                pos_file = POSFile(ship_type=ship_type, file_path=file_name)
                session.add(pos_file)
                session.flush()
                print(f"✅ POS 등록됨: {file_name} ({ship_type})")
            else:
                print(f"🔄 업데이트 대상 (이미 등록됨): {file_name} ({ship_type})")
                session.query(POSParagraph).filter_by(pos_file_id=pos_file.id).delete()

            paragraphs = parse_pdf_to_paragraphs(full_path)
            for i, para in enumerate(paragraphs):
                section = extract_section_heading(para)
                new_para = POSParagraph(
                    pos_file_id=pos_file.id,
                    section=section,
                    order=i + 1,
                    content=para
                )
                session.add(new_para)

    # ✅ DB에서 존재하지 않는 파일 삭제
    all_pos_files = session.query(POSFile).all()
    delete_count = 0
    for pos in all_pos_files:
        if (pos.ship_type, pos.file_path) not in existing_files_in_disk:
            print(f"🗑️ 삭제됨 (파일 없음): {pos.file_path} ({pos.ship_type})")
            session.query(POSParagraph).filter_by(pos_file_id=pos.id).delete()
            session.delete(pos)
            delete_count += 1

    session.commit()
    session.close()
    print(f"📦 완료: 총 {len(existing_files_in_disk)}개 업로드, {delete_count}개 삭제")

if __name__ == "__main__":
    upload_and_cleanup_pos_files()