"""This module handles all Firebase Firestore services.

@Author: Karthick T. Sharma
"""

from sqlalchemy.future import select
from sqlalchemy import delete, update, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker,selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.sql.expression import func
from models import User, Question, Choice, Comment, Rating
from google.cloud import storage
import bcrypt
# from passlib.hash import bcrypt
import jwt
import datetime
import uuid
from typing import Dict, List
import xml.etree.ElementTree as ET

from src.utils import english_to_vietnamese

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)

# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'D:/GR2/quizzzy2/quizzzy-backend/app/secret/serviceAccountKey.json'


# Tạo engine cho cơ sở dữ liệu
database_url = "mysql+aiomysql://my_user:my_password@103.138.113.68/my_database"
engine = create_async_engine(database_url, echo=True)

# Tạo session maker
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class FirebaseService:
    """FirebaseService"""
    """Handle firestore operations."""

    def __init__(self, db: AsyncSession):
        # """Initialize firebase firestore client."""
        # firebase_admin.initialize_app(
        #     credentials.Certificate("secret/serviceAccountKey.json"))
        # self._db = firestore.client()
        # # Thông tin kết nối đến cơ sở dữ liệu MySQL
        # self.database_url = "mysql+aiomysql://my_user:my_password@localhost/my_database"
        
        # # Tạo engine cho cơ sở dữ liệu
        # self.engine = create_async_engine(self.database_url, echo=True)

        # # Tạo session maker
        # self.SessionLocal = sessionmaker(
        #     bind=self.engine,
        #     class_=AsyncSession,
        #     expire_on_commit=False
        # )

        # # Tạo phiên làm việc
        # self.db: AsyncSession = self.SessionLocal()
        self.db = db
    
    async def close(self):
        """Đóng phiên làm việc."""
        await self.db.close()

    def __validate(self, questions, crct_ans, all_ans):
        """Validate data

        Args:
            questions (list[str]): list of generated questions.
            crct_ans (list[str]): list of correct answers.
            all_ans (list[str]): list of all answers squeezed together.

        Raises:
            TypeError: 'questions' must be list of strings
            TypeError: 'crct_ans' must be list of strings
            TypeError: 'all_ans' must be list of strings
        """
        if not isinstance(questions, list):
            raise TypeError("'questions' must be list of strings")

        if not isinstance(crct_ans, list):
            raise TypeError("'crct_ans' must be list of strings")

        if not isinstance(all_ans, list):
            raise TypeError("'all_ans' must be list of strings")
    
    
    def __validate_export_input(self, uid, name):
        """Validate export input data

        Args:
            uid (str): user id.
            name (str): topic name.

        Raises:
            ValueError: If any input is invalid.
        """
        if not uid or not isinstance(uid, int):
            raise ValueError("'uid' must be a int")

        if not name or not isinstance(name, str):
            raise ValueError("'name' must be a non-empty string")
  
    async def get_random_questions(self, uid: int, limit: int = 20) -> List[Dict[str, any]]:
        """Lấy ngẫu nhiên các câu hỏi từ cơ sở dữ liệu.
        
        Args:
            limit (int): Số lượng câu hỏi cần lấy. Mặc định là 20.

        Returns:
            List[Dict[str, any]]: Danh sách các câu hỏi.
        """
        try:
            all_data = {}

            query = (
                select(Question)
                .order_by(func.rand())
                .limit(limit)
                .options(
                    selectinload(Question.choices),     # Load trước các lựa chọn
                    selectinload(Question.comments),    # Load trước các bình luận
                    selectinload(Question.ratings)      # Load trước các đánh giá
                )
            )
            result = await self.db.execute(query)
            questions_list = result.scalars().all()

            if not questions_list:
                raise ValueError("Không tìm thấy câu hỏi nào.")

            # Chuẩn bị dữ liệu để trả về
            for question in questions_list:
                topic = question.topic
                # Lấy các lựa chọn cho câu hỏi
                choices: List[Choice] = question.choices
                choices_text = [choice.choice_text for choice in choices] # Truy cập danh sách các lựa chọn liên quan

                # Lấy các bình luận cho câu hỏi
                comments: List[Comment] = question.comments
                comments_text = [comment.comment_text for comment in comments]
                # comments_data = [{
                #                     'comment_id': comment.id,
                #                     'user_id': comment.user_id,
                #                     'comment_value': comment.comments_text
                #                 }
                #                 for comment in question.comments]
                comments_data = []
                for comment in comments:
                    username = await self.get_username_from_uid(comment.user_id)  # Lấy tên người dùng từ user_id
                    comments_data.append({
                        'comment_id': comment.id,
                        'user_id': comment.user_id,
                        'comment_value': comment.comment_text,
                        'created_at': comment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        'username': username  # Thêm username vào dữ liệu bình luận
                    })
                
                # Lấy các đánh giá cho câu hỏi
                ratings: List[Rating] = question.ratings
                ratings_values = [rating.rating_value for rating in ratings]
                # ratings_data = [{
                #     'rating_id': rating.id, 
                #     'rating_value': rating.rating_value, 
                #     'created_at': rating.created_at
                # } 
                # for rating in question.ratings]
                ratings_data = []
                for rating in ratings:
                    username = await self.get_username_from_uid(rating.user_id)  # Lấy tên người dùng từ user_id
                    ratings_data.append({
                    'rating_id': rating.id, 
                    'rating_value': rating.rating_value, 
                    'created_at': rating.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    'username': username  # Thêm username vào dữ liệu bình luận
                })
                # ratings_data = [{'rating_id': rating['id'], 'rating_value': rating['rating_value']} for rating in question.ratings]
                # Dưới không subscriptable được

                # Tính toán điểm trung bình
                average_rating = sum(ratings_values) / len(ratings_values) if ratings_values else 0

                user_data = await self.get_username_from_uid(question.user_id)

                duplicate_info = await self.check_duplicates(uid, question.question_text, choices, question.id)
                
                question_data = {
                    'username': user_data,
                    'question_id': question.id,
                    'context': question.context,
                    'question_text': question.question_text,
                    'choices': choices_text,
                    'correct_choice': question.correct_choice,
                    'tags': question.tags,
                    'duplicate_info': duplicate_info,
                    'comments': comments_data,  # Thêm bình luận vào dữ liệu câu hỏi
                    'ratings': ratings_data,    # Thêm đánh giá vào dữ liệu câu hỏi
                    'average_rating': average_rating
                }
                
                # Thêm câu hỏi vào danh sách câu hỏi của topic
                if topic not in all_data:
                    all_data[topic] = []
                all_data[topic].append(question_data)

            return all_data
        
        except SQLAlchemyError as e:
            raise ValueError(f"Could not retrieve data: {str(e)}")