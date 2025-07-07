#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# .env 파일 로드
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"DATABASE_URL: {DATABASE_URL}")

try:
    # 데이터베이스 연결 테스트
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        # 간단한 쿼리 실행
        result = connection.execute(text("SELECT version();"))
        version = result.fetchone()
        print(f"✅ 데이터베이스 연결 성공!")
        print(f"PostgreSQL 버전: {version[0]}")
        
        # 테이블 목록 확인
        result = connection.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = result.fetchall()
        print(f"\n📋 현재 테이블 목록:")
        for table in tables:
            print(f"  - {table[0]}")
            
        # 각 테이블의 레코드 수 확인
        print(f"\n📊 테이블별 레코드 수:")
        for table in tables:
            table_name = table[0]
            try:
                result = connection.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.fetchone()[0]
                print(f"  - {table_name}: {count}개")
            except Exception as e:
                print(f"  - {table_name}: 조회 실패 ({e})")

except OperationalError as e:
    print(f"❌ 데이터베이스 연결 실패: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 예상치 못한 오류: {e}")
    sys.exit(1)
