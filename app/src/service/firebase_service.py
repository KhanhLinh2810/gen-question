"""This module handles all Firebase Firestore services.

@Author: Karthick T. Sharma
"""

import os
import firebase_admin

from firebase_admin import firestore
from firebase_admin import credentials

from sqlalchemy.future import select
from sqlalchemy import delete, update, or_, Table
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker,selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.sql.expression import func
from models import User, Question, Choice, Comment, Rating
from deep_translator import GoogleTranslator
from google.cloud import storage
import bcrypt
# from passlib.hash import bcrypt
import jwt
import datetime
import uuid
from typing import Optional, Dict, List
import xml.etree.ElementTree as ET
import json

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)

# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'D:/GR2/quizzzy2/quizzzy-backend/app/secret/serviceAccountKey.json'


def english_to_vietnamese(text):
    translator = GoogleTranslator(source='en', target='vi')
    translated_text = translator.translate(text)
    return translated_text

# Tạo engine cho cơ sở dữ liệu
database_url = "mysql+aiomysql://my_user:my_password@103.138.113.68/my_database"
engine = create_async_engine(database_url, echo=True)

# Tạo session maker
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class MySQLService:
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

    # def update_generated_status(self, request, status):
        # """Change status of 'GeneratorWorking' is firestore.

        # Args:
        #     request (ModelInput): request format from flutter.
        #     status (bool): state whether question generated.
        # """

        # if not isinstance(status, bool):
        #     raise TypeError("'status' must be a bool value")

        # doc_ref = self._db.collection('users').document(request.uid)
        # doc_ref.update({'GeneratorWorking': status})
    async def update_generated_status(self, uid: str, status: bool):
        """Cập nhật trạng thái 'GeneratorWorking' trong bảng users"""
        if not isinstance(status, bool):
            raise TypeError("'status' phải là kiểu bool")

        query = select(User).where(User.id == uid)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if user:
            user.GeneratorWorking = status
            await self.db.commit()

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

    # def check_duplicates(self, request, question, answers):
    #     """Kiểm tra câu hỏi và đáp án có trùng lặp trong database không.

    #     Args:
    #         request (ModelInput): yêu cầu từ người dùng.
    #         question (str): câu hỏi cần kiểm tra.
    #         answers (list[str]): các đáp án cần kiểm tra.

    #     Returns:
    #         dict: thông tin trùng lặp nếu có.
    #     """
    #     doc_ref = self._db.collection('users').document(request.uid)
    #     collection_name = english_to_vietnamese(request.name)
    #     collection_ref = doc_ref.collection(collection_name)
    #     documents = collection_ref.stream()
        
    #     duplicate_info = {
    #         'duplicate_questions': [],
    #         'duplicate_answers': []
    #     }

    #     # Lặp qua các tài liệu trong collection
    #     for idx, doc in enumerate(documents):
    #         data = doc.to_dict()

    #         # Kiểm tra nếu câu hỏi trùng lặp
    #         if data['question'] == question:
    #             duplicate_info['duplicate_questions'].append(idx)

    #         # Kiểm tra các đáp án trùng lặp
    #         for answer in answers:
    #             if answer in data['all_ans'].values():
    #                 duplicate_info['duplicate_answers'].append({'index': idx, 'answer': answer})

    #     # Trả về thông tin về các câu hỏi và đáp án trùng lặp
    #     return duplicate_info
    async def check_duplicates(self, uid: str, question: str, answers: list, current_question_id: int = None):
        """Kiểm tra câu hỏi và đáp án có trùng lặp trong cơ sở dữ liệu không, bỏ qua chính câu hỏi và đáp án của nó."""
        
        # Kiểm tra trùng lặp của câu hỏi
        query = select(Question).where(
            Question.user_id == uid,
            Question.question_text == question,
            Question.id != current_question_id  # Loại trừ chính câu hỏi này
        )
        result = await self.db.execute(query)
        duplicate_questions = result.scalars().all()

        duplicate_info = {
            'duplicate_questions': [q.id for q in duplicate_questions],
            'duplicate_answers': []
        }

        # Chuyển đổi `answers` thành danh sách các chuỗi nếu chưa phải
        answer_texts = [answer.choice_text if isinstance(answer, Choice) else answer for answer in answers]

        # Kiểm tra trùng lặp của các đáp án
        for answer_text in answer_texts:
            answer_query = select(Choice).where(
                Choice.question_id.in_([q.id for q in duplicate_questions]),
                Choice.choice_text == answer_text
            )
            answer_result = await self.db.execute(answer_query)
            duplicate_choices = answer_result.scalars().all()

            # Loại trừ các đáp án từ câu hỏi hiện tại
            duplicate_info['duplicate_answers'].extend([
                {'question_id': choice.question_id, 'answer': choice.choice_text}
                for choice in duplicate_choices if choice.question_id != current_question_id
            ])

        return duplicate_info
    
    # def send_results_to_fs(self, request, questions, crct_ans, all_ans, context):
    #     """Send generated question to appropiate fs doc.

    #     Args:
    #         request (ModelInput): request format from flutter.
    #         questions (list[str]): list of generated questions.
    #         crct_ans (list[str]): list of correct answers.
    #         all_ans (list[str]): list of all answers squeezed together.
    #         context (str): input corpus used to generate questions.
    #     """

    #     self.__validate(questions=questions,
    #                     crct_ans=crct_ans, all_ans=all_ans)

    #     doc_ref = self._db.collection('users').document(request.uid)
    #     print(all_ans)
    #     results = []
    #     for idx, question in enumerate(questions):
    #         q_dict = {
    #             'context': english_to_vietnamese(context),
    #             'question': english_to_vietnamese(question),
    #             'crct_ans': english_to_vietnamese(crct_ans[idx]),
    #             # 'all_ans': all_ans[idx * 4: 4 + idx * 4]
    #             'all_ans': {
    #                 '0': english_to_vietnamese(all_ans[idx * 4]),
    #                 '1': english_to_vietnamese(all_ans[idx * 4 + 1]),
    #                 '2': english_to_vietnamese(all_ans[idx * 4 + 2]),
    #                 '3': english_to_vietnamese(all_ans[idx * 4 + 3])
    #             }
    #         }
            
    #         collection_name = english_to_vietnamese(request.name)
    #         collection_ref = doc_ref.collection(collection_name)

            
    #         # # Kiểm tra xem tên collection đã tồn tại chưa
    #         # if collection_ref.get():
    #         #     # Collection đã tồn tại, cập nhật dữ liệu
    #         #     doc_ref.collection(collection_name).document(str(idx)).update(q_dict)
    #         #     print("Dữ liệu đã được cập nhật trong collection", collection_name)
    #         # else:
    #         #     # Collection chưa tồn tại, tạo mới
    #         #     doc_ref.collection(collection_name).document(str(idx)).set(q_dict)
    #         #     print("Dữ liệu đã được thêm vào collection", collection_name)
            
            
    #         # # Sử dụng ID tự động của Firestore để tạo tài liệu mới
    #         # collection_ref.add(q_dict)
    #         # print("Dữ liệu đã được thêm vào collection", collection_name)

            
    #         # Kiểm tra trùng lặp
    #         duplicate_info = self.check_duplicates(request, q_dict['question'], list(q_dict['all_ans'].values()))
            
    #         # Lấy số lượng tài liệu hiện có trong collection
    #         current_documents = collection_ref.get()
    #         current_count = len(current_documents)

    #         # results = []  # Danh sách để lưu trữ kết quả

    #         # Sử dụng current_count + idx để tạo ID tài liệu tuần tự
    #         document_id = str(current_count + idx)
    #         collection_ref.document(document_id).set(q_dict)
    #         print("Dữ liệu đã được thêm vào collection", collection_name, "với document ID:", document_id)

    #         # Lưu lại thông tin về collection name, document ID và dữ liệu đã lưu vào danh sách results
    #         results.append({
    #             'collection_name': collection_name,
    #             'document_id': document_id,
    #             'data': q_dict,
    #             'duplicate_info': duplicate_info
    #         })
    #     # Trả về danh sách results sau khi hoàn tất quá trình lưu trữ
    #     return results
    async def send_results_to_db(self, uid: str, topic: str, questions: list, crct_ans: list, all_ans: list, context: str, tags: list):
        """Gửi câu hỏi đã tạo vào cơ sở dữ liệu MySQL"""
        self.__validate(questions=questions, crct_ans=crct_ans, all_ans=all_ans)

        tags_str = ",".join(tags)  # Chuyển danh sách tags thành chuỗi phân cách bởi dấu phẩy

        query = select(Question).where(Question.user_id == uid, Question.topic == topic)
        result = await self.db.execute(query)
        topic_questions = result.scalars().all()
        if topic_questions:
            topic_id = topic_questions[0].topic

        if not topic:
            topic = str(uuid.uuid4())

        results = []
        user_data = await self.get_username_from_uid(uid)
        for idx, question in enumerate(questions):
            new_question = Question(
                user_id=uid,
                topic=english_to_vietnamese(topic),
                question_text=english_to_vietnamese(question),
                context=english_to_vietnamese(context),
                correct_choice=english_to_vietnamese(crct_ans[idx]),
                tags=tags_str
            )
            self.db.add(new_question)
            await self.db.flush()  # Để lấy ID của câu hỏi

            # Lưu các lựa chọn câu trả lời
            choices = [
                english_to_vietnamese(all_ans[idx * 4 + i]) for i in range(4)
            ]
            for choice_text in choices:
                new_choice = Choice(
                    question_id=new_question.id,
                    choice_text=choice_text
                )
                self.db.add(new_choice)

            await self.db.commit()

            duplicate_info = await self.check_duplicates(uid, new_question.question_text, choices, new_question.id)
            results.append({
                'username': user_data,
                'question_id': new_question.id,
                'topic': new_question.topic,
                'context': new_question.context,
                'question_text': new_question.question_text,
                'choices': choices,
                'correct_choice': new_question.correct_choice,
                'tags': new_question.tags,
                'duplicate_info': duplicate_info
            })

        return results
    
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

    # def get_questions_by_uid_and_topic(self, uid, topic):
    #     """Get questions from Firestore based on user id and topic.

    #     Args:
    #         uid (str): user id.
    #         topic (str): topic name.

    #     Returns:
    #         list[dict]: list of questions with their answers.
    #     """
    #     self.__validate_export_input(uid, topic)  # Validate inputs

    #     doc_ref = self._db.collection('users').document(uid)
    #     collection_ref = doc_ref.collection(topic)  # Không cần dịch topic

    #     # Kiểm tra xem collection có tồn tại hay không
    #     documents = collection_ref.stream()  # Lấy tất cả các tài liệu trong collection
    #     documents_list = list(documents)  # Chuyển stream thành danh sách để kiểm tra

    #     if not documents_list:
    #         raise ValueError(f"Topic '{topic}' does not exist for user '{uid}'.")
        
    #     questions = []
    #     for doc in documents_list:
    #         data = doc.to_dict()
    #         print(data['question'])
    #         print([data['all_ans']['0'], data['all_ans']['1'], data['all_ans']['2'], data['all_ans']['3']])
    #         print(str([data['all_ans']['0'], data['all_ans']['1'], data['all_ans']['2'], data['all_ans']['3']].index(data['crct_ans'])))
    #         question = {
    #             'text': data['question'],
    #             'choices': [data['all_ans']['0'], data['all_ans']['1'], data['all_ans']['2'], data['all_ans']['3']],
    #             'correct_choice': data['crct_ans']
    #         }
    #         questions.append(question)
    #     return questions
    async def get_questions_by_uid_and_topic(self, uid: int, topic: str) -> List[Dict[str, any]]:
        """Lấy câu hỏi từ MySQL dựa trên user id và topic.

        Args:
            uid (int): ID người dùng.
            topic (str): Tên chủ đề.

        Returns:
            list[dict]: danh sách câu hỏi với các đáp án của chúng.
        """
        # Xác thực đầu vào
        if not isinstance(uid, int) or not isinstance(topic, str):
            raise ValueError("Invalid uid or topic")

        # Truy vấn câu hỏi từ cơ sở dữ liệu dựa trên uid và topic
        query = (
            select(Question)
            .where(Question.user_id == uid, Question.topic == topic)
            .options(selectinload(Question.choices), selectinload(Question.comments), selectinload(Question.ratings))
            )  # Tải sẵn các choices, comments và ratings
        result = await self.db.execute(query)
        questions_list = result.scalars().all()  # Lấy tất cả các câu hỏi

        if not questions_list:
            raise ValueError(f"Topic '{topic}' does not exist for user '{uid}'.")

        questions = []
        for question in questions_list:
            topic = question.topic
            # Lấy các lựa chọn cho câu hỏi
            choices: List[Choice] = question.choices
            choices_text = [choice.choice_text for choice in choices] # Truy cập danh sách các lựa chọn liên quan

            # Lấy các bình luận cho câu hỏi
            comments: List[Comment] = question.comments
            comments_text = [comment.comment_text for comment in comments]
            
            # Lấy các đánh giá cho câu hỏi
            ratings: List[Rating] = question.ratings
            ratings_values = [rating.rating_value for rating in ratings]

            # Tính toán điểm trung bình
            average_rating = sum(ratings_values) / len(ratings_values) if ratings_values else 0

            question_data = {
                'text': question.question_text,
                'choices': choices_text,
                'correct_choice': question.correct_choice,
                'tags': question.tags,
                'comments': comments_text,  # Thêm bình luận vào dữ liệu câu hỏi
                'ratings': ratings_values,    # Thêm đánh giá vào dữ liệu câu hỏi
                'average_rating': average_rating
            }
            questions.append(question_data)

        return questions

    # def create_user(self, email: str, username: str, password: str, is_admin: bool):
    #     """Create a new user with a unique UID.

    #     Args:
    #         email (str): User's email.
    #         username (str): User's username.
    #         password (str): User's password.

    #     Returns:
    #         dict: User's information including UID.
    #     """
    #     users_ref = self._db.collection('users')
        
    #     # Check if email or username already exists
    #     email_query = users_ref.where('email', '==', email).get()
    #     if email_query:
    #         raise ValueError("Email already exists")
        
    #     username_query = users_ref.where('username', '==', username).get()
    #     if username_query:
    #         raise ValueError("Username already exists")
        
    #     # Hash the password
    #     hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
    #     # Create a unique UID
    #     uid = str(uuid.uuid4())
        
    #     # Save the user to Firestore
    #     user_data = {
    #         'uid': uid,
    #         'email': email,
    #         'username': username,
    #         'password': hashed_password.decode('utf-8'),
    #         'is_admin': is_admin
    #     }
    #     users_ref.document(uid).set(user_data)
        
    #     return user_data
    async def create_user(self, email: str, username: str, password: str, is_admin: bool = False):
        """Tạo người dùng mới với MySQL"""
        # hashed_password = bcrypt.hash(password)
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        new_user = User(
            email=email,
            username=username,
            password=hashed_password.decode('utf-8'),
            is_admin=is_admin,
            GeneratorWorking=False,
            current_token=None,
            avatar=None 
        )
        self.db.add(new_user)
        try:
            await self.db.commit()
            return new_user
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Username or email already exists")

    # def authenticate_user(self, identifier, password):
    #     """Authenticate a user with email/username and password.

    #     Args:
    #         identifier (str): User's email or username.
    #         password (str): User's password.

    #     Returns:
    #         str: JWT token if authentication is successful.
    #     """
    #     users_ref = self._db.collection('users')
        
    #     # Check if the identifier is an email or username
    #     user_query = users_ref.where('email', '==', identifier).get()
    #     if not user_query:
    #         user_query = users_ref.where('username', '==', identifier).get()
        
    #     if not user_query:
    #         raise ValueError("Invalid email/username or password")
        
    #     user_data = user_query[0].to_dict()
        
    #     # Check the password
    #     if not bcrypt.checkpw(password.encode('utf-8'), user_data['password'].encode('utf-8')):
    #         raise ValueError("Invalid email/username or password")
        
    #     # Generate a JWT token
    #     token = jwt.encode({
    #         'uid': user_data['uid'],
    #         'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    #     }, 'your_jwt_secret', algorithm='HS256')
        
    #     return token, user_data['uid']
    async def authenticate_user(self, username_or_email: str, password: str):
        """Xác thực người dùng với email/username và mật khẩu"""
        query = select(User).where((User.username == username_or_email) | (User.email == username_or_email))
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        # Check the password
        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            raise ValueError("Invalid email/username or password")
        
        # Generate a JWT token
        token = jwt.encode({
            'uid': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=3)
        }, 'your_jwt_secret', algorithm='HS256')
        
        return token, user.id

    # def get_user_by_email(self, email):
    #     """Retrieve user data by email from Firestore.

    #     Args:
    #         email (str): Email to search for in Firestore.

    #     Returns:
    #         dict: User data if found, None otherwise.
    #     """
    #     users_ref = self._db.collection('users')
    #     query = users_ref.where('email', '==', email).limit(1).get()
        
    #     for user in query:
    #         return user.to_dict()

    #     return None
    async def get_user_by_email(self, email: str):
        """Retrieve user data by email from MySQL.

        Args:
            email (str): Email to search for in MySQL.

        Returns:
            User: User data if found, None otherwise.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()  # Lấy một đối tượng User hoặc None nếu không tìm thấy

    # def get_user_by_username(self, username):
    #     """Retrieve user data by username from Firestore.

    #     Args:
    #         username (str): Username to search for in Firestore.

    #     Returns:
    #         dict: User data if found, None otherwise.
    #     """
    #     users_ref = self._db.collection('users')
    #     query = users_ref.where('username', '==', username).limit(1).get()
        
    #     for user in query:
    #         return user.to_dict()

    #     return None
    async def get_user_by_username(self, username: str):
        """Retrieve user data by username from MySQL.

        Args:
            username (str): Username to search for in MySQL.

        Returns:
            User: User data if found, None otherwise.
        """
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_username_from_uid(self, uid: int) -> str:
        """
        Lấy tên người dùng từ user ID.

        Args:
            uid (int): ID của người dùng.

        Returns:
            str: Tên người dùng.
        """
        try:
            # Truy vấn lấy user dựa trên uid
            query = select(User).where(User.id == uid)
            result = await self.db.execute(query)
            user = result.scalars().first()
            
            if user:
                return user.username
            else:
                raise ValueError(f"Không tìm thấy người dùng với ID: {uid}")
        
        except SQLAlchemyError as e:
            raise ValueError(f"Lỗi truy vấn cơ sở dữ liệu: {str(e)}")
    
    async def get_user_info_from_uid(self, uid: int) -> str:
        """
        Lấy thông tin người dùng từ user ID.

        Args:
            uid (int): ID của người dùng.

        Returns:
            str: Tên người dùng.
        """
        try:
            # Truy vấn lấy user dựa trên uid
            query = select(User).where(User.id == uid)
            result = await self.db.execute(query)
            user = result.scalars().first()
            
            if user:
                return user
            else:
                raise ValueError(f"Không tìm thấy người dùng với ID: {uid}")
        
        except SQLAlchemyError as e:
            raise ValueError(f"Lỗi truy vấn cơ sở dữ liệu: {str(e)}")
    
    # def change_password_func(self, uid: str, current_password: str, new_password: str):
    #     """
    #         Change password of a user in Firestore.
    #         Args:
    #             identifier (str): User's email or username.
    #             current_password (str): User's current password.
    #             new_password (str): User's new password.
    #         Returns:
    #             dict: Success message if password change is successful.
    #     """
    #     users_ref = self._db.collection('users').document(uid)
    #     user_data = users_ref.get().to_dict()
       
    #     # Kiểm tra mật khẩu hiện tại
    #     if not bcrypt.checkpw(current_password.encode('utf-8'), user_data['password'].encode('utf-8')):
    #         raise ValueError("Invalid password")
 
    #     # Hash mật khẩu mới
    #     new_hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
       
    #     # Cập nhật mật khẩu mới trong Firestore
    #     users_ref.update({'password': new_hashed_password})
       
    #     return {'message': 'Password changed successfully'}
    async def change_password_func(self, uid: int, current_password: str, new_password: str):
        """Đổi mật khẩu cho người dùng"""
        query = select(User).where(User.id == uid)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not bcrypt.checkpw(current_password.encode('utf-8'), user.password.encode('utf-8')):
            raise ValueError("Invalid password")

        new_hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.password = new_hashed_password
        await self.db.commit()
        return {'message': 'Password changed successfully'}
 
    # def get_user_by_token(self, token: str):
    #     try:
    #         payload = jwt.decode(token, "your_jwt_secret", algorithms=["HS256"])
    #         uid = payload.get("uid")
    #         if not uid:
    #             raise ValueError("Invalid token")
 
    #         user_doc = self._db.collection('users').document(uid).get()
    #         if not user_doc.exists:
    #             raise ValueError("User does not exist")
 
    #         return user_doc.to_dict()
    #     except jwt.ExpiredSignatureError:
    #         raise ValueError("Token has expired")
    #     except jwt.InvalidTokenError:
    #         raise ValueError("Invalid token")
    async def get_user_by_token(self, token: str):
        """Retrieve user data by token from MySQL.

        Args:
            token (str): JWT token.

        Returns:
            User: User data if found, None otherwise.
        """
        try:
            # Giải mã token để lấy uid
            payload = jwt.decode(token, "your_jwt_secret", algorithms=["HS256"])
            uid = payload.get("uid")
            if not uid:
                raise ValueError("Invalid token")

            # Truy vấn MySQL để lấy user dựa trên uid
            result = await self.db.execute(select(User).where(User.id == uid))
            user = result.scalar_one_or_none()  # Lấy một đối tượng User hoặc None nếu không tìm thấy

            if not user:
                raise ValueError("User does not exist")

            return user
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

    # async def update_user_token(self, uid: str, token: str):
    #     """Cập nhật token của user trong Firestore."""
    #     try:
    #         user_ref = self._db.collection('users').document(uid)
    #         user_ref.update({
    #             'current_token': token  # Lưu token mới
    #         })
    #     except Exception as e:
    #         raise ValueError(f"Could not update token: {str(e)}")
    async def update_user_token(self, uid: str, token: str):
        """Cập nhật token của user trong MySQL."""
        try:
            # Truy vấn để lấy User có id là uid
            result = await self.db.execute(select(User).where(User.id == uid))
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError("User not found")

            # Cập nhật token mới
            user.current_token = token
            await self.db.commit()  # Commit thay đổi vào cơ sở dữ liệu

        except SQLAlchemyError as e:
            await self.db.rollback()  # Rollback nếu có lỗi
            raise ValueError(f"Could not update token: {str(e)}")
    
    # def get_all_topics_and_questions_by_uid(self, uid):
    #     """Get all topics and their questions based on user id.
 
    #     Args:
    #         uid (str): user id.
 
    #     Returns:
    #         dict: Dictionary with topics as keys and lists of questions as values.
    #     """
    #     user_ref = self._db.collection('users').document(uid)
    #     collections = user_ref.collections()
    #     all_data = {}
 
    #     for collection in collections:
    #         topic = collection.id
    #         documents = collection.stream()
    #         questions = []
    #         for doc in documents:
    #             data = doc.to_dict()
    #             # question = {
    #             #     'text': data['question'],
    #             #     'choices': [data['all_ans']['0'], data['all_ans']['1'], data['all_ans']['2'], data['all_ans']['3']],
    #             #     'correct_choice': data['crct_ans']
    #             # }
    #             # Kiểm tra loại dữ liệu của 'all_ans'
    #             if isinstance(data['all_ans'], list):
    #                 choices = data['all_ans']  # Sử dụng trực tiếp nếu là danh sách
    #             elif isinstance(data['all_ans'], dict):
    #                 choices = [data['all_ans']['0'], data['all_ans']['1'], data['all_ans']['2'], data['all_ans']['3']]
    #             else:
    #                 raise ValueError("Unexpected type for 'all_ans'")

    #             question = {
    #                 'text': data['question'],
    #                 'choices': choices,
    #                 'correct_choice': data['crct_ans']
    #             }
    #             questions.append(question)
    #         all_data[topic] = questions
       
    #     return all_data
    async def get_all_topics_and_questions_by_uid(self, uid: int):
        """Get all topics and their questions based on user id in MySQL.

        Args:
            uid (int): user id.

        Returns:
            dict: Dictionary with topics as keys and lists of questions as values.
        """
        try:
            all_data = {}

            # Truy vấn tất cả các câu hỏi của người dùng có id là `uid`
            # query = select(Question).where(Question.user_id == uid).options(selectinload(Question.choices))  # Tải sẵn các choices
            query = (
                select(Question)
                .where(Question.user_id == uid)
                .options(selectinload(Question.choices), selectinload(Question.comments), selectinload(Question.ratings))  # Tải sẵn các choices, comments và ratings
            )
            result = await self.db.execute(query)
            questions_list = result.scalars().all()  # Lấy tất cả các câu hỏi

            if not questions_list:
                raise ValueError(f"Topic '{topic}' does not exist for user '{uid}'.")

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

                user_data = await self.get_username_from_uid(uid)
                
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
    
    async def search_questions_by_keyword(self, uid: int, keyword: str):
        """
        Tìm kiếm tất cả các câu hỏi có chứa từ khóa trong Question.context hoặc Question.question_text.

        Args:
            keyword (str): Từ khóa tìm kiếm.

        Returns:
            dict: Dictionary với các topic là key và các danh sách câu hỏi là giá trị.
        """
        try:
            all_data = {}

            # Tìm kiếm tất cả các câu hỏi có chứa từ khóa trong `context` hoặc `question_text`
            query = (
                select(Question)
                .where(or_(Question.context.ilike(f"%{keyword}%"), Question.question_text.ilike(f"%{keyword}%")))
                .options(selectinload(Question.choices), selectinload(Question.comments), selectinload(Question.ratings))
            )
            result = await self.db.execute(query)
            questions_list = result.scalars().all()

            if not questions_list:
                return {"detail": f"No questions found with keyword '{keyword}'."}

            for question in questions_list:
                topic = question.topic

                # Lấy các lựa chọn cho câu hỏi
                choices: List[Choice] = question.choices
                choices_text = [choice.choice_text for choice in choices]

                # Lấy các bình luận cho câu hỏi
                comments: List[Comment] = question.comments
                comments_data = []
                for comment in comments:
                    username = await self.get_username_from_uid(comment.user_id)
                    comments_data.append({
                        'comment_id': comment.id,
                        'user_id': comment.user_id,
                        'comment_value': comment.comment_text,
                        'username': username
                    })

                # Lấy các đánh giá cho câu hỏi
                ratings: List[Rating] = question.ratings
                ratings_values = [rating.rating_value for rating in ratings]
                ratings_data = [{'rating_id': rating.id, 'rating_value': rating.rating_value} for rating in ratings]

                # Tính điểm trung bình của đánh giá
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
                    'comments': comments_data,
                    'ratings': ratings_data,
                    'average_rating': average_rating
                }

                # Thêm câu hỏi vào danh sách của topic
                if topic not in all_data:
                    all_data[topic] = []
                all_data[topic].append(question_data)

            return all_data

        except SQLAlchemyError as e:
            raise ValueError(f"Could not retrieve data: {str(e)}")
    
    # def delete_topic_by_uid(self, uid, topic):
    #     """Delete a topic from Firestore based on user id and topic.
 
    #     Args:
    #         uid (str): user id.
    #         topic (str): topic name.
 
    #     Returns:
    #         bool: True if deletion is successful, False otherwise.
    #     """
        
    #     doc_ref = self._db.collection('users').document(uid)
    #     collection_ref = doc_ref.collection(topic)
 
    #     # Kiểm tra xem collection có tồn tại hay không
    #     docs = collection_ref.stream()
    #     docs_list = list(docs)  # Chuyển iterator thành danh sách để kiểm tra độ dài

    #     if docs_list:
    #         # Nếu có tài liệu trong collection, tiến hành xóa chúng
                                        
    #         for doc in docs_list:
    #             doc.reference.delete()
    #         print(f"Collection {topic} has been deleted.")

    #         return True
    #     else:
    #         # Nếu không có tài liệu nào, collection không tồn tại hoặc đã rỗng
    #         print(f"Collection {topic} does not exist or is already empty.")
    #         return False
    async def delete_topic_by_uid(self, uid: int, topic: str) -> bool:
        """Delete a topic from MySQL based on user id and topic.

        Args:
            uid (int): user id.
            topic (str): topic name.

        Returns:
            bool: True if deletion is successful, False otherwise.
        """
        try:
            # Kiểm tra xem có câu hỏi nào với user_id và topic không
            result = await self.db.execute(
                select(Question).where(Question.user_id == uid, Question.topic == topic)
            )
            questions = result.scalars().all()

            if questions:
                # Nếu có câu hỏi, tiến hành xóa
                await self.db.execute(
                    delete(Question).where(Question.user_id == uid, Question.topic == topic)
                )
                await self.db.commit()
                print(f"Topic '{topic}' for user {uid} has been deleted.")
                return True
            else:
                # Nếu không có câu hỏi nào, topic không tồn tại hoặc đã rỗng
                print(f"Topic '{topic}' for user {uid} does not exist or is already empty.")
                return False

        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Could not delete topic: {str(e)}")
   
    # def delete_question_by_uid_and_topic(self, uid, topic, question_id):
    #     """Delete a question from Firestore based on user id, topic, and question id.
 
    #     Args:
    #         uid (str): user id.
    #         topic (str): topic name.
    #         question_id (str): question document id.
 
    #     Returns:
    #         bool: True if deletion is successful, False otherwise.
    #     """
    #     # Truy cập collection của topic
    #     collection_ref = self._db.collection('users').document(uid).collection(topic)
        
    #     # Kiểm tra xem collection có tồn tại hay không
    #     docs = collection_ref.stream()
    #     docs_list = list(docs)  # Chuyển iterator thành danh sách để kiểm tra độ dài

    #     if not docs_list:
    #         print(f"Topic {topic} does not exist or is already empty.")
                                                  
    #         return False

    #     # Truy cập tài liệu cụ thể trong collection
    #     doc_ref = collection_ref.document(question_id)

    #     # Kiểm tra xem question_id có tồn tại hay không
    #     if not doc_ref.get().exists:
    #         print(f"Question {question_id} does not exist in topic {topic}.")
    #         return False

    #     # Xóa tài liệu cụ thể trong collection
    #     doc_ref.delete()

    #     print(f"Question {question_id} in topic {topic} has been deleted.")
    #     return True
    async def delete_question_by_uid_and_topic(self, uid: int, topic: str, question_id: int) -> bool:
        """Delete a question from MySQL based on user id, topic, and question id.

        Args:
            uid (int): User ID.
            topic (str): Topic name.
            question_id (int): Question ID.

        Returns:
            bool: True if deletion is successful, False otherwise.
        """
        try:
            # Kiểm tra xem câu hỏi với `user_id`, `topic`, và `question_id` có tồn tại không
            result = await self.db.execute(
                select(Question).where(
                    Question.user_id == uid,
                    Question.topic == topic,
                    Question.id == question_id
                )
            )
            question = result.scalar_one_or_none()

            if not question:
                print(f"Question {question_id} does not exist in topic '{topic}' for user {uid}.")
                return False

            # Nếu câu hỏi tồn tại, tiến hành xóa
            await self.db.execute(
                delete(Question).where(
                    Question.user_id == uid,
                    Question.topic == topic,
                    Question.id == question_id
                )
            )
            await self.db.commit()
            
            print(f"Question {question_id} in topic '{topic}' for user {uid} has been deleted.")
            return True

        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Could not delete question: {str(e)}")
       
    # def delete_user(self, uid):
    #     """Delete a user from Firestore based on user id.
 
    #     Args:
    #         uid (str): user id.
 
    #     Returns:
    #         bool: True if deletion is successful, False otherwise.
    #     """
    #     try:
    #         user_ref = self._db.collection('users').document(uid)
    #         user_ref.delete()
    #         return True
    #     except Exception as e:
    #         print(f"Error deleting user: {e}")
    #         return False
    async def delete_user(self, uid: int) -> bool:
        """Delete a user from MySQL based on user id.

        Args:
            uid (int): User ID.

        Returns:
            bool: True if deletion is successful, False otherwise.
        """
        try:
            # Kiểm tra xem người dùng có tồn tại không
            result = await self.db.execute(select(User).where(User.id == uid))
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User with ID {uid} does not exist.")

            # Lấy người dùng theo UID
            stmt = select(User).where(User.id == uid)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User not found")

            # Lấy tất cả các câu hỏi của người dùng
            stmt = select(Question).where(Question.user_id == uid)
            result = await self.db.execute(stmt)
            questions = result.scalars().all()

            # Xóa tất cả các câu hỏi và các liên kết liên quan
            for question in questions:
                await self.db.execute(delete(Choice).where(Choice.question_id == question.id))
                await self.db.execute(delete(Comment).where(Comment.question_id == question.id))
                await self.db.execute(delete(Rating).where(Rating.question_id == question.id))
                await self.db.delete(question)

            # Xóa người dùng
            await self.db.delete(user)

            # Lưu thay đổi
            await self.db.commit()

            return {"status": "success", "message": f"User {uid} and all related data deleted successfully"}
        except SQLAlchemyError as e:
            await self.db.rollback()
            return ValueError(f"Error deleting user: {e}")

    # def change_user_info(self, uid, new_email, new_username):
    #     """Change user information in Firestore based on user id.
    #         Args:
    #             uid (str): user id.
    #             new_email (str): new email.
    #             new_username (str):
    #         Returns:
    #             bool: True if change is successful, False otherwise.
    #     """
    #     try:
    #         user_ref = self._db.collection('users').document(uid)
    #         user_ref.update({'email': new_email,
    #                          'username': new_username})
    #         return True
    #     except Exception as e:
    #         print(f"Error changing user info: {e}")
    #         return False
    async def change_user_info(self, uid: int, new_email: str, new_username: str) -> bool:
        """Change user information in MySQL based on user id.

        Args:
            uid (int): User ID.
            new_email (str): New email.
            new_username (str): New username.

        Returns:
            bool: True if change is successful, False otherwise.
        """
        try:
            # Cập nhật thông tin người dùng
            stmt = (
                update(User).
                where(User.id == uid).
                values(email=new_email, username=new_username)
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            print(f"User info for ID {uid} has been updated.")
            return True

        except SQLAlchemyError as e:
            await self.db.rollback()
            print(f"Error changing user info: {e}")
            return False

    def upload_avatar(self, uid: str, file):
        """Upload avatar for a user and update Firestore.

        Args:
            uid (str): User ID.
            file: File object of the avatar image.

        Returns:
            str: Public URL of the uploaded avatar.
        """
        # Initialize the Cloud Storage client
        storage_client = storage.Client()
        bucket_name = 'nabingx_bucket'
        bucket = storage_client.bucket(bucket_name)

        # Create a new blob and upload the file's content.
        blob = bucket.blob(f'avatars/{uid}/{file.filename}')
        blob.upload_from_file(file.file)

        # No need to call make_public() because we're using uniform bucket-level access
        # Instead, configure the bucket IAM policy to allow public access to objects if needed

        # Make the blob public
        blob.make_public()

        # Update Firestore with the avatar URL
        avatar_url = blob.public_url
        user_ref = self._db.collection('users').document(uid)
        user_ref.update({'avatar': avatar_url})

        return avatar_url

    # def change_topic_name(self, uid: str, old_topic: str, new_topic: str):
    #     """Change the name of a topic in Firestore based on user id.
 
    #     Args:
    #         uid (str): user id.
    #         old_topic (str): old topic name.
    #         new_topic (str): new topic name.
 
    #     Returns:
    #         bool: True if change is successful, False otherwise.
    #     """
    #     # Lấy tài liệu của user
    #     user_doc_ref = self._db.collection('users').document(uid)
    #     old_topic_ref = user_doc_ref.collection(old_topic)
    #     new_topic_ref = user_doc_ref.collection(new_topic)
 
    #     # Lấy tất cả các tài liệu từ collection topic cũ
    #     documents = old_topic_ref.stream()
    #     # Sao chép các tài liệu từ topic cũ sang topic mới
    #     for doc in documents:
    #         doc_dict = doc.to_dict()
    #         new_topic_ref.document(doc.id).set(doc_dict)
 
    #     # Xóa collection topic cũ
    #     if not  self.delete_topic_by_uid(uid, old_topic):
    #         raise ValueError(f"Topic {old_topic} does not exist or is already empty.")
    #     return {'status': 200, 'message': f'Topic {old_topic} name changed to {new_topic} successfully'}
    async def change_topic_name(self, uid: str, old_topic: str, new_topic: str) -> dict:
        """Change the name of a topic in MySQL based on user id.

        Args:
            uid (str): user id.
            old_topic (str): old topic name.
            new_topic (str): new topic name.

        Returns:
            dict: Status message indicating the result of the operation.
        """
        try:
            # Cập nhật tên topic trong bảng questions
            stmt = (
                update(Question)  # Giả sử Question là model tương ứng với bảng questions
                .where(Question.user_id == uid, Question.topic == old_topic)
                .values(topic=new_topic)
            )

            await self.db.execute(stmt)
            await self.db.commit()

            return {'status': 200, 'message': f'Topic {old_topic} name changed to {new_topic} successfully'}

        except SQLAlchemyError as e:
            await self.db.rollback()
            print(f"Error changing topic name: {e}")
            return {'status': 500, 'message': 'Failed to change topic name'}
   
    # def update_question(self, uid: str, topic: str, question_id: str, new_info: dict):
    #     """Update a question in Firestore based on user id, topic, and question id.
 
    #     Args:
    #         uid (str): user id.
    #         topic (str): topic name.
    #         question_id (str): question document id.
    #         new_info (dict): new question information.
 
    #     Returns:
    #         bool: True if update is successful, False otherwise.
    #     """
    #     # Truy cập collection của topic
    #     question_ref = self._db.collection('users').document(uid).collection(topic).document(question_id)
       
    #     if not question_ref.get().exists:
    #         raise ValueError(f"Question {question_id} does not exist in topic {topic}.")
    #     question_ref.update(new_info)
    #     return {"status": "success", "message": f"Question {question_id} of topic {topic} updated successfully"}
    async def update_question(self, uid: str, question_id: str, new_info: dict) -> dict:
        """Update a question in MySQL based on user id and question id.

        Args:
            uid (str): user id.
            question_id (str): question document id.
            new_info (dict): new question information.

        Returns:
            dict: Status message indicating the result of the operation.
        """
        try:
            # Tách riêng các trường cho bảng Question và Choice
            # question_data = {key: value for key, value in new_info.items() if key in Question.__table__.columns.keys()}
            question_data = {key: value for key, value in new_info.items()}
            print(question_data)
            choice_data = new_info.get('all_ans', [])
            print(choice_data)

            # Cập nhật câu hỏi trong bảng Question
            if question_data:
                stmt = (
                    update(Question)
                    .where(Question.user_id == uid, Question.id == question_id)
                    # .values(**question_data)
                    .values(
                        context = question_data.get('context'),
                        topic = question_data.get('topic'),
                        correct_choice = question_data.get('correct_choice'),
                        question_text = question_data.get('question_text'),
                        tags = question_data.get('tags')  # Lưu chuỗi tags
                    )
                )
                result = await self.db.execute(stmt)

                # Kiểm tra xem câu hỏi có tồn tại không
                if result.rowcount == 0:
                    raise ValueError(f"Question {question_id} does not exist.")

            # Nếu có dữ liệu cho bảng Choice, cập nhật choices
            if choice_data:
                # Xóa các choices hiện tại
                await self.db.execute(
                    delete(Choice).where(Choice.question_id == question_id)
                )

                # Thêm các lựa chọn mới
                for choice_text in choice_data.values():
                    new_choice = Choice(question_id=question_id, choice_text=choice_text)
                    self.db.add(new_choice)

                await self.db.commit()

            return {"status": "success", "message": f"Question {question_id} updated successfully"}

        except SQLAlchemyError as e:
            await self.db.rollback()
            print(f"Error updating question: {e}")
            return {"status": "error", "message": {e}}
    
    async def add_or_update_rating(self, user_id: int, question_id: int, rating_value: int):
        # Tìm câu hỏi cụ thể
        result = await self.db.execute(select(Question).where(Question.id == question_id))
        question = result.scalars().first()
        
        if not question:
            raise ValueError("Question not found")

        # Kiểm tra xem người dùng đã đánh giá câu hỏi chưa
        result = await self.db.execute(select(Rating).where(Rating.question_id == question_id, Rating.user_id == user_id))
        existing_rating = result.scalars().first()

        if existing_rating:
            # Nếu đã có rating, cập nhật giá trị mới
            existing_rating.rating_value = rating_value
        else:
            # Nếu chưa có rating, tạo mới
            new_rating = Rating(question_id=question_id, user_id=user_id, rating_value=rating_value, created_at=datetime.datetime.now(datetime.timezone.utc))
            self.db.add(new_rating)

        # Lưu thay đổi vào DB
        await self.db.commit()

        # Tính toán điểm trung bình
        result = await self.db.execute(select(Rating).where(Rating.question_id == question_id))
        all_ratings = result.scalars().all()
        average_rating = sum(r.rating_value for r in all_ratings) / len(all_ratings) if all_ratings else 0

        return average_rating, all_ratings  # Trả về điểm trung bình và danh sách rating
    
    async def add_comment(self, user_id: int, question_id: int, comment: int):
        # Tìm câu hỏi cụ thể
        result = await self.db.execute(select(Question).where(Question.id == question_id))
        question = result.scalars().first()
        
        if not question:
            raise ValueError("Question not found")

        # Kiểm tra xem người dùng đã đánh giá câu hỏi chưa
        result = await self.db.execute(select(Comment).where(Comment.question_id == question_id, Comment.user_id == user_id))

        # Nếu chưa có comment, tạo mới
        new_comment = Comment(question_id=question_id, user_id=user_id, comment_text=comment, created_at=datetime.datetime.now(datetime.timezone.utc))
        self.db.add(new_comment)

        # Lưu thay đổi vào DB
        await self.db.commit()

        result = await self.db.execute(select(Comment).where(Comment.question_id == question_id))
        all_comments = result.scalars().all()

        return new_comment, all_comments  # Trả về bình luận mới tạo và tất cả bình luận cho câu hỏi đó
    
    # def aiken_format(self, questions: List[Question]):
    #     # Chuẩn bị nội dung cho file Aiken
    #     aiken_format_content = ""
    #     for question in questions:
    #         aiken_format_content += f"{question.question_text}\n"
    #         choices: List[Choice] = self.db.execute(select(Choice).filter(Choice.question_id == question.id)).all()
    #         for idx, choice in enumerate(choices):
    #             aiken_format_content += f"{chr(65 + idx)}. {choice.choice_text}\n"
    #         correct_choice_index = next(
    #             (idx for idx, choice in enumerate(question.choices) if choice.choice_text == question.correct_choice),
    #             None
    #         )
    #         if correct_choice_index is not None:
    #             correct_choice = chr(65 + correct_choice_index)
    #             aiken_format_content += f"ANSWER: {correct_choice}\n\n"
    async def generate_aiken_content(self, questions: List[Question]) -> str:
        """Chuyển đổi danh sách các câu hỏi sang định dạng Aiken."""
        aiken_content = ""
        for question in questions:
            aiken_content += f"{question['text']}\n"  # Thêm câu hỏi
            
            # Lấy các lựa chọn từ quan hệ `choices`
            choices = question['choices']
            print(choices)
            for idx, choice in enumerate(choices):
                aiken_content += f"{chr(65 + idx)}. {choice}\n"
            
            # Xác định lựa chọn đúng
            correct_choice_index = next(
                (idx for idx, choice in enumerate(choices) if choice == question['correct_choice']),
                None
            )
            
            if correct_choice_index is not None:
                correct_answer_letter = chr(65 + correct_choice_index)
                aiken_content += f"ANSWER: {correct_answer_letter}\n\n"
        
        return aiken_content
    
    async def generate_moodle_xml_content(self, questions: List[dict]) -> str:
        """Chuyển đổi danh sách các câu hỏi sang định dạng Moodle XML."""
        
        quiz = ET.Element("quiz")

        for question in questions:
            question_elem = ET.SubElement(quiz, "question", type="multichoice")

            # Thêm tên câu hỏi
            name_elem = ET.SubElement(question_elem, "name")
            name_text = ET.SubElement(name_elem, "text")
            name_text.text = question['text']  # Câu hỏi

            # Thêm nội dung câu hỏi
            questiontext_elem = ET.SubElement(question_elem, "questiontext", format="html")
            questiontext_text = ET.SubElement(questiontext_elem, "text")
            questiontext_text.text = f"<![CDATA[{question['text']}]]>"

            # Thêm các lựa chọn
            for choice in question['choices']:
                answer_elem = ET.SubElement(question_elem, "answer", fraction="100" if choice == question['correct_choice'] else "0")
                answer_text = ET.SubElement(answer_elem, "text")
                answer_text.text = choice

                feedback_elem = ET.SubElement(answer_elem, "feedback")
                feedback_text = ET.SubElement(feedback_elem, "text")
                feedback_text.text = "Correct!" if choice == question['correct_choice'] else "Incorrect."

        # Chuyển đổi đối tượng XML thành chuỗi
        return ET.tostring(quiz, encoding="unicode", method="xml")
    
    async def delete_rating(self, rating_id: int, uid: int):
        """
        Xóa đánh giá nếu người dùng là chủ sở hữu của câu hỏi hoặc của đánh giá.

        Args:
            uid (int): ID của người dùng yêu cầu xóa đánh giá.
            rating_id (int): ID của đánh giá cần xóa.

        Returns:
            str: Thông báo kết quả xóa thành công hoặc lý do thất bại.
        """
        try:
            # Truy vấn để kiểm tra sự tồn tại của rating
            query = select(Rating).where(Rating.id == rating_id)
            result = await self.db.execute(query)
            rating = result.scalar_one_or_none()

            if rating is None:
                raise ValueError(f"Rating with ID {rating_id} does not exist.")
            
            # Kiểm tra quyền sở hữu dựa trên uid của người dùng
            query_question = select(Question).where(Question.id == rating.question_id)
            result_question = await self.db.execute(query_question)
            question = result_question.scalar_one_or_none()

            if not question:
                return {"detail": "Question không tồn tại."}

            # Xác nhận người dùng là chủ sở hữu của question hoặc của rating
            if question.user_id != uid and rating.user_id != uid:
                return {"detail": "Không có quyền xóa đánh giá này."}

            # Xóa rating
            await self.db.delete(rating)
            await self.db.commit()

            return {"message": f"Rating with ID {rating_id} has been deleted successfully."}

        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Failed to delete rating: {str(e)}")
    
    async def delete_comment(self, comment_id: int, uid: int):
        """
        Xóa đánh giá nếu người dùng là chủ sở hữu của câu hỏi hoặc của đánh giá.

        Args:
            uid (int): ID của người dùng yêu cầu xóa đánh giá.
            comment_id (int): ID của bình luận cần xóa.

        Returns:
            str: Thông báo kết quả xóa thành công hoặc lý do thất bại.
        """
        try:
            # Truy vấn để kiểm tra sự tồn tại của rating
            query = select(Comment).where(Comment.id == comment_id)
            result = await self.db.execute(query)
            comment = result.scalar_one_or_none()

            if comment is None:
                raise ValueError(f"Rating with ID {comment_id} does not exist.")
            
            # Kiểm tra quyền sở hữu dựa trên uid của người dùng
            query_question = select(Question).where(Question.id == comment.question_id)
            result_question = await self.db.execute(query_question)
            question = result_question.scalar_one_or_none()

            if not question:
                return {"detail": "Question không tồn tại."}

            # Xác nhận người dùng là chủ sở hữu của question hoặc của rating
            if question.user_id != uid and comment.user_id != uid:
                return {"detail": "Không có quyền xóa đánh giá này."}

            # Xóa rating
            await self.db.delete(comment)
            await self.db.commit()

            return {"message": f"Rating with ID {comment_id} has been deleted successfully."}

        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValueError(f"Failed to delete rating: {str(e)}")
    
    async def change_topic_name(self, uid: int, old_topic: str, new_topic: str):
        """API để thay đổi tên topic của các câu hỏi, nếu user là chủ sở hữu của câu hỏi.

        Args:
            uid (int): ID của người dùng cần xác thực quyền sở hữu câu hỏi.
            old_topic (str): Tên topic cũ cần đổi.
            new_topic (str): Tên topic mới sẽ thay thế.

        Returns:
            dict: Kết quả thông báo thành công hoặc lỗi.
        """
        try:
            # Truy vấn các câu hỏi có `topic` là `old_topic` và `user_id` là `uid`
            query = (
                select(Question)
                .where(Question.topic == old_topic, Question.user_id == uid)
            )
            result = await self.db.execute(query)
            questions_list = result.scalars().all()

            if not questions_list:
                return {"detail": "Không tìm thấy câu hỏi nào với topic này hoặc người dùng không có quyền."}

            # Cập nhật topic cho các câu hỏi thuộc `old_topic` và có user_id là `uid`
            update_query = (
                update(Question)
                .where(Question.topic == old_topic, Question.user_id == uid)
                .values(topic=new_topic)
            )
            await self.db.execute(update_query)
            await self.db.commit()

            return {"detail": f"Đã đổi tên topic từ '{old_topic}' thành '{new_topic}' thành công."}

        except SQLAlchemyError as e:
            await self.db.rollback()
            return {"detail": f"Lỗi khi thay đổi tên topic: {str(e)}"}
    
    async def update_avatar_url(self, uid: int, avatar_url: str):
        """
        Cập nhật avatar URL mới cho người dùng dựa trên user ID.

        Args:
            uid (int): ID của người dùng.
            avatar_url (str): Đường dẫn URL của avatar mới.

        Raises:
            ValueError: Nếu không tìm thấy người dùng hoặc có lỗi truy vấn cơ sở dữ liệu.
        """
        try:
            # Truy vấn lấy user dựa trên uid
            query = select(User).where(User.id == uid)
            result = await self.db.execute(query)
            user = result.scalars().first()

            # Kiểm tra nếu user tồn tại, cập nhật avatar_url
            if user:
                user.avatar = avatar_url
                await self.db.commit()  # Lưu thay đổi vào database
            else:
                raise ValueError(f"Không tìm thấy người dùng với ID: {uid}")

        except SQLAlchemyError as e:
            await self.db.rollback()  # Hoàn tác nếu có lỗi
            raise ValueError(f"Lỗi truy vấn cơ sở dữ liệu: {str(e)}")
    
    async def delete_user_question(self, uid: int, question_id: int) -> dict:
        """
        Xóa câu hỏi của người dùng cùng với các liên kết liên quan.

        Args:
            uid (int): ID của người dùng.
            question_id (int): ID của câu hỏi.

        Returns:
            dict: Trạng thái của thao tác xóa.
        """
        try:
            # Kiểm tra câu hỏi có tồn tại và thuộc về người dùng
            stmt = select(Question).where(Question.user_id == uid, Question.id == question_id)
            result = await self.db.execute(stmt)
            question = result.scalar_one_or_none()

            if not question:
                raise ValueError(f"Question not found or unauthorized")

            # Xóa tất cả Choice liên quan đến câu hỏi
            await self.db.execute(delete(Choice).where(Choice.question_id == question_id))
            
            # Xóa tất cả Comment liên quan đến câu hỏi
            await self.db.execute(delete(Comment).where(Comment.question_id == question_id))
            
            # Xóa tất cả Rating liên quan đến câu hỏi
            await self.db.execute(delete(Rating).where(Rating.question_id == question_id))
            
            # Xóa câu hỏi sau khi xóa các liên kết liên quan
            await self.db.delete(question)
            
            # Lưu thay đổi
            await self.db.commit()

            return {"status": "success", "message": f"Question {question_id} and related data deleted successfully"}

        except SQLAlchemyError as e:
            await self.db.rollback()
            print(f"Error deleting question: {e}")
            raise ValueError(f"Failed to delete question: {e}")
    
    async def delete_user_topic(self, uid: int, topic: str) -> dict:
        """
        Xóa tất cả các câu hỏi của người dùng với topic chỉ định và các liên kết liên quan.

        Args:
            uid (int): ID của người dùng.
            topic (str): Tên topic của câu hỏi.

        Returns:
            dict: Trạng thái của thao tác xóa.
        """
        try:
            # Lấy tất cả câu hỏi có cùng topic của người dùng
            stmt = select(Question).where(Question.user_id == uid, Question.topic == topic)
            result = await self.db.execute(stmt)
            questions = result.scalars().all()

            if not questions:
                raise ValueError(f"No questions found with the specified topic for the user")

            # Xóa tất cả liên kết liên quan đến từng câu hỏi
            for question in questions:
                # Xóa Choices liên quan đến câu hỏi
                await self.db.execute(delete(Choice).where(Choice.question_id == question.id))
                
                # Xóa Comments liên quan đến câu hỏi
                await self.db.execute(delete(Comment).where(Comment.question_id == question.id))
                
                # Xóa Ratings liên quan đến câu hỏi
                await self.db.execute(delete(Rating).where(Rating.question_id == question.id))

                # Xóa câu hỏi
                await self.db.delete(question)

            # Lưu thay đổi
            await self.db.commit()

            return {"status": "success", "message": f"All questions with topic '{topic}' for user {uid} deleted successfully"}

        except SQLAlchemyError as e:
            await self.db.rollback()
            print(f"Error deleting questions by topic: {e}")
            raise ValueError(f"Failed to delete questions by topic: {e}")
        
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