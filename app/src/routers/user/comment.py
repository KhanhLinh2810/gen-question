from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime


from src.interface import *
from src.loaders.database import auth_scheme, fs


# comment of question
router = APIRouter(
    prefix="/comments",      # Tất cả endpoint trong router này bắt đầu bằng /comment
    tags=["comments"],       # Hiển thị trong docs (Swagger UI)
)

@router.post('/')
async def create_comment(request: ICreateComment, token: str = Depends(auth_scheme)):
    try:
        # Tham chiếu đến tài liệu câu hỏi cụ thể
        users_ref = fs._db.collection('users')
        user_query = users_ref.where('email', '==', request.id).get()
        if not user_query:
            user_query = users_ref.where('username', '==', request.id).get()
        
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
            new_comment = {
                'uid': user_data['uid'],
                'comment': request.comment,
                'time': datetime.now().isoformat()  # Thêm thời gian hiện tại
            }
            comments.append(new_comment)
            comment_id = len(comments) - 1  # Vị trí của bình luận mới
 
            # Cập nhật trường comments trong Firestore
            doc_ref.update({'comments': comments})
 
            return {
                'status': 200,
                'data': doc_ref.get().to_dict(),  # Trả về dữ liệu đã cập nhật từ Firestore
                'comment_id': comment_id  # Trả về comment_id của bình luận mới
            }
        else:
            raise ValueError("Question not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/delete')
async def delete_comment(request: IDeleteComment, token: str = Depends(auth_scheme)):
    try:
        # Tham chiếu đến tài liệu câu hỏi cụ thể
        users_ref = fs._db.collection('users')
        user_query = users_ref.where('email', '==', request.id).get()
        if not user_query:
            user_query = users_ref.where('username', '==', request.id).get()
        
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
            
            # Tìm và xóa bình luận có comment_id khớp
            if request.comment_id < 0 or request.comment_id >= len(comments):
                raise ValueError("Comment with the given comment_id not found")

            # Tìm và xóa bình luận có comment_id khớp
            new_comments = [comment for i, comment in enumerate(comments) if i != request.comment_id]

            # Cập nhật lại comment_id cho từng bình luận
            for idx, comment in enumerate(new_comments):
                comment['comment_id'] = idx

            # Cập nhật trường comments trong Firestore
            doc_ref.update({'comments': new_comments})

            return {
                'status': 200,
                'data': doc_ref.get().to_dict()  # Trả về dữ liệu đã cập nhật từ Firestore
            }
        else:
            raise ValueError("Question not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
   