"""This module handles all Firebase Firestore services.

@Author: Karthick T. Sharma
"""

import firebase_admin

from firebase_admin import firestore
from firebase_admin import credentials
from deep_translator import GoogleTranslator
import bcrypt
import jwt
import datetime
import uuid

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)


def english_to_vietnamese(text):
    translator = GoogleTranslator(source='en', target='vi')
    translated_text = translator.translate(text)
    return translated_text

class FirebaseService:
    """Handle firestore operations."""

    def __init__(self):
        """Initialize firebase firestore client."""
        firebase_admin.initialize_app(
            credentials.Certificate("secret/serviceAccountKey.json"))
        self._db = firestore.client()

    def update_generated_status(self, request, status):
        """Change status of 'GeneratorWorking' is firestore.

        Args:
            request (ModelInput): request format from flutter.
            status (bool): state whether question generated.
        """

        if not isinstance(status, bool):
            raise TypeError("'status' must be a bool value")

        doc_ref = self._db.collection('users').document(request.uid)
        doc_ref.update({'GeneratorWorking': status})

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

    def check_duplicates(self, request, question, answers):
        """Kiểm tra câu hỏi và đáp án có trùng lặp trong database không.

        Args:
            request (ModelInput): yêu cầu từ người dùng.
            question (str): câu hỏi cần kiểm tra.
            answers (list[str]): các đáp án cần kiểm tra.

        Returns:
            dict: thông tin trùng lặp nếu có.
        """
        doc_ref = self._db.collection('users').document(request.uid)
        collection_name = english_to_vietnamese(request.name)
        collection_ref = doc_ref.collection(collection_name)
        documents = collection_ref.stream()
        
        duplicate_info = {
            'duplicate_questions': [],
            'duplicate_answers': []
        }

        # Lặp qua các tài liệu trong collection
        for idx, doc in enumerate(documents):
            data = doc.to_dict()

            # Kiểm tra nếu câu hỏi trùng lặp
            if data['question'] == question:
                duplicate_info['duplicate_questions'].append(idx)

            # Kiểm tra các đáp án trùng lặp
            for answer in answers:
                if answer in data['all_ans'].values():
                    duplicate_info['duplicate_answers'].append({'index': idx, 'answer': answer})

        # Trả về thông tin về các câu hỏi và đáp án trùng lặp
        return duplicate_info
    
    def send_results_to_fs(self, request, questions, crct_ans, all_ans, context):
        """Send generated question to appropiate fs doc.

        Args:
            request (ModelInput): request format from flutter.
            questions (list[str]): list of generated questions.
            crct_ans (list[str]): list of correct answers.
            all_ans (list[str]): list of all answers squeezed together.
            context (str): input corpus used to generate questions.
        """

        self.__validate(questions=questions,
                        crct_ans=crct_ans, all_ans=all_ans)

        doc_ref = self._db.collection('users').document(request.uid)
        print(all_ans)
        results = []
        for idx, question in enumerate(questions):
            q_dict = {
                'context': english_to_vietnamese(context),
                'question': english_to_vietnamese(question),
                'crct_ans': english_to_vietnamese(crct_ans[idx]),
                # 'all_ans': all_ans[idx * 4: 4 + idx * 4]
                'all_ans': {
                    '0': english_to_vietnamese(all_ans[idx * 4]),
                    '1': english_to_vietnamese(all_ans[idx * 4 + 1]),
                    '2': english_to_vietnamese(all_ans[idx * 4 + 2]),
                    '3': english_to_vietnamese(all_ans[idx * 4 + 3])
                }
            }
            
            collection_name = english_to_vietnamese(request.name)
            collection_ref = doc_ref.collection(collection_name)

            
            # # Kiểm tra xem tên collection đã tồn tại chưa
            # if collection_ref.get():
            #     # Collection đã tồn tại, cập nhật dữ liệu
            #     doc_ref.collection(collection_name).document(str(idx)).update(q_dict)
            #     print("Dữ liệu đã được cập nhật trong collection", collection_name)
            # else:
            #     # Collection chưa tồn tại, tạo mới
            #     doc_ref.collection(collection_name).document(str(idx)).set(q_dict)
            #     print("Dữ liệu đã được thêm vào collection", collection_name)
            
            
            # # Sử dụng ID tự động của Firestore để tạo tài liệu mới
            # collection_ref.add(q_dict)
            # print("Dữ liệu đã được thêm vào collection", collection_name)

            
            # Kiểm tra trùng lặp
            duplicate_info = self.check_duplicates(request, q_dict['question'], list(q_dict['all_ans'].values()))
            
            # Lấy số lượng tài liệu hiện có trong collection
            current_documents = collection_ref.get()
            current_count = len(current_documents)

            # results = []  # Danh sách để lưu trữ kết quả

            # Sử dụng current_count + idx để tạo ID tài liệu tuần tự
            document_id = str(current_count + idx)
            collection_ref.document(document_id).set(q_dict)
            print("Dữ liệu đã được thêm vào collection", collection_name, "với document ID:", document_id)

            # Lưu lại thông tin về collection name, document ID và dữ liệu đã lưu vào danh sách results
            results.append({
                'collection_name': collection_name,
                'document_id': document_id,
                'data': q_dict,
                'duplicate_info': duplicate_info
            })
        # Trả về danh sách results sau khi hoàn tất quá trình lưu trữ
        return results
    
    def __validate_export_input(self, uid, name):
        """Validate export input data

        Args:
            uid (str): user id.
            name (str): topic name.

        Raises:
            ValueError: If any input is invalid.
        """
        if not uid or not isinstance(uid, str):
            raise ValueError("'uid' must be a non-empty string")

        if not name or not isinstance(name, str):
            raise ValueError("'name' must be a non-empty string")

    def get_questions_by_uid_and_topic(self, uid, topic):
        """Get questions from Firestore based on user id and topic.

        Args:
            uid (str): user id.
            topic (str): topic name.

        Returns:
            list[dict]: list of questions with their answers.
        """
        self.__validate_export_input(uid, topic)  # Validate inputs

        doc_ref = self._db.collection('users').document(uid)
        collection_ref = doc_ref.collection(topic)  # Không cần dịch topic
        documents = collection_ref.stream()  # Lấy tất cả các tài liệu trong collection
        questions = []
        for doc in documents:
            data = doc.to_dict()
            print(data['question'])
            print([data['all_ans']['0'], data['all_ans']['1'], data['all_ans']['2'], data['all_ans']['3']])
            print(str([data['all_ans']['0'], data['all_ans']['1'], data['all_ans']['2'], data['all_ans']['3']].index(data['crct_ans'])))
            question = {
                'text': data['question'],
                'choices': [data['all_ans']['0'], data['all_ans']['1'], data['all_ans']['2'], data['all_ans']['3']],
                'correct_choice': data['crct_ans']
            }
            questions.append(question)
        return questions

    def create_user(self, email: str, username: str, password: str):
        """Create a new user with a unique UID.

        Args:
            email (str): User's email.
            username (str): User's username.
            password (str): User's password.

        Returns:
            dict: User's information including UID.
        """
        users_ref = self._db.collection('users')
        
        # Check if email or username already exists
        email_query = users_ref.where('email', '==', email).get()
        if email_query:
            raise ValueError("Email already exists")
        
        username_query = users_ref.where('username', '==', username).get()
        if username_query:
            raise ValueError("Username already exists")
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create a unique UID
        uid = str(uuid.uuid4())
        
        # Save the user to Firestore
        user_data = {
            'uid': uid,
            'email': email,
            'username': username,
            'password': hashed_password.decode('utf-8')
        }
        users_ref.document(uid).set(user_data)
        
        return user_data

    def authenticate_user(self, identifier, password):
        """Authenticate a user with email/username and password.

        Args:
            identifier (str): User's email or username.
            password (str): User's password.

        Returns:
            str: JWT token if authentication is successful.
        """
        users_ref = self._db.collection('users')
        
        # Check if the identifier is an email or username
        user_query = users_ref.where('email', '==', identifier).get()
        if not user_query:
            user_query = users_ref.where('username', '==', identifier).get()
        
        if not user_query:
            raise ValueError("Invalid email/username or password")
        
        user_data = user_query[0].to_dict()
        
        # Check the password
        if not bcrypt.checkpw(password.encode('utf-8'), user_data['password'].encode('utf-8')):
            raise ValueError("Invalid email/username or password")
        
        # Generate a JWT token
        token = jwt.encode({
            'uid': user_data['uid'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, 'your_jwt_secret', algorithm='HS256')
        
        return token, user_data['uid']

    def get_user_by_email(self, email):
        """Retrieve user data by email from Firestore.

        Args:
            email (str): Email to search for in Firestore.

        Returns:
            dict: User data if found, None otherwise.
        """
        users_ref = self._db.collection('users')
        query = users_ref.where('email', '==', email).limit(1).get()
        
        for user in query:
            return user.to_dict()

        return None

    def get_user_by_username(self, username):
        """Retrieve user data by username from Firestore.

        Args:
            username (str): Username to search for in Firestore.

        Returns:
            dict: User data if found, None otherwise.
        """
        users_ref = self._db.collection('users')
        query = users_ref.where('username', '==', username).limit(1).get()
        
        for user in query:
            return user.to_dict()

        return None

    def change_password_func(self, uid: str, current_password: str, new_password: str):
        """
            Change password of a user in Firestore.
            Args:
                uid (str): User's uid.
                current_password (str): User's current password.
                new_password (str): User's new password.
            Returns:
                dict: Success message if password change is successful.
        """
        users_ref = self._db.collection('users').document(uid)
        user_data = users_ref.get().to_dict()
       
        # Kiểm tra mật khẩu hiện tại
        if not bcrypt.checkpw(current_password.encode('utf-8'), user_data['password'].encode('utf-8')):
            raise ValueError("Invalid password")
 
        # Hash mật khẩu mới
        new_hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
       
        # Cập nhật mật khẩu mới trong Firestore
        users_ref.update({'password': new_hashed_password})
       
        return {'message': 'Password changed successfully'}
 
    def get_user_by_token(self, token: str):
        try:
            payload = jwt.decode(token, "your_jwt_secret", algorithms=["HS256"])
            uid = payload.get("uid")
            if not uid:
                raise ValueError("Invalid token")
 
            user_doc = self._db.collection('users').document(uid).get()
            if not user_doc.exists:
                raise ValueError("User does not exist")
 
            return user_doc.to_dict()
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

    def get_all_topics_and_questions_by_uid(self, uid):
        """Get all topics and their questions based on user id.
 
        Args:
            uid (str): user id.
 
        Returns:
            dict: Dictionary with topics as keys and lists of questions as values.
        """
        user_ref = self._db.collection('users').document(uid)
        collections = user_ref.collections()
        all_data = {}
 
        for collection in collections:
            topic = collection.id
            documents = collection.stream()
            questions = []
            for doc in documents:
                data = doc.to_dict()
                question = {
                    'text': data['question'],
                    'choices': [data['all_ans']['0'], data['all_ans']['1'], data['all_ans']['2'], data['all_ans']['3']],
                    'correct_choice': data['crct_ans']
                }
                questions.append(question)
            all_data[topic] = questions
       
        return all_data
    def delete_topic_by_uid(self, uid, topic):
        """Delete a topic from Firestore based on user id and topic.
 
        Args:
            uid (str): user id.
            topic (str): topic name.
 
        Returns:
            bool: True if deletion is successful, False otherwise.
        """
        try:
            doc_ref = self._db.collection('users').document(uid)
            collection_ref = doc_ref.collection(topic)
 
            # Xóa tất cả các tài liệu trong collection trước
            docs = collection_ref.stream()
            for doc in docs:
                doc.reference.delete()
 
            # Sau đó xóa collection (topic)
            collection_ref = doc_ref.collection(topic).document()
            collection_ref.delete()
 
            return True
        except Exception as e:
            print(f"Error deleting topic: {e}")
            return False
   
    def delete_question_by_uid_and_topic(self, uid, topic, question_id):
        """Delete a question from Firestore based on user id, topic, and question id.
 
        Args:
            uid (str): user id.
            topic (str): topic name.
            question_id (str): question document id.
 
        Returns:
            bool: True if deletion is successful, False otherwise.
        """
        try:
            doc_ref = self._db.collection('users').document(uid)
            collection_ref = doc_ref.collection(topic)
 
            # Xóa tài liệu cụ thể trong collection
            collection_ref.document(question_id).delete()
 
            return True
        except Exception as e:
            print(f"Error deleting question: {e}")
            return False
       
    def delete_user(self, uid):
        """Delete a user from Firestore based on user id.
 
        Args:
            uid (str): user id.
 
        Returns:
            bool: True if deletion is successful, False otherwise.
        """
        try:
            user_ref = self._db.collection('users').document(uid)
            user_ref.delete()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    def change_user_info(self, uid, new_email, new_username):
        """Change user information in Firestore based on user id.
            Args:
                uid (str): user id.
                new_email (str): new email.
                new_username (str):
            Returns:
                bool: True if change is successful, False otherwise.
        """
        try:
            user_ref = self._db.collection('users').document(uid)
            user_ref.update({'email': new_email,
                             'username': new_username})
            return True
        except Exception as e:
            print(f"Error changing user info: {e}")
            return False
