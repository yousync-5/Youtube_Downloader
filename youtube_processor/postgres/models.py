from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON # PostgreSQL JSON 타입 사용 시 필요
from sqlalchemy.sql import func # func.now() 사용 시 필요

from .database import Base

# Token 모델이 참조하는 모든 모델들을 먼저 정의합니다.
# 정의 순서도 중요합니다. 참조되는 모델이 먼저 정의되어야 합니다.

class URL(Base):
    __tablename__ = "urls"
    youtube_url = Column(Text, primary_key=True)   
    actor_id    = Column(Integer,
                         ForeignKey("actors.id", ondelete="CASCADE"),
                         nullable=False, index=True)

    actor  = relationship("Actor", back_populates="urls")
    tokens = relationship("Token",
                          back_populates="url",
                          cascade="all, delete",
                          passive_deletes=True)

class Actor(Base):
    __tablename__ = "actors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    
    urls = relationship("URL",
                        back_populates="actor",
                        cascade="all, delete",
                        passive_deletes=True)

    token_actors = relationship(
        "TokenActor",
        back_populates="actor",
        cascade="all, delete",
        passive_deletes=True
    )

    aliases = relationship(
        "ActorAlias", # ActorAlias 모델은 정의되지 않았지만, 일단 관계만 추가
        back_populates="actor",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

class ActorAlias(Base): # Actor 모델에 관계가 있으므로 추가 (정의가 없었음)
    __tablename__ = "actor_aliases"
    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("actors.id", ondelete="CASCADE"), nullable=False, index=True)
    alias_name = Column(String, nullable=False, index=True)

    __table_args__ = (UniqueConstraint("actor_id", "alias_name", name="uq_actor_alias"),)

    actor = relationship("Actor", back_populates="aliases")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    
    google_id = Column(String, unique=True, index=True, nullable=True)
    profile_picture = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    login_type = Column(String, default="email")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    bookmarks = relationship(
        "Bookmark",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    
    token_name = Column(String, nullable=False)
    actor_name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)

    s3_textgrid_url = Column(Text, nullable=True)
    s3_pitch_url = Column(Text, nullable=True)
    s3_bgvoice_url = Column(Text, nullable=True)
    youtube_url = Column(
        Text,
        ForeignKey("urls.youtube_url", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    view_count = Column(Integer, nullable=False, default=0, index=True)

    # 관계
    url = relationship("URL", back_populates="tokens")
    scripts = relationship("Script",
                        back_populates="token",
                        cascade="all, delete",
                        passive_deletes=True)

    token_actors = relationship(
        "TokenActor",
        back_populates="token",
        cascade="all, delete",
        passive_deletes=True
    )

    bookmarked_by = relationship(
        "Bookmark",
        back_populates="token",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
    analysis_results = relationship("AnalysisResult", back_populates="token", cascade="all, delete")


class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(
        Integer,
        ForeignKey("tokens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )    
    
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    script = Column(Text, nullable=False)
    translation = Column(Text, nullable=True)

    token = relationship(
        "Token",
        back_populates="scripts",
        passive_deletes=True,
    )    
    words = relationship(
        "ScriptWord",
        back_populates="script",
        cascade="all, delete",
        passive_deletes=True,
    )

class ScriptWord(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(
        Integer,
        ForeignKey("scripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    word = Column(String)
    start_time = Column(Float)
    end_time = Column(Float)
    probability = Column(Float)
    
    # 새로 추가할 컬럼: MFCC 계수를 2D 리스트로 저장
    mfcc    = Column(JSON, nullable=True)
    
    # 관계 설정
    script = relationship(
        "Script",
        back_populates="words",
        passive_deletes=True,
    )

class Bookmark(Base):
    __tablename__ = "bookmarks"

    user_id  = Column(Integer,
                      ForeignKey("users.id", ondelete="CASCADE"),
                      primary_key=True,
                      index=True)
    token_id = Column(Integer,
                      ForeignKey("tokens.id", ondelete="CASCADE"),
                      primary_key=True,
                      index=True)

    created_at = Column(DateTime,
                        server_default=func.now(),
                        nullable=False)

    user  = relationship("User",  back_populates="bookmarks", passive_deletes=True)
    token = relationship("Token", back_populates="bookmarked_by", passive_deletes=True)

class TokenActor(Base):
    __tablename__ = "token_actors"
    id       = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("actors.id", ondelete="CASCADE"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("token_id", "actor_id", name="uq_token_actor"),
    )

    token = relationship("Token", back_populates="token_actors", passive_deletes=True)
    actor = relationship("Actor", back_populates="token_actors", passive_deletes=True)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)
    token_id = Column(Integer,
                  ForeignKey("tokens.id", ondelete="CASCADE"),
                  nullable=False)
    status = Column(String, nullable=False)
    progress = Column(Integer, nullable=False)
    result = Column(JSON, nullable=True)
    message = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    token = relationship("Token", back_populates="analysis_results")