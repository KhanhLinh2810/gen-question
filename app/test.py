# import bcrypt

# # Lấy mật khẩu từ người dùng (thường là một chuỗi)
# password = "12345678"

# # Hash mật khẩu
# hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# print(hashed_password)
# print(hashed_password.decode('utf-8'))
# -------------------------------------------------------------------------------
import os
import io
import re
import asyncio
from src.service.firebase_service import MySQLService, SessionLocal
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from fastapi.responses import JSONResponse, FileResponse
from auth import JWTBearer
from deep_translator import GoogleTranslator
from typing import Optional, Dict, List
from PyPDF2 import PdfReader
from PIL import Image, UnidentifiedImageError
import pytesseract
from database import get_db
from pathlib import Path

from src.inferencehandler import inference_handler
from src.ansgenerator.false_answer_generator import FalseAnswerGenerator
from src.model.abstractive_summarizer import AbstractiveSummarizer
from src.model.question_generator import QuestionGenerator
from src.model.keyword_extractor import KeywordExtractor

from sqlalchemy.future import select
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker,selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models import User, Question, Choice, Comment, Rating

class ModelInput(BaseModel):
    """General request model structure for flutter incoming req."""
    uid: Optional[str] = None
    context: str
    name: str

#Translator vietnamese<->english
def vietnamese_to_english(text):
    translator = GoogleTranslator(source='vi', target='en')
    translated_text = translator.translate(text)
    return translated_text


# FastAPI setup
app = FastAPI()

# initialize question and ans models
summarizer = AbstractiveSummarizer()
question_gen = QuestionGenerator()
false_ans_gen = FalseAnswerGenerator()
keyword_extractor = KeywordExtractor()

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

async def process_request(request: ModelInput):
    """Process user request and return generated questions to their Firestore database.

    Args:
        request (ModelInput): request from Flutter.
    """
    # Khởi tạo session
    async with SessionLocal() as session:
        try:
            mysql_service = MySQLService(session)
            # Xử lý ngữ cảnh và tên
            request.context = vietnamese_to_english(request.context)
            request.name = vietnamese_to_english(request.name)

            # Cập nhật trạng thái đã tạo câu hỏi
            await mysql_service.update_generated_status(request, True)
            questions, crct_ans, all_ans = generate_que_n_ans(request.context)
            await mysql_service.update_generated_status(request, False)
            
            # Gọi hàm để gửi kết quả về Firestore
            results = await mysql_service.send_results_to_db(uid=request.uid, topic=request.name, questions=questions, crct_ans=crct_ans, all_ans=all_ans, context=request.context)
            return results

        except Exception as e:
            # Xử lý lỗi nếu có
            print(f"Error processing request: {e}")
            return {"status": "error", "message": str(e)}

# Định nghĩa schema cho việc tạo người dùng mới
class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    identifier: str  # Can be either email or username
    password: str

class UserChangePassword(BaseModel):
    password: str
    new_password: str

class User(BaseModel):
    id: int
    username: str
    email: str
    avatar: str = None
    is_admin: bool = False

    class Config:
        orm_mode = True  # Cho phép chuyển đổi từ đối tượng ORM

class UserInfo(BaseModel):
    username: str
    email: str
    avatar: str = None
    is_admin: bool = False

    class Config:
        orm_mode = True  # Cho phép chuyển đổi từ đối tượng ORM

class UserInput(BaseModel):
    context: str
    name: str

class ModelExportInput(BaseModel):
    """Request model for exporting questions."""
    uid: Optional[str] = None
    name: str

class ModelRatingInput(BaseModel):
    """Rating questions."""
    uid: Optional[str] = None
    question_id: int
    rate: int

class ModelCommentInput(BaseModel):
    uid: Optional[str] = None
    question_id: int
    comment: str

@ app.post("/register", response_model=dict)
async def create_user(user: UserCreate):
    """Tạo người dùng mới."""
    async with SessionLocal() as session:
        mysql_service = MySQLService(session)  # Truyền db vào khởi tạo MySQLService
        try:
            new_user = await mysql_service.create_user(
                email=user.email,
                username=user.username,
                password=user.password,
                is_admin=False
            )
            return {"status": "success", "message": "User created successfully", "user_id": new_user.id}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
@ app.post("/admin-register", response_model=dict)
async def create_user(user: UserCreate):
    """Tạo người dùng mới."""
    async with SessionLocal() as session:
        mysql_service = MySQLService(session)  # Truyền db vào khởi tạo MySQLService
        try:
            new_user = await mysql_service.create_user(
                email=user.email,
                username=user.username,
                password=user.password,
                is_admin=True
            )
            return {"status": "success", "message": "User created successfully", "user_id": new_user.id}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# User login
@ app.post('/login', response_model=dict)
async def login_user(user: UserLogin):
    """Login a user with email/username and password.

    Args:
        user (UserLogin): user login model

    Returns:
        JSONResponse: response with token
    """
    async with SessionLocal() as session:
        mysql_service = MySQLService(session)  # Truyền db vào khởi tạo MySQLService
        try:
            token, uid = await mysql_service.authenticate_user(user.identifier, user.password)

            # Lưu token mới vào Firestore
            await mysql_service.update_user_token(uid, token)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return JSONResponse(content={'status': 200, 'token': token, 'uid': uid})

@app.post('/change-password')
async def change_password(user: UserChangePassword, token: str = Depends(JWTBearer(SessionLocal))):
    async with SessionLocal() as session:
        mysql_service = MySQLService(session)

        try:
            # Lấy thông tin người dùng dựa trên token
            user_data = await mysql_service.get_user_by_token(token)
            if not user_data:
                raise HTTPException(status_code=404, detail="User not found.")

            # Gọi hàm thay đổi mật khẩu trong MySQLService
            response = await mysql_service.change_password_func(
                uid=user_data.id,  # Giả sử `id` là trường chính của người dùng
                current_password=user.password,
                new_password=user.new_password
            )

            return JSONResponse(content={'status': 200, 'message': response['message']})
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
@ app.get('/user-info', response_model=User)
async def get_user_info(token: str = Depends(JWTBearer(SessionLocal))):
    """Lấy thông tin người dùng từ MySQL dựa trên token."""
    async with SessionLocal() as session:
        mysql_service = MySQLService(session)
        try:
            # Lấy thông tin người dùng dựa trên token
            user_data = await mysql_service.get_user_by_token(token)
            
            if not user_data:
                raise HTTPException(status_code=404, detail="User not found")

            user_info = User.from_orm(user_data)  # Chuyển đổi sang mô hình Pydantic
            # Trả về thông tin người dùng
            return JSONResponse(content={'status': 200, 'data': user_info.dict()})
            # return user_data
            # chạy được nhưng muốn có dòng status 200 kia nữa
        
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@ app.get('/user-all-topics-questions')
async def get_all_topics_and_questions(token: str = Depends(JWTBearer(SessionLocal))):
    async with SessionLocal() as session:
        mysql_service = MySQLService(session)
        try:
            user_data = await mysql_service.get_user_by_token(token)
            if not user_data:
                raise HTTPException(status_code=404, detail="User not found")
            uid = user_data.id
            
            all_topics_and_questions = await mysql_service.get_all_topics_and_questions_by_uid(uid)
            
            return JSONResponse(content={'status': 200, 'data': all_topics_and_questions})
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

@ app.get('/other-user-info')
async def get_other_user_info(identifier: str, token: str = Depends(JWTBearer(SessionLocal))):
    """Lấy thông tin người dùng khác dựa trên email hoặc username."""
    async with SessionLocal() as session:
        mysql_service = MySQLService(session)
        try:
            # Sử dụng dịch vụ MySQL để tìm người dùng theo email
            user = await mysql_service.get_user_by_email(identifier)

            if not user:  # Nếu không tìm thấy theo email, tìm theo username
                user = await mysql_service.get_user_by_username(identifier)

            if not user:
                raise ValueError("Invalid email/username")

            # Chuyển đổi đối tượng user thành dict để Pydantic xử lý
            user_data = User.from_orm(user)  # Sử dụng từ ORM nếu bạn đã bật orm_mode

            # Chuyển đổi user_data sang từ điển nếu cần
            return JSONResponse(content={'status': 200, 'data': user_data.dict()})  # Giả sử user_data là mô hình Pydantic

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@ app.delete('/delete-user')
async def delete_user(token: str = Depends(JWTBearer(SessionLocal))):
    """Xóa người dùng dựa trên token."""
    async with SessionLocal() as session:
        try:
            user_service = MySQLService(session)  # Khởi tạo dịch vụ với session
            # Lấy thông tin người dùng từ token
            user_data = await user_service.get_user_by_token(token)  # Lấy thông tin người dùng dựa trên token
            uid = user_data.id  # Giả sử `id` là trường chính của người dùng

            # Xóa người dùng
            success = await user_service.delete_user(uid)  # Gọi hàm xóa người dùng

            if success:
                return JSONResponse(content={'status': 200, 'message': 'User deleted successfully'})
            else:
                raise HTTPException(status_code=500, detail="Failed to delete user")

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
@app.post('/change-user-info')
async def change_user_info(user: UserInfo, token: str = Depends(JWTBearer(SessionLocal))):
    """Thay đổi thông tin người dùng."""
    async with SessionLocal() as session:
        try:
            user_service = MySQLService(session)  # Khởi tạo dịch vụ với session
            
            # Lấy thông tin người dùng từ token
            user_data = await user_service.get_user_by_token(token)
            uid = user_data.id  # Giả sử `id` là trường chính của người dùng
            
            # Thay đổi thông tin người dùng
            success = await user_service.change_user_info(uid, user.email, user.username)
            
            if success:
                return JSONResponse(content={'status': 200, 'message': f'User {user.username} info changed successfully'})
            else:
                raise HTTPException(status_code=500, detail="Failed to change user info")
                
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
@app.post('/get-question')
async def model_inference(request: UserInput, bg_task: BackgroundTasks, token: str = Depends(JWTBearer(SessionLocal))):
    """Process user request

    Args:
        request (ModelInput): request model
        bg_task (BackgroundTasks): run process_request() on other thread
        and respond to request

    Returns:
        dict(str: int): response
    """
    error_sentences = []
    results = []
    
    # Khởi tạo session
    async with SessionLocal() as session:
        user_service = MySQLService(session)
        user_data = await user_service.get_user_by_token(token)
        model_input = ModelInput(**request.dict(), uid=user_data.id)
        
        try:
            # Gọi hàm process_request với session
            results = await process_request(model_input)
        except Exception as e:
            print(f"Lỗi khi xử lí câu: {request.context}. Lỗi: {e}")
            error_sentences.append({'sentence': request.context, 'error': str(e)})

    return {
        'status': 200,
        'data': results,
        'errors': error_sentences if error_sentences else None
    }

# API để chia đoạn văn thành các câu và gửi yêu cầu cho API `get-question`
@ app.post('/get-questions')
async def get_questions(request: UserInput, bg_task: BackgroundTasks, token: str = Depends(JWTBearer(SessionLocal))):
    """Process user request by splitting the context into sentences 
    and sending asynchronous requests to the `get-question` API for each sentence.

    Args:
        request (UserInput): request model

    Returns:
        dict: response with status
    """
    async with SessionLocal() as session:
        user_service = MySQLService(session)
        # Khởi tạo danh sách kết quả trước khi vòng lặp bắt đầu
        results = []
        error_sentences = []

        # Tạo biểu thức chính quy để tìm các dấu ngắt câu
        sentence_delimiters = r'[.!?]'

        # Tách đoạn văn thành các câu
        sentences = re.split(sentence_delimiters, request.context)

        # Loại bỏ các câu rỗng
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

        # Lấy thông tin người dùng từ token
        user_data = await user_service.get_user_by_token(token)
        model_input = ModelInput(**request.dict(), uid=user_data.id)

        # Tạo các tác vụ không đồng bộ cho mỗi câu
        async def process_sentence(sentence):
            try:
                result = await process_request(ModelInput(context=sentence, uid=model_input.uid, name=model_input.name))
                return result, None
            except Exception as e:
                return None, {'sentence': sentence, 'error': str(e)}

        # Chạy tất cả các tác vụ song song
        tasks = [process_sentence(sentence) for sentence in sentences]
        responses = await asyncio.gather(*tasks)

        # Phân loại kết quả và lỗi
        for result, error in responses:
            if result:
                results.append(result)
            if error:
                error_sentences.append(error)

        # Trả về kết quả
        response_content = {
            'status': 200,
            'data': results,
            'errors': error_sentences if error_sentences else None
        }

        return JSONResponse(content=response_content)

