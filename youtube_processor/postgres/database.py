# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# .env 파일에 DATABASE_URL이 정의되어 있어야 함
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")  # 기본값은 SQLite
print("✅ DATABASE_URL:", DATABASE_URL)
# DB 엔진 생성
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 모델 베이스 클래스
Base = declarative_base()

# 의존성 주입 또는 수동으로 쓸 수 있게 하는 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
