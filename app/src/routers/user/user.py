from fastapi import APIRouter, HTTPException, UploadFile, Depends, File
from fastapi.responses import JSONResponse


from src.interface import *
from src.loaders.database import auth_scheme, fs
from src.routers.user import auth, comment, question, rating, topic

router = APIRouter(
    prefix="/user",      # Tất cả endpoint trong router này bắt đầu bằng /auth
    tags=["user"],       # Hiển thị trong docs (Swagger UI)
)

router.include_router(auth.router)
router.include_router(comment.router)
router.include_router(question.router)
router.include_router(rating.router)
router.include_router(topic.router)

@router.post('/change-password')
async def change_password(user: IChangePassword, token: str = Depends(auth_scheme)):
    """Change password for a user.

    Args:
        user (IChangePassword): user change password model

    Returns:
        JSONResponse: response with status
    """
    try:
        user_data = fs.get_user_by_token(token)

        response = fs.change_password_func(user_data['uid'], user.password, user.new_password)
        return JSONResponse(content={'status': 200, 'message': response['message']})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post('/change-info')
async def change_user_info(user: User, token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
        fs.change_user_info(user_data['uid'], user.email, user.username)
        return JSONResponse(content={'status': 200, 'message': f'User {user.username} info changed successfully'})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upload-avatar")
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

@router.get('/topics-questions')
async def get_all_topics_and_questions(token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
        uid = user_data['uid']
        
        all_topics_and_questions = fs.get_all_topics_and_questions_by_uid(uid)
        
        return JSONResponse(content={'status': 200, 'data': all_topics_and_questions})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/', response_model=User)
async def get_user_info(token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
        return JSONResponse(content={'status': 200, 'data': user_data})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete('/')
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
