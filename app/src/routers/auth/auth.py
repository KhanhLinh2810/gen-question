from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.interface import IRegister, ILogin
from src.loaders.database import get_database
from src.repositories import UserRepository, AuthRepository
from src.utils import res_ok


router = APIRouter(
    prefix="/auth",      # Tất cả endpoint trong router này bắt đầu bằng /auth
    tags=["auth"],       # Hiển thị trong docs (Swagger UI)
)

@router.post('/user/register')
async def register_user(user: IRegister):
    """Register a new user with unique email and username validation.

    Args:
        user (IRegister): user registration model

    Returns:
        JSONResponse: response with status
    """
    user_repo = UserRepository()
    new_user = await user_repo.create_user(user.email, user.username, user.password)

    return JSONResponse(status_code=200, content=res_ok(data=new_user))

@router.post('/user/login')
async def login_user(body: ILogin):
    """Login a user with email/username and password.

    Args:
        user (ILogin): user login model

    Returns:
        JSONResponse: response with token
    """
    try:
        auth_repo = AuthRepository()
        token= await auth_repo.authenticate_user(body)
        return JSONResponse(status_code=200, content=res_ok(data={"access_token": token}))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

