from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ✅ PostgreSQL 연결 URI (.env에서 불러오도록)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:password@localhost:5432/yourdbname")

# ✅ SQLAlchemy 설정
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ✅ POS 모델 정의
class POS(Base):
    __tablename__ = 'pos'
    
    id = Column(Integer, primary_key=True, index=True)
    ship_type = Column(String(50), nullable=False)
    section = Column(Text)
    original_text = Column(Text, nullable=False)

# ✅ 테이블 생성 함수 (초기 세팅 시 사용)
def create_tables():
    Base.metadata.create_all(bind=engine)