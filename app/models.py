# models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Date, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

from src.enums import UserRole

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(100), nullable=False)
    generator_working = Column(Boolean, default=False)
    role = Column(Integer, default=UserRole.USER)
    avatar_url = Column(Text, nullable=True)
    
    questions = relationship(
        "Question",
        back_populates="user",
        cascade="all, delete",
        passive_deletes=True
    )

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic = Column(String(100), nullable=False)
    context = Column(Text, nullable=False)  # Nội dung câu hỏi
    question_text = Column(Text, nullable=False)
    correct_choice = Column(String(255), nullable=False)
    tags = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="questions")
    choices = relationship("Choice", back_populates="question", cascade="all, delete", passive_deletes=True)
    comments = relationship("Comment", back_populates="question", cascade="all, delete", passive_deletes=True)
    ratings = relationship("Rating", back_populates="question", cascade="all, delete", passive_deletes=True)

class Choice(Base):
    __tablename__ = "choices"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    choice_text = Column(String(255), nullable=False)
    
    question = relationship("Question", back_populates="choices")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    question = relationship("Question", back_populates="comments")

class Rating(Base):
    __tablename__ = "ratings"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    rating_value = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("Question", back_populates="ratings")

# src/models/base.py
from sqlalchemy import Column, DateTime, func

class BaseModelMixin:
    """Mixin để tự động thêm created_at và updated_at cho mọi model"""
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Lưu thời điểm tạo
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())  # Lưu thời điểm cập nhật