@ app.post("/upload_pdf_to_questions")
async def upload_pdf(file: UploadFile = File(...), token: str = Depends(JWTBearer(SessionLocal))) -> Dict[str, str]:
    """Upload a PDF file, extract text, split it into sentences, and process each sentence asynchronously.

    Args:
        file (UploadFile): PDF file to be uploaded and processed.
        token (str): Authorization token.

    Returns:
        Dict[str, str]: Response with status, data, and any errors.
    """
    async with SessionLocal() as session:
        user_service = MySQLService(session)
        try:
            # Xác thực người dùng từ token
            user_data = await user_service.get_user_by_token(token)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Kiểm tra định dạng file
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="File không phải định dạng PDF")

        try:
            # Đọc nội dung của file PDF
            file_read = await file.read()
            pdf_reader = PdfReader(io.BytesIO(file_read))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""

            # Lấy tên file làm topic, bỏ phần ".pdf"
            topic = os.path.splitext(file.filename)[0]

            # Tạo biểu thức chính quy để tìm các dấu ngắt câu
            sentence_delimiters = r'[.!?\n]'

            # Tách đoạn văn thành các câu
            sentences = re.split(sentence_delimiters, text)

            # Loại bỏ các câu rỗng
            sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

            # Chuẩn bị dữ liệu đầu vào
            model_input = ModelInput(context=text, name=topic, uid=user_data.id)

            # Tạo các tác vụ không đồng bộ cho mỗi câu
            async def process_sentence(sentence):
                try:
                    result = await process_request(ModelInput(context=sentence, uid=model_input.uid, name=model_input.name))
                    return result, None
                except Exception as e:
                    return None, {'sentence': sentence, 'error': str(e)}

            # Chạy tất cả các tác vụ song song
            tasks = [process_sentence(sentence) for sentence in sentences]
            responses = await asyncio.gather(*tasks)

            # Phân loại kết quả và lỗi
            results = [result for result, _ in responses if result]
            error_sentences = [error for _, error in responses if error]

            # Trả về kết quả
            response_content = {
                'status': 200,
                'data': results,
                'errors': error_sentences if error_sentences else None
            }

            return JSONResponse(content=response_content)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing PDF: {e}")

@ app.post("/generate_questions_from_image")
async def generate_questions_from_image(file: UploadFile = File(...), token: str = Depends(JWTBearer(SessionLocal))):
    async with SessionLocal() as session:
        user_service = MySQLService(session)
        try:
            user_data = await user_service.get_user_by_token(token)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Kiểm tra định dạng file
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File không phải là hình ảnh")

        try:
            # Đọc hình ảnh
            image_data = await file.read()
            image = Image.open(io.BytesIO(image_data))

            # Sử dụng pytesseract để trích xuất văn bản với ngôn ngữ tiếng Việt
            extracted_text = pytesseract.image_to_string(image, lang='vie')

            # Gộp các dòng văn bản trích xuất
            lines = extracted_text.split('\n')
            combined_text = " ".join([line.strip() for line in lines if line.strip()])

            # Lấy tên file làm topic, bỏ phần mở rộng (e.g., ".png")
            topic = os.path.splitext(file.filename)[0]

            # Tạo danh sách câu hỏi và câu lỗi trước khi xử lý
            sentence_delimiters = r'[.!?\n]'
            sentences = re.split(sentence_delimiters, combined_text)
            sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

            model_input = ModelInput(context=combined_text, name=topic, uid=user_data.id)

            # Sử dụng asyncio.gather để xử lý từng câu không đồng bộ
            async def process_sentence(sentence):
                try:
                    result = await process_request(ModelInput(context=sentence, uid=model_input.uid, name=model_input.name))
                    return result, None
                except Exception as e:
                    return None, {'sentence': sentence, 'error': str(e)}

            responses = await asyncio.gather(*[process_sentence(sentence) for sentence in sentences])

            # Phân tách kết quả thành kết quả thành công và lỗi
            results = [result for result, _ in responses if result]
            error_sentences = [error for _, error in responses if error]

            response_content = {
                'status': 200,
                'data': results,
                'errors': error_sentences if error_sentences else None
            }
            
            return JSONResponse(content=response_content)

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@ app.post('/duplicate-questions-answers')
async def get_duplicate_questions_answers(request: ModelExportInput, token: str = Depends(JWTBearer(SessionLocal))):
    async with SessionLocal() as session:
        user_service = MySQLService(session)
        try:
            if not request.uid:
                user_data = await user_service.get_user_by_token(token)
                request.uid = user_data.id
            # Lấy danh sách các câu hỏi từ Firebase theo uid và chủ đề (name)
            questions = await user_service.get_questions_by_uid_and_topic(uid=request.uid, topic=request.name)
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

