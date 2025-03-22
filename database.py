from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# ✅ 기본 루트 디렉토리 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ POS/SPEC 폴더 경로
POS_FOLDER = os.path.join(BASE_DIR, "DB", "POS")
SPEC_FOLDER = os.path.join(BASE_DIR, "DB", "SPEC")

# ✅ PostgreSQL 연결 URI (.env에서 불러오기)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:587289@localhost:5432/aipos"
)

# ✅ SQLAlchemy 설정
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ✅ POS 문장 비교용 모델
class POS(Base):
    __tablename__ = 'pos'

    id = Column(Integer, primary_key=True, index=True)
    ship_type = Column(String(50), nullable=False)
    section = Column(Text)
    original_text = Column(Text, nullable=False)

# ✅ POS PDF 파일 경로 모델
class POSFile(Base):
    __tablename__ = 'pos_files'

    id = Column(Integer, primary_key=True)
    ship_type = Column(String(50), nullable=False)
    file_path = Column(Text, nullable=False)  # 예: STD_POS_174K.pdf

# ✅ 표준 사양서 문단 모델
class Spec(Base):
    __tablename__ = 'spec'

    id = Column(Integer, primary_key=True)
    ship_type = Column(String(50), nullable=False)
    section = Column(Text)
    paragraph = Column(Text, nullable=False)

# ✅ 테이블 생성 함수
def create_tables():
    Base.metadata.create_all(bind=engine)

# ✅ POS PDF 전체 경로 반환
def get_pos_pdf_path_by_filename(ship_type, filename):
    session = SessionLocal()
    try:
        pos_file = session.query(POSFile).filter_by(ship_type=ship_type, file_path=filename).first()
        if pos_file:
            return os.path.join(POS_FOLDER, ship_type.replace(" ", "_"), filename)
        return None
    finally:
        session.close()

# ✅ POS 항목 목록
def get_pos_items(ship_type):
    session = SessionLocal()
    try:
        return session.query(POS).filter_by(ship_type=ship_type).all()
    finally:
        session.close()

# ✅ 표준 사양서 문단 목록
def get_standard_spec_paragraphs(ship_type):
    session = SessionLocal()
    try:
        return session.query(Spec).filter_by(ship_type=ship_type).all()
    finally:
        session.close()

# ✅ 특정 선종(ship_type)에 해당하는 POS 파일명 목록 가져오기
def get_pos_filenames_by_shiptype(ship_type):
    session = SessionLocal()
    try:
        files = session.query(POSFile).filter_by(ship_type=ship_type).all()
        return [f.file_path for f in files]  # 파일 경로만 추출 (파일명)
    finally:
        session.close()