from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.interface import IRegister, ILogin
from src.loaders.database import fs


router = APIRouter(
    prefix="/auth",      # Tất cả endpoint trong router này bắt đầu bằng /auth
    tags=["user-auth"],       # Hiển thị trong docs (Swagger UI)
)

@router.post('/register')
async def register_user(user: IRegister):
    """Register a new user with unique email and username validation.

    Args:
        user (IRegister): user registration model

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
    user_data = fs.create_user(user.email, user.username, user.password, False)

    return JSONResponse(content={'status': 201, 'message': 'User registered successfully', 'user_data': user_data})

@router.post('/login')
async def login_user(user: ILogin):
    """Login a user with email/username and password.

    Args:
        user (ILogin): user login model

    Returns:
        JSONResponse: response with token
    """
    try:
        token, uid = fs.authenticate_user(user.id, user.password)

        # Lưu token mới vào Firestore
        await fs.update_user_token(uid, token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(content={'status': 200, 'token': token, 'uid': uid})
