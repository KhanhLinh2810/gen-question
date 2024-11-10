# models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Date, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(100), nullable=False)
    GeneratorWorking = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    current_token = Column(String(255), nullable=True)
    avatar = Column(String(255), nullable=True)
    
    questions = relationship("Question", back_populates="user")

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String(100), nullable=False)
    context = Column(Text, nullable=False)  # Nội dung câu hỏi
    question_text = Column(Text, nullable=False)
    correct_choice = Column(String(255), nullable=False)
    tags = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="questions")
    choices = relationship("Choice", back_populates="question", cascade="all, delete")
    comments = relationship("Comment", back_populates="question", cascade="all, delete")
    ratings = relationship("Rating", back_populates="question", cascade="all, delete")

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
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating_value = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    question = relationship("Question", back_populates="ratings")
