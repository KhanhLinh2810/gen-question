"""Main python file for flask application.

This module handles all API requests.

@Author: Karthick T. Sharma
"""

# pylint: disable=no-name-in-module
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Header, File, UploadFile
from pydantic import BaseModel, EmailStr, constr
from fastapi.responses import JSONResponse, FileResponse
import re
import xml.etree.ElementTree as ET
from auth import JWTBearer

from src.inferencehandler import inference_handler
from src.ansgenerator.false_answer_generator import FalseAnswerGenerator
from src.model.abstractive_summarizer import AbstractiveSummarizer
from src.model.question_generator import QuestionGenerator
from src.model.keyword_extractor import KeywordExtractor
from src.service.firebase_service import FirebaseService
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta
from typing import Optional


# initialize fireabse client
fs = FirebaseService()

# initialize question and ans models
summarizer = AbstractiveSummarizer()
question_gen = QuestionGenerator()
false_ans_gen = FalseAnswerGenerator()
keyword_extractor = KeywordExtractor()

# FastAPI setup
app = FastAPI()

# Định nghĩa một biến dùng cho xác thực
auth_scheme = JWTBearer()


def generate_que_n_ans(context):
    """Generate question from given context.

    Args:
        context (str): input corpus needed to generate question.

    Returns:
        tuple[list[str], list[str], list[list[str]]]: tuple of lists of all
        generated questions n' answers.
    """
    summary, splitted_text = inference_handler.get_all_summary(
        model=summarizer, context=context)
    filtered_kws = keyword_extractor.get_keywords(
        original_list=splitted_text, summarized_list=summary)

    crct_ans, all_answers = false_ans_gen.get_output(filtered_kws=filtered_kws)
    questions = inference_handler.get_all_questions(
        model=question_gen, context=summary, answer=crct_ans)

    return questions, crct_ans, all_answers


def process_request(request):
    """Process user request and return generated questions to their firestore database.

    Args:
        request (ModelInput): request from flutter.
    """
    request.context = vietnamese_to_english(request.context)
    request.name = vietnamese_to_english(request.name)

    fs.update_generated_status(request, True)
    questions, crct_ans, all_ans = generate_que_n_ans(request.context)
    fs.update_generated_status(request, False)
    # fs.send_results_to_fs(request, questions, crct_ans, all_ans, request.context)
    # Sửa ở đây: Trả về kết quả từ hàm send_results_to_fs
    results = fs.send_results_to_fs(request, questions, crct_ans, all_ans, request.context)
    return results


# body classes for req n' res
# pylint: disable=too-few-public-methods
class ModelInput(BaseModel):
    """General request model structure for flutter incoming req."""
    uid: Optional[str] = None
    context: str
    name: str

class UserInput(BaseModel):
    context: str
    name: str

class ModelExportInput(BaseModel):
    """Request model for exporting questions."""
    uid: Optional[str] = None
    name: str

#son
class ModelRatingInput(BaseModel):
    """Rating questions."""
    identifier: str
    name: str
    question_id: str
    rate: int

class ModelCommentInput(BaseModel):
    identifier: str
    name: str
    question_id: str
    comment: str

class UserCreate(BaseModel):
    email: EmailStr
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=6)

class UserLogin(BaseModel):
    identifier: str  # Can be either email or username
    password: str

class UserChangePassword(BaseModel):
    password: str
    new_password: str

class All_ans(BaseModel):
    """All answers model."""
    ans1: str
    ans2: str
    ans3: str
    ans4: str
   
class UpdateQuestion(BaseModel):
    """Update question model."""
    all_ans: All_ans
    context: str
    crct_ans: str
    question: str

class User(BaseModel):
    uid: str
    email: str
    username: str

def get_current_user(token: str = Header(...)):
    try:
        user_data = fs.get_user_by_token(token)
        return User(**user_data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


#Translator vietnamese<->english
def vietnamese_to_english(text):
    translator = GoogleTranslator(source='vi', target='en')
    translated_text = translator.translate(text)
    return translated_text

# Hàm tạo XML format cho Moodle
def create_moodle_xml(questions):
    """Create Moodle XML from question list.

    Args:
        questions (list[dict]): list of questions.

    Returns:
        str: XML content as string.
    """
    quiz = ET.Element('quiz')

    for question in questions:
        question_el = ET.SubElement(quiz, 'question', type='multichoice')
        
        name_el = ET.SubElement(question_el, 'name')
        text_name_el = ET.SubElement(name_el, 'text')
        text_name_el.text = question['text']

        questiontext_el = ET.SubElement(question_el, 'questiontext', format='html')
        text_questiontext_el = ET.SubElement(questiontext_el, 'text')
        text_questiontext_el.text = f"<![CDATA[{question['text']}]]>"

        # Thêm các câu trả lời
        for answer in question['choices']:
            fraction = "100" if answer == question['correct_choice'] else "0"
            answer_el = ET.SubElement(question_el, 'answer', fraction=fraction)
            text_answer_el = ET.SubElement(answer_el, 'text')
            text_answer_el.text = answer
            feedback_el = ET.SubElement(answer_el, 'feedback')
            text_feedback_el = ET.SubElement(feedback_el, 'text')
            text_feedback_el.text = "Correct!" if answer == question['correct_choice'] else "Incorrect."

    # Tạo nội dung XML từ ElementTree
    xml_str = ET.tostring(quiz, encoding='unicode')
    return xml_str


# API
# req -> context and ans-s,
# res -> questions
@ app.post('/get-question')
async def model_inference(request: UserInput, bg_task: BackgroundTasks, token: str = Depends(auth_scheme)):
    """Process user request

    Args:
        request (ModelInput): request model
        bg_task (BackgroundTasks): run process_request() on other thread
        and respond to request

    Returns:
        dict(str: int): response
    """
    # bg_task.add_task(process_request, request)


    # # Tạo một dictionary để lưu trữ kết quả
    # results = []

    # def background_task():
    #     nonlocal results
    #     results = process_request(request)

    # # Thêm tác vụ nền để xử lý yêu cầu
    # bg_task.add_task(background_task)


    # Thực hiện xử lý yêu cầu và lưu kết quả vào Firestore
    # Không dùng background vì để nó chạy trong cùng 1 thread để chờ xử lí xong mới có results
    user_data = fs.get_user_by_token(token)
    model_input = ModelInput(**request.dict(), uid=user_data['uid'])
    results = process_request(model_input)

    return {
        'status': 200,
        'data': results
    }

# API để chia đoạn văn thành các câu và gửi yêu cầu cho API `get-question`
@ app.post('/get-questions')
async def get_questions(request: UserInput, bg_task: BackgroundTasks, token: str = Depends(auth_scheme)):
    """Process user request by splitting the context into sentences 
    and sending requests to the `get-question` API for each sentence.

    Args:
        request (ModelInput): request model

    Returns:
        dict: response with status
    """
    # Khởi tạo danh sách kết quả trước khi vòng lặp bắt đầu
    results = []

    # Tạo biểu thức chính quy để tìm các dấu ngắt câu
    sentence_delimiters = r'[.!?]'

    # Tách đoạn văn thành các câu
    sentences = re.split(sentence_delimiters, request.context)

    # Loại bỏ các câu rỗng
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

    user_data = fs.get_user_by_token(token)
    model_input = ModelInput(**request.dict(), uid=user_data['uid'])
    # Gửi yêu cầu cho mỗi câu và thu thập kết quả
    for sentence in sentences:
        result = process_request(ModelInput(context=sentence, uid=model_input.uid, name=model_input.name))
        results.append(result)
        # bg_task.add_task(process_request, ModelInput(context=sentence, uid=request.uid, name=request.name))

    # Trả về kết quả
    return JSONResponse(content={'status': 200, 'data': results})

@ app.post('/export-questions')
async def export_questions(request: ModelExportInput, token: str = Depends(auth_scheme)):
    """Export questions in Aiken format based on the provided topic.

    Args:
        request (ModelExportInput): request model

    Returns:
        FileResponse: response with the exported file
    """
    try:
        if not request.uid:
            user_data = fs.get_user_by_token(token)
            request.uid = user_data['uid']
        questions = fs.get_questions_by_uid_and_topic(request.uid, request.name)  # Fetch questions from Firestore by uid and topic
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    aiken_format_content = ""

    for question in questions:
        aiken_format_content += f"{question['text']}\n"
        for idx, answer in enumerate(question['choices']):
            aiken_format_content += f"{chr(65 + idx)}. {answer}\n"
        correct_choice_index = question['choices'].index(question['correct_choice'])  # Lấy vị trí của đáp án đúng trong danh sách lựa chọn
        correct_choice = chr(65 + correct_choice_index)  # Convert số thành ký tự tương ứng
        aiken_format_content += f"ANSWER: {correct_choice}\n\n"

    # Đường dẫn đến thư mục Downloads của người dùng
    downloads_path = str(Path.home() / "Downloads")
    file_name = f"{request.name}.txt"
    file_path = os.path.join(downloads_path, file_name)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(aiken_format_content)

    return FileResponse(file_path, filename=file_name)

@ app.post('/export-questions-moodle')
async def export_questions_moodle(request: ModelExportInput, token: str = Depends(auth_scheme)):
    """Export questions in Moodle XML format based on the provided topic.

    Args:
        request (ModelExportInput): request model

    Returns:
        FileResponse: response with the exported file
    """
    try:
        if not request.uid:
            user_data = fs.get_user_by_token(token)
            request.uid = user_data['uid']
        questions = fs.get_questions_by_uid_and_topic(request.uid, request.name)  # Fetch questions from Firestore by uid and topic
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    moodle_xml_content = create_moodle_xml(questions)

    # Đường dẫn đến thư mục Downloads của người dùng
    downloads_path = str(Path.home() / "Downloads")
    file_name = f"{request.name}.xml"
    file_path = os.path.join(downloads_path, file_name)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(moodle_xml_content)

    return FileResponse(file_path, filename=file_name)

@ app.post('/duplicate-questions-answers')
async def get_duplicate_questions_answers(request: ModelExportInput, token: str = Depends(auth_scheme)):
    try:
        if not request.uid:
            user_data = fs.get_user_by_token(token)
            request.uid = user_data['uid']
        # Lấy danh sách các câu hỏi từ Firebase theo uid và chủ đề (name)
        questions = fs.get_questions_by_uid_and_topic(uid=request.uid, topic=request.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    duplicate_questions = []
    duplicate_answers = []

    # Kiểm tra các câu hỏi trùng nhau
    for idx1, q1 in enumerate(questions):
        for idx2, q2 in enumerate(questions[idx1 + 1:], start=idx1 + 1):
            if q1['text'] == q2['text']:
                duplicate_questions.append({'question': q1['text'], 'position1': idx1, 'position2': idx2})

            # Kiểm tra các đáp án trùng nhau
            for ans1 in q1['choices']:
                if ans1 in q2['choices']:
                    duplicate_answers.append({'answer': ans1, 'position1': idx1, 'position2': idx2})

    return {
        'duplicate_questions': duplicate_questions,
        'duplicate_answers': duplicate_answers
    }

@app.post('/rating-questions')
async def rate_questions(request: ModelRatingInput, token: str = Depends(auth_scheme)):
    try:
        # Tham chiếu đến tài liệu câu hỏi cụ thể
        users_ref = fs._db.collection('users')
        user_query = users_ref.where('email', '==', request.identifier).get()
        if not user_query:
            user_query = users_ref.where('username', '==', request.identifier).get()
        
        if not user_query:
            raise ValueError("Invalid email/username or password")
        
        user = user_query[0].to_dict()
        doc_ref = fs._db.collection('users').document(user['uid']).collection(request.name).document(request.question_id)
        user_data = fs.get_user_by_token(token)
        # Lấy dữ liệu hiện tại của tài liệu
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            ratings = data.get('rating', [])
 
            # Kiểm tra xem uid đã tồn tại trong danh sách ratings chưa
            uid_exists = False
            for rating in ratings:
                if rating['uid'] == user_data['uid']:
                    rating['rate'] = request.rate
                    uid_exists = True
                    break
 
            # Nếu uid không tồn tại, thêm mới vào danh sách ratings
            if not uid_exists:
                ratings.append({
                    'uid': user_data['uid'],
                    'rate': request.rate
                })
 
            # Cập nhật trường rating trong Firestore
            doc_ref.update({'rating': ratings})
 
            # Tính toán điểm trung bình
            average_rating = sum(r['rate'] for r in ratings) / len(ratings) if ratings else 0
 
            # Cập nhật trường average_rating
            doc_ref.update({'average_rating': average_rating})
 
            return {
                'status': 200,
                'data': doc_ref.get().to_dict()  # Trả về dữ liệu đã cập nhật từ Firestore
            }
        else:
            raise ValueError("Question not found")
 
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
 
   
@app.post('/comment-questions')
async def comment_questions(request: ModelCommentInput, token: str = Depends(auth_scheme)):
    try:
        # Tham chiếu đến tài liệu câu hỏi cụ thể
        users_ref = fs._db.collection('users')
        user_query = users_ref.where('email', '==', request.identifier).get()
        if not user_query:
            user_query = users_ref.where('username', '==', request.identifier).get()
        
        if not user_query:
            raise ValueError("Invalid email/username or password")
        
        user = user_query[0].to_dict()
        doc_ref = fs._db.collection('users').document(user['uid']).collection(request.name).document(request.question_id)
        user_data = fs.get_user_by_token(token)
        # Lấy dữ liệu hiện tại của tài liệu
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            comments = data.get('comments', [])
 
            # Thêm bình luận mới vào danh sách bình luận
            comments.append({
                'uid': user_data['uid'],
                'comment': request.comment,
                'time': datetime.now().isoformat()  # Thêm thời gian hiện tại
            })
 
            # Cập nhật trường comments trong Firestore
            doc_ref.update({'comments': comments})
 
            return {
                'status': 200,
                'data': doc_ref.get().to_dict()  # Trả về dữ liệu đã cập nhật từ Firestore
            }
        else:
            raise ValueError("Question not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
 
@app.get('/search-questions')
async def search_questions(keyword: str, token: str = Depends(auth_scheme)):
    try:
        # Tham chiếu đến bộ sưu tập người dùng
        users_collection = fs._db.collection('users')
        
        # Lấy tất cả các tài liệu người dùng
        users = users_collection.stream()

        matching_questions = []
        
        # Duyệt qua tất cả các tài liệu người dùng
        for user in users:
            user_id = user.id
            user_data = user.to_dict()
            
            # Duyệt qua tất cả các bộ sưu tập câu hỏi của mỗi người dùng
            question_collections = fs._db.collection('users').document(user_id).collections()
            for collection in question_collections:
                documents = collection.stream()
                
                # Lọc các câu hỏi dựa trên tiêu đề
                for doc in documents:
                    data = doc.to_dict()
                    if keyword.lower() in data['question'].lower():  # Tìm kiếm không phân biệt chữ hoa chữ thường
                        question_data = {
                            'user_id': user_id,
                            'collection_id': collection.id,
                            'id': doc.id,
                            'text': data['question'],
                            'choices': [data['all_ans'][str(i)] for i in range(4)],  # Giả sử có 4 lựa chọn
                            'correct_choice': data['crct_ans']
                        }
                        
                        # Chỉ thêm trường 'rating' nếu có ít nhất một đánh giá
                        if 'rating' in data and data['rating']:
                            question_data['rating'] = data['rating']
                        
                        matching_questions.append(question_data)

        return {
            'status': 200,
            'data': matching_questions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

# User registration
@app.post('/register')
async def register_user(user: UserCreate):
    """Register a new user with unique email and username validation.

    Args:
        user (UserCreate): user registration model

    Returns:
        JSONResponse: response with status
    """
    # Kiểm tra email duy nhất
    if fs.get_user_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Kiểm tra username duy nhất
    if fs.get_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    # Lưu người dùng mới vào Firestore
    user_data = fs.create_user(user.email, user.username, user.password)

    return JSONResponse(content={'status': 201, 'message': 'User registered successfully', 'user_data': user_data})

# User login
@app.post('/login')
async def login_user(user: UserLogin):
    """Login a user with email/username and password.

    Args:
        user (UserLogin): user login model

    Returns:
        JSONResponse: response with token
    """
    try:
        token, uid = fs.authenticate_user(user.identifier, user.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(content={'status': 200, 'token': token, 'uid': uid})

@app.post('/change-password')
async def change_password(user: UserChangePassword, token: str = Depends(auth_scheme)):
    """Change password for a user.

    Args:
        user (UserChangePassword): user change password model

    Returns:
        JSONResponse: response with status
    """
    try:
        user_data = fs.get_user_by_token(token)

        response = fs.change_password_func(user_data['uid'], user.password, user.new_password)
        return JSONResponse(content={'status': 200, 'message': response['message']})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get('/user-info', response_model=User)
async def get_user_info(token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
        return JSONResponse(content={'status': 200, 'data': user_data})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get('/user-all-topics-questions')
async def get_all_topics_and_questions(token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
        uid = user_data['uid']
        
        all_topics_and_questions = fs.get_all_topics_and_questions_by_uid(uid)
        
        return JSONResponse(content={'status': 200, 'data': all_topics_and_questions})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete('/delete-user-topic')
async def delete_topic(topic_delete: str, token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
        uid = user_data['uid']
        
        success = fs.delete_topic_by_uid(uid, topic_delete)
        
        if success:
            return JSONResponse(content={'status': 200, 'message': 'Topic deleted successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to delete topic")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete('/delete-user-question')
async def delete_question(topic: str, question_id_delete: str, token: str = Depends(auth_scheme)):
    try:
        # Lấy thông tin người dùng từ token
        user_data = fs.get_user_by_token(token)
        uid = user_data['uid']
        
        # Xóa câu hỏi của người dùng
        success = fs.delete_question_by_uid_and_topic(uid, topic, question_id_delete)
        
        if success:
            return JSONResponse(content={'status': 200, 'message': 'Question deleted successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to delete question")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete('/delete-user')
async def delete_user(token: str = Depends(auth_scheme)):
    try:
        # Lấy thông tin người dùng từ token
        user_data = fs.get_user_by_token(token)
        uid = user_data['uid']
        
        # Xóa người dùng
        success = fs.delete_user(uid)
        
        if success:
            return JSONResponse(content={'status': 200, 'message': 'User deleted successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to delete user")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get('/other-user-info')    
async def get_other_user_info(identifier: str , token: str = Depends(auth_scheme)):
    try:
        users_ref = fs._db.collection('users')
        user_query = users_ref.where('email', '==', identifier).limit(1).get()
        if not user_query:
            user_query = users_ref.where('username', '==', identifier).limit(1).get()
       
        if not user_query:
            raise ValueError("Invalid email/username")
        user_data = user_query[0].to_dict()
        return JSONResponse(content={'status': 200, 'data': user_data})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get('/other-user-all-topics-questions')
async def get_other_user_all_topics_and_questions(identifier: str, token: str = Depends(auth_scheme)):
    try:
        users_ref = fs._db.collection('users')
        user_query = users_ref.where('email', '==', identifier).limit(1).get()
        if not user_query:
            user_query = users_ref.where('username', '==', identifier).limit(1).get()
       
        if not user_query:
            raise ValueError("Invalid email/username")
 
        user_data = user_query[0].to_dict()
        uid = user_data['uid']
        
        all_topics_and_questions = fs.get_all_topics_and_questions_by_uid(uid)
        
        return JSONResponse(content={'status': 200, 'data': all_topics_and_questions})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post('/change-user-info')
async def change_user_info(user: User, token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
        fs.change_user_info(user_data['uid'], user.email, user.username)
        return JSONResponse(content={'status': 200, 'message': f'User {user.username} info changed successfully'})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/upload-avatar")
async def upload_avatar(file: UploadFile = File(...), token: str = Depends(auth_scheme)):
    """Upload avatar for a user and update Firestore.

    Args:
        file: File object of the avatar image.

    Returns:
        dict: Information about the uploaded avatar.
    """
    try:
        user_data = fs.get_user_by_token(token)
        # Kiểm tra xem người dùng có tồn tại không
        user_ref = fs._db.collection('users').document(user_data['uid'])
        user_doc = user_ref.get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")

        # Upload avatar và nhận URL của ảnh
        avatar_url = fs.upload_avatar(user_data['uid'], file)
        return {"avatar_url": avatar_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post('/change-topic-name')
async def change_topic_name(topic: str, new_topic: str, token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
        uid = user_data['uid']
        response = fs.change_topic_name(uid, topic, new_topic)
        return JSONResponse(content=response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
   
@app.post('/change-question')
async def update_question(topic: str, question_id: str, info: UpdateQuestion, token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
        uid = user_data['uid']
        new_info = {
            'all_ans': {
                '0': info.all_ans.ans1,
                '1': info.all_ans.ans2,
                '2': info.all_ans.ans3,
                '3': info.all_ans.ans4
            },
            'context': info.context,
            'crct_ans': info.crct_ans,
            'question': info.question
        }
        response = fs.update_question(uid, topic, question_id, new_info)
        return JSONResponse(content=response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
