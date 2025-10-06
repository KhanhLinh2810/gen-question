from fastapi import APIRouter, HTTPException, Depends


from src.interface import *
from src.loaders.database import auth_scheme, fs


router = APIRouter(
    prefix="/ratings",      # Tất cả endpoint trong router này bắt đầu bằng /ratings
    tags=["ratings"],       # Hiển thị trong docs (Swagger UI)
)

@router.post('/')
async def create_rating(request: ICreateRating, token: str = Depends(auth_scheme)):
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
 

@router.post('/delete')
async def delete_rating(request: IDeleteRating, token: str = Depends(auth_scheme)):
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
            ratings = data.get('rating', [])

            # Xoá đánh giá có uid khớp
            new_ratings = [rating for rating in ratings if not rating['uid'] == user_data['uid']]
        
            if len(ratings) == len(new_ratings):
                raise ValueError("Rating with the given UID not found")

            # Cập nhật trường rating trong Firestore
            doc_ref.update({'rating': new_ratings})

            # Tính toán điểm trung bình
            average_rating = sum(r['rate'] for r in new_ratings) / len(new_ratings) if new_ratings else 0

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