@ app.post('/rating-questions')
async def rate_questions(request: ModelRatingInput, token: str = Depends(JWTBearer(SessionLocal))):
    async with SessionLocal() as session:
        user_service = MySQLService(session)
        try:
            if not request.uid:
                user_data = await user_service.get_user_by_token(token)
                request.uid = user_data.id
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Gọi hàm để thêm hoặc cập nhật rating
        average_rating, ratings = await user_service.add_or_update_rating(request.uid, request.question_id, request.rate)

        return {
            'status': 200,
            'data': {
                'question_id': request.question_id,
                'average_rating': average_rating,
                'ratings': [{"user_id": r.user_id, "rating_value": r.rating_value} for r in ratings]
            }
        }

@ app.post('/comment-questions')
async def comment_questions(request: ModelCommentInput, token: str = Depends(JWTBearer(SessionLocal))):
    async with SessionLocal() as session:
        user_service = MySQLService(session)
        try:
            if not request.uid:
                user_data = await user_service.get_user_by_token(token)
                request.uid = user_data.id
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Gọi hàm để thêm hoặc cập nhật rating
        new_comment, all_comments = await user_service.add_comment(request.uid, request.question_id, request.comment)

        return {
            'status': 200,
            'data': {
                'question_id': request.question_id,
                'new_comment': new_comment,
                'ratings': [{"user_id": comment.user_id, "rating_value": comment.comment_text} for comment in all_comments]
            }
        }

@ app.delete("/ratings/{rating_id}", response_model=dict)
async def delete_rating(rating_id: int, token: str = Depends(JWTBearer(SessionLocal))):
    """
    API endpoint để xóa rating dựa trên rating_id.

    Args:
        rating_id (int): ID của rating cần xóa.

    Returns:
        dict: Thông báo về kết quả xóa.
    """
    async with SessionLocal() as session:
        user_service = MySQLService(session)
        try:
            user_data = await user_service.get_user_by_token(token)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        try:
            result = await user_service.delete_rating(rating_id, user_data.id)
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@ app.delete("/comments/{comment_id}", response_model=dict)
async def delete_comment(comment_id: int, token: str = Depends(JWTBearer(SessionLocal))):
    """
    API endpoint để xóa comment dựa trên comment_id.

    Args:
        comment_id (int): ID của comment cần xóa.

    Returns:
        dict: Thông báo về kết quả xóa.
    """
    async with SessionLocal() as session:
        user_service = MySQLService(session)
        try:
            user_data = await user_service.get_user_by_token(token)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        try:
            result = await user_service.delete_comment(comment_id, user_data.id)
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@ app.post('/export-questions')
async def export_questions(request: ModelExportInput, token: str = Depends(JWTBearer(SessionLocal))):
    """Xuất câu hỏi ra định dạng Aiken dựa trên chủ đề được cung cấp."""
    async with SessionLocal() as session:
        user_service = MySQLService(session)
        try:
            if not request.uid:
                user_data = await user_service.get_user_by_token(token)
                request.uid = user_data.id
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Truy vấn các câu hỏi từ MySQL dựa vào uid và topic
    questions = await user_service.get_questions_by_uid_and_topic(request.uid, request.name)
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this topic")

    aiken_format_content =await user_service.generate_aiken_content(questions)
    
    # Tạo đường dẫn đến file trong thư mục Downloads của người dùng
    downloads_path = str(Path.home() / "Downloads")
    file_name = f"{request.name}.txt"
    file_path = os.path.join(downloads_path, file_name)

    # Ghi nội dung vào file
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(aiken_format_content)

    # Trả về file cho người dùng
    return FileResponse(file_path, filename=file_name)

@ app.post('/export-questions-moodle')
async def export_questions_moodle(request: ModelExportInput, token: str = Depends(JWTBearer(SessionLocal))):
    """Xuất câu hỏi ra định dạng Aiken dựa trên chủ đề được cung cấp."""
    async with SessionLocal() as session:
        user_service = MySQLService(session)
        try:
            if not request.uid:
                user_data = await user_service.get_user_by_token(token)
                request.uid = user_data.id
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Truy vấn các câu hỏi từ MySQL dựa vào uid và topic
    questions = await user_service.get_questions_by_uid_and_topic(request.uid, request.name)
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this topic")

    moodle_xml_format_content =await user_service.generate_moodle_xml_content(questions)
    
    # Tạo đường dẫn đến file trong thư mục Downloads của người dùng
    downloads_path = str(Path.home() / "Downloads")
    file_name = f"{request.name}.xml"
    file_path = os.path.join(downloads_path, file_name)

    # Ghi nội dung vào file
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(moodle_xml_format_content)

    # Trả về file cho người dùng
    return FileResponse(file_path, filename=file_name)

