import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, POSFile, create_tables, POS_FOLDER

# ✅ 선종별 폴더 매핑
ship_folder_mapping = {
    "174K LNGC": os.path.join(POS_FOLDER, "174K_LNGC"),
    "180K LNGC": os.path.join(POS_FOLDER, "180K_LNGC"),
    "200K LNGC": os.path.join(POS_FOLDER, "200K_LNGC"),
    "88K LPGC": os.path.join(POS_FOLDER, "88K_LPGC"),
    "91K LPGC": os.path.join(POS_FOLDER, "91K_LPGC"),
}

def upload_and_cleanup_pos_files():
    create_tables()
    session = SessionLocal()

    # 현재 실제 폴더에 존재하는 파일들
    existing_files_in_disk = set()

    for ship_type, folder_path in ship_folder_mapping.items():
        if not os.path.exists(folder_path):
            print(f"📁 폴더 없음 (건너뜀): {folder_path}")
            continue

        for file_name in os.listdir(folder_path):
            if file_name.endswith(".pdf"):
                existing_files_in_disk.add((ship_type, file_name))

                existing = session.query(POSFile).filter_by(ship_type=ship_type, file_path=file_name).first()
                if existing:
                    print(f"🔄 업데이트 대상 (이미 등록됨): {file_name} ({ship_type})")
                else:
                    new_pos = POSFile(ship_type=ship_type, file_path=file_name)
                    session.add(new_pos)
                    print(f"✅ 새로 등록됨: {file_name} ({ship_type})")

    # 실제 파일이 없는 POSFile DB 항목 삭제
    all_pos_files = session.query(POSFile).all()
    delete_count = 0
    for pos in all_pos_files:
        if (pos.ship_type, pos.file_path) not in existing_files_in_disk:
            print(f"🗑️ 삭제됨 (파일 없음): {pos.file_path} ({pos.ship_type})")
            session.delete(pos)
            delete_count += 1

    session.commit()
    session.close()
    print(f"📦 완료: 총 {len(existing_files_in_disk)}개 업로드, {delete_count}개 삭제")

if __name__ == "__main__":
    upload_and_cleanup_pos_files()