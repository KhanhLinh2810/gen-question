"""This module handles all Firebase Firestore services.

@Author: Karthick T. Sharma
"""

import firebase_admin

from firebase_admin import firestore
from firebase_admin import credentials
from deep_translator import GoogleTranslator


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
                'data': q_dict
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
    