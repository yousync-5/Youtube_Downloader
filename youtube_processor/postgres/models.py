# models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base

class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_name = Column(String, index=True)
    actor_name = Column(String)
    category = Column(String)
    start_time = Column(Float)
    end_time = Column(Float)
    s3_textgrid_url = Column(String)
    s3_pitch_url = Column(String)
    s3_bgvoice_url = Column(String)
    youtube_url = Column(String)

    # 관계 설정 (1:N)
    sentences = relationship("ScriptSentence", back_populates="token")


class ScriptSentence(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("tokens.id"))
    script = Column(Text)
    start_time = Column(Float)
    end_time = Column(Float)

    # 관계 설정
    token = relationship("Token", back_populates="sentences")
    words = relationship("ScriptWord", back_populates="sentence", cascade="all, delete")

class ScriptWord(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    sentence_id = Column(Integer, ForeignKey("scripts.id"))
    word = Column(String)
    start_time = Column(Float)
    end_time = Column(Float)
    probability = Column(Float)

    # 관계 설정
    sentence = relationship("ScriptSentence", back_populates="words")