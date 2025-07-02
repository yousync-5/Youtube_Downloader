# fix_encoding.py
with open(".env", "r", encoding="cp949") as f:
    content = f.read()

with open(".env", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ .env 파일을 UTF-8로 변환 완료!")
