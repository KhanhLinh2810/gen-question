"""This module handles all Firebase Firestore services.

@Author: Karthick T. Sharma
"""

import firebase_admin

from firebase_admin import firestore
from firebase_admin import credentials
from googletrans import Translator


def english_to_vietnamese(text):
    translator = Translator()
    translated_text = translator.translate(text, src='en', dest='vi')
    return translated_text.text

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
            print(all_ans)
            doc_ref.collection(english_to_vietnamese(request.name)).document(str(idx)).set(q_dict)
