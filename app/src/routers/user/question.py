from fastapi import APIRouter, HTTPException, UploadFile, Depends, File
from fastapi.responses import JSONResponse, FileResponse
from PIL import Image
from PyPDF2 import PdfReader
from typing import Dict
from pathlib import Path


import io, os, re, pytesseract

from src.utils import vietnamese_to_english
from src.inferencehandler import inference_handler
from src.interface import *
from src.service import *
from src.loaders.database import auth_scheme, fs
from src.loaders import summarizer, keyword_extractor, false_ans_gen, question_gen


router = APIRouter(
    prefix="/questions",      # Tất cả endpoint trong router này bắt đầu bằng /auth
    tags=["questions"],       # Hiển thị trong docs (Swagger UI)
)

# create
@router.post("/pdf")
async def generate_questions_from_pdf(file: UploadFile = File(...), token: str = Depends(auth_scheme)) -> Dict[str, str]:
    try:
        user_data = fs.get_user_by_token(token)
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
        print(text)
        
        # Lấy tên file làm topic, bỏ phần ".pdf"
        topic = os.path.splitext(file.filename)[0]
        print(topic)

        # Khởi tạo danh sách kết quả trước khi vòng lặp bắt đầu
        results = []
        error_sentences = []

        # Tạo biểu thức chính quy để tìm các dấu ngắt câu
        sentence_delimiters = r'[.!?\n]'

        # Tách đoạn văn thành các câu
        sentences = re.split(sentence_delimiters, text)

        # Loại bỏ các câu rỗng
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
        print(sentences)

        model_input = ModelInput(context=text, name=topic, uid=user_data['uid'])
        # Gửi yêu cầu cho mỗi câu và thu thập kết quả
        for sentence in sentences:
            try:
                result = generate_and_store_questions(ModelInput(context=sentence, uid=model_input.uid, name=model_input.name))
                results.append(result)
            except Exception as e:
                print(f"Lỗi khi xử lí câu: {sentence}. Lỗi: {e}")
                error_sentences.append({'sentence': sentence, 'error': str(e)})
                continue

        response_content = {
            'status': 200,
            'data': results,
            'errors': error_sentences if error_sentences else None
        }
        
        return JSONResponse(content=response_content)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {e}")

@router.post("/image")
async def generate_questions_from_image(file: UploadFile = File(...), token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
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
        results = []
        error_sentences = []

        # Tạo biểu thức chính quy để tìm các dấu ngắt câu
        sentence_delimiters = r'[.!?\n]'

        # Tách đoạn văn thành các câu
        sentences = re.split(sentence_delimiters, combined_text)

        # Loại bỏ các câu rỗng
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
        print(sentences)

        model_input = ModelInput(context=combined_text, name=topic, uid=user_data['uid'])
        # Gửi yêu cầu cho mỗi câu và thu thập kết quả
        for sentence in sentences:
            try:
                result = generate_and_store_questions(ModelInput(context=sentence, uid=model_input.uid, name=model_input.name))
                results.append(result)
            except Exception as e:
                print(f"Lỗi khi xử lí câu: {sentence}. Lỗi: {e}")
                error_sentences.append({'sentence': sentence, 'error': str(e)})
                continue

        response_content = {
            'status': 200,
            'data': results,
            'errors': error_sentences if error_sentences else None
        }
        
        return JSONResponse(content=response_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/sentence')
async def generate_questions_from_sentence(request: ICreateQuestion, token: str = Depends(auth_scheme)):
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
    results = []
    error_sentences = []
    user_data = fs.get_user_by_token(token)
    model_input = ModelInput(**request.dict(), uid=user_data['uid'])
    try:
        results = generate_and_store_questions(model_input)
    except Exception as e:
        # Không để là model_input.context mà là request.context vì model_input.context là tiếng Anh
        print(f"Lỗi khi xử lí câu: {request.context}. Lỗi: {e}")
        error_sentences.append({'sentence': request.context, 'error': str(e)})

    return {
        'status': 200,
        'data': results,
        'errors': error_sentences if error_sentences else None
    }

@router.post('/paragraph')
async def generate_questions_from_paragraph(request: ICreateQuestion, token: str = Depends(auth_scheme)):
    # API để chia đoạn văn thành các câu và tạo ra các câu hỏi cho từng câu.
    """Process user request by splitting the context into sentences 
    and sending requests to the `get-question` API for each sentence.

    Args:
        request (ModelInput): request model

    Returns:
        dict: response with status
    """
    # Khởi tạo danh sách kết quả trước khi vòng lặp bắt đầu
    results = []
    error_sentences = []

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
        try:
            result = generate_and_store_questions(ModelInput(context=sentence, uid=model_input.uid, name=model_input.name))
            results.append(result)
            # bg_task.add_task(process_request, ModelInput(context=sentence, uid=request.uid, name=request.name))
        except Exception as e:
            print(f"Lỗi khi xử lí câu: {sentence}. Lỗi: {e}")
            error_sentences.append({'sentence': sentence, 'error': str(e)})
            continue

    # Trả về kết quả
    response_content = {
        'status': 200,
        'data': results,
        'errors': error_sentences if error_sentences else None
    }
    
    return JSONResponse(content=response_content)

# index
@router.get('/')
async def index(keyword: str, token: str = Depends(auth_scheme)):
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

# export question
@router.post('/export/aiken')
async def export_questions(request: IExportQuestion, token: str = Depends(auth_scheme)):
    """Export questions in Aiken format based on the provided topic.

    Args:
        request (IExportQuestion): request model

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

@router.post('/export/moodle')
async def export_questions_moodle(request: IExportQuestion, token: str = Depends(auth_scheme)):
    """Export questions in Moodle XML format based on the provided topic.

    Args:
        request (IExportQuestion): request model

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

# update
@router.put('/')
async def update_question(topic: str, question_id: str, info: IUpdateQuestion, token: str = Depends(auth_scheme)):
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

# delete
@router.delete('/')
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

# other
@ router.post('/check-duplicate')
async def get_duplicate_questions_answers(request: IExportQuestion, token: str = Depends(auth_scheme)):
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

# create
def generate_and_store_questions(request):
    """Generate questions from user request and store results in Firestore.

    Args:
        request (ModelInput): request from flutter.

    Returns:
        dict: results saved to Firestore
    """
    request.context = vietnamese_to_english(request.context)
    request.name = vietnamese_to_english(request.name)

    fs.update_generated_status(request, True)
    questions, crct_ans, all_ans = generate_questions_and_answers(request.context)
    fs.update_generated_status(request, False)

    results = fs.send_results_to_fs(request, questions, crct_ans, all_ans, request.context)
    return results

# other
def generate_questions_and_answers(context: str):
    """Generate questions and answers from given context.

    Args:
        context (str): input corpus used to generate question.

    Returns:
        tuple[list[str], list[str], list[list[str]]]:
        questions, correct answers, and all answer choices.
    """
    summary, splitted_text = inference_handler.get_all_summary(
        model=summarizer, context=context
    )
    filtered_kws = keyword_extractor.get_keywords(
        original_list=splitted_text, summarized_list=summary
    )

    crct_ans, all_answers = false_ans_gen.get_output(filtered_kws=filtered_kws)
    questions = inference_handler.get_all_questions(
        model=question_gen, context=summary, answer=crct_ans
    )

    return questions, crct_ans, all_answers