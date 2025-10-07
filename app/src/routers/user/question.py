from fastapi import APIRouter, HTTPException, UploadFile, Request, File, Query
from fastapi.responses import JSONResponse, FileResponse
from PIL import Image
from PyPDF2 import PdfReader
from typing import Dict
from pathlib import Path


import io, os, re, pytesseract

from src.repositories import QuestionRepository, ChoiceRepository
from src.interface import *
from src.service import *
from src.utils import res_ok


router = APIRouter(
    prefix="/questions",      # Tất cả endpoint trong router này bắt đầu bằng /auth
    tags=["questions"],       # Hiển thị trong docs (Swagger UI)
)

# create
@router.post("/pdf")
async def generate_questions_from_pdf(request: Request, file: UploadFile = File(...),) -> Dict[str, str]:
    question_repo = QuestionRepository()
    user_id = request.state.user["uid"]
    # Kiểm tra định dạng file
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="file.not_pdf")

    try:
        # Đọc nội dung của file PDF
        file_read = await file.read()
        pdf_reader = PdfReader(io.BytesIO(file_read))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        print(text)
        
        # Lấy tên file làm topic, bỏ phần ".pdf"
        topic = os.path.splitext(file.filename)[0]
        print(topic)

        # Khởi tạo danh sách kết quả trước khi vòng lặp bắt đầu
        new_questions = []
        error_sentences = []

        # Tạo biểu thức chính quy để tìm các dấu ngắt câu
        sentence_delimiters = r'[.!?\n]'

        # Tách đoạn văn thành các câu
        sentences = re.split(sentence_delimiters, text)

        # Loại bỏ các câu rỗng
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
        print(sentences)

        # Gửi yêu cầu cho mỗi câu và thu thập kết quả
        for sentence in sentences:
            try:
                new_question = question_repo.generate_and_store_questions(ModelInput(context=sentence, uid=user_id, name=topic))
                new_questions.append(new_question)
            except Exception as e:
                print(f"Lỗi khi xử lí câu: {sentence}. Lỗi: {e}")
                error_sentences.append({'sentence': sentence, 'error': str(e)})
                continue
        
        result = {
            "success": new_questions,
            "fail": error_sentences
        }
        return JSONResponse(status_code=200, content=res_ok(result))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {e}")

@router.post("/image")
async def generate_questions_from_image(request: Request, file: UploadFile = File(...)):
    question_repo = QuestionRepository()
    user_id = request.state.user["uid"]
    
    # Kiểm tra định dạng file
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="file.not_image")
    
    try:
        # Đọc hình ảnh
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))

        # Sử dụng pytesseract để trích xuất văn bản với ngôn ngữ tiếng Việt
        extracted_text = pytesseract.image_to_string(image, lang='vie')

        # TODO: Sử dụng văn bản trích xuất để tạo câu hỏi
        # Ví dụ giả định: sử dụng đoạn văn bản đầu tiên làm câu hỏi, các đoạn sau làm câu trả lời
        lines = extracted_text.split('\n')
        combined_text = ""
        for i, line in enumerate(lines):
            if i > 0:
                combined_text += " "  # Thêm khoảng trắng trước mỗi dòng từ dòng thứ hai trở đi
            combined_text += line

        # Lấy tên file làm topic, bỏ phần ".png, etc"
        topic = os.path.splitext(file.filename)[0]
        print(topic)

        # Khởi tạo danh sách kết quả trước khi vòng lặp bắt đầu
        new_questions = []
        error_sentences = []

        # Tạo biểu thức chính quy để tìm các dấu ngắt câu
        sentence_delimiters = r'[.!?\n]'

        # Tách đoạn văn thành các câu
        sentences = re.split(sentence_delimiters, combined_text)

        # Loại bỏ các câu rỗng
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
        print(sentences)

        # Gửi yêu cầu cho mỗi câu và thu thập kết quả
        for sentence in sentences:
            try:
                new_question = question_repo.generate_and_store_questions(ModelInput(context=sentence, uid=user_id, name=topic))
                new_questions.append(new_question)
            except Exception as e:
                print(f"Lỗi khi xử lí câu: {sentence}. Lỗi: {e}")
                error_sentences.append({'sentence': sentence, 'error': str(e)})
                continue
        
        result = {
            "success": new_questions,
            "fail": error_sentences
        }
        return JSONResponse(status_code=200, content=res_ok(result))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/sentence')
async def generate_questions_from_sentence(body: ICreateQuestion, request: Request):
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
    question_repo = QuestionRepository()
    user_id = request.state.user["uid"]
    
    new_questions = []
    error_sentences = []
    model_input = ModelInput(**body.dict(), uid=user_id)
    try:
        new_questions =  question_repo.generate_and_store_questions(model_input)
    except Exception as e:
        # Không để là model_input.context mà là request.context vì model_input.context là tiếng Anh
        print(f"Lỗi khi xử lí câu: {body.context}. Lỗi: {e}")
        error_sentences.append({'sentence': body.context, 'error': str(e)})

    result = {
        "success": new_questions,
        "fail": error_sentences
    }
    return JSONResponse(status_code=200, content=res_ok(result))
        
@router.post('/paragraph')
async def generate_questions_from_paragraph(body: ICreateQuestion, request: Request):
    # API để chia đoạn văn thành các câu và tạo ra các câu hỏi cho từng câu.
    """Process user request by splitting the context into sentences 
    and sending requests to the `get-question` API for each sentence.

    Args:
        request (ModelInput): request model

    Returns:
        dict: response with status
    """
    question_repo = QuestionRepository()
    user_id = request.state.user["uid"]
    

    # Khởi tạo danh sách kết quả trước khi vòng lặp bắt đầu
    new_questions = []
    error_sentences = []

    # Tạo biểu thức chính quy để tìm các dấu ngắt câu
    sentence_delimiters = r'[.!?]'

    # Tách đoạn văn thành các câu
    sentences = re.split(sentence_delimiters, request.context)

    # Loại bỏ các câu rỗng
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

    model_input = ModelInput(**body.dict(), uid=user_id)
    # Gửi yêu cầu cho mỗi câu và thu thập kết quả
    for sentence in sentences:
        try:
            result = question_repo.generate_and_store_questions(ModelInput(context=sentence, uid=model_input.uid, name=model_input.name))
            new_questions.append(result)
            # bg_task.add_task(process_request, ModelInput(context=sentence, uid=request.uid, name=request.name))
        except Exception as e:
            print(f"Lỗi khi xử lí câu: {sentence}. Lỗi: {e}")
            error_sentences.append({'sentence': sentence, 'error': str(e)})
            continue

    result = {
        "success": new_questions,
        "fail": error_sentences
    }
    return JSONResponse(status_code=200, content=res_ok(result))
     

# index
@router.get('/')
async def index(keyword: str | None = Query(None)):
    try:
        question_repo = QuestionRepository()
        choice_repo = ChoiceRepository()

        list_question = await question_repo.get_many(keyword)
        matching_questions = []

        for q in list_question:
            list_choice = await choice_repo.get_many_by_question_id(q.id)
            list_choice_content = [c.choice_text for c in list_choice]

            question_data = {
                "id": q.id,
                "user_id": q.user_id,
                "text": q.question_text,
                "choices": list_choice_content,
                "correct_choice": q.correct_choice,
                "tags": q.tags,
            }

            matching_questions.append(question_data)
        return JSONResponse(status_code=200, content=res_ok(matching_questions))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

# export question
@router.post('/export/aiken')
async def export_questions(body: IExportQuestion, request: Request):
    """Export questions in Aiken format based on the provided topic.

    Args:
        request (IExportQuestion): request model

    Returns:
        FileResponse: response with the exported file
    """
    question_repo = QuestionRepository()
    list_question = await question_repo.get_list_question_by_user_and_topic
    
    aiken_format_content = ""

    for question in list_question:
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

@router.post('/export/moodle')
async def export_questions_moodle(request: IExportQuestion):
    """Export questions in Moodle XML format based on the provided topic.

    Args:
        request (IExportQuestion): request model

    Returns:
        FileResponse: response with the exported file
    """
    question_repo = QuestionRepository()
    list_question = await question_repo.get_list_question_by_user_and_topic
    
    moodle_xml_content = create_moodle_xml(list_question)

    # Đường dẫn đến thư mục Downloads của người dùng
    downloads_path = str(Path.home() / "Downloads")
    file_name = f"{request.name}.xml"
    file_path = os.path.join(downloads_path, file_name)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(moodle_xml_content)

    return FileResponse(file_path, filename=file_name)

# update
@router.put('/{question_id}')
async def update_question(question_id: int, info: IUpdateQuestion, request: Request):
    try:
        question_repo = QuestionRepository()
        user_id = request.state.user["uid"]
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
        await question_repo.update_question(user_id, question_id, new_info)
        return JSONResponse(status_code=200, content=res_ok())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# delete
@router.delete('/{question_id}')
async def delete_question(question_id: int, request: Request):
    try:
        question_repo = QuestionRepository()
        user_id = request.state.user["uid"]  
        await question_repo.delete_question(user_id, question_id)
        return JSONResponse(status_code=200, content=res_ok())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# # other
# @router.post('/check-duplicate')
# async def get_duplicate_questions_answers(request: IExportQuestion, request: Request):
#     try:
#         if not request.uid:
#             user_data = fs.get_user_by_token(token)
#             request.uid = user_data['uid']
#         # Lấy danh sách các câu hỏi từ Firebase theo uid và chủ đề (name)
#         questions = fs.get_questions_by_uid_and_topic(uid=request.uid, topic=request.name)
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))

#     duplicate_questions = []
#     duplicate_answers = []

#     # Kiểm tra các câu hỏi trùng nhau
#     for idx1, q1 in enumerate(questions):
#         for idx2, q2 in enumerate(questions[idx1 + 1:], start=idx1 + 1):
#             if q1['text'] == q2['text']:
#                 duplicate_questions.append({'question': q1['text'], 'position1': idx1, 'position2': idx2})

#             # Kiểm tra các đáp án trùng nhau
#             for ans1 in q1['choices']:
#                 if ans1 in q2['choices']:
#                     duplicate_answers.append({'answer': ans1, 'position1': idx1, 'position2': idx2})

#     return {
#         'duplicate_questions': duplicate_questions,
#         'duplicate_answers': duplicate_answers
#     }
