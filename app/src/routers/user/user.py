from fastapi import APIRouter, HTTPException, UploadFile, Depends, File, Request
from fastapi.responses import JSONResponse


from src.interface import *
from src.routers.user import comment, question, rating, topic
from src.middleware import JWTBearer
from src.loaders.database import get_database
from src.repositories import UserRepository
from src.utils import res_ok

router = APIRouter(
    prefix="/user",      # Tất cả endpoint trong router này bắt đầu bằng /auth
    tags=["user"],       # Hiển thị trong docs (Swagger UI)
    dependencies=[Depends(lambda: JWTBearer(get_database()))]
)

router.include_router(comment.router)
router.include_router(question.router)
router.include_router(rating.router)
router.include_router(topic.router)

@router.put('/change-password')
async def change_password(data: IChangePassword, request: Request):
    try:
        user_repo = UserRepository()
        user = request.state.user
        await user_repo.change_password(user.id, data.new_password)
        return JSONResponse(status_code=200, content= res_ok(data=user))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.put('/change-info')
async def change_user_info(user: User, request: Request):
    try:
        user_repo = UserRepository()
        user = request.state.user
        await user_repo.change_user_info(user['uid'], user.email, user.username)
        return JSONResponse(status_code=200, content= res_ok(data=user))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upload-avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    """Upload avatar for a user and update Firestore.

    Args:
        file: File object of the avatar image.

    Returns:
        dict: Information about the uploaded avatar.
    """
    try:
        user_repo = UserRepository()
        user = request.state.user

        avatar_url = user_repo.upload_avatar(user["uid"], file)
        return JSONResponse(status_code=200, content= res_ok(data={avatar_url}))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# @router.get('/topics-questions')
# async def get_all_topics_and_questions(request: Request):
#     try:
#         user_repo = UserRepository()
#         user = request.state.user
#         uid = user["uid"]
        
#         all_topics_and_questions = fs.get_all_topics_and_questions_by_uid(uid)
        
#         return JSONResponse(content={'status': 200, 'data': all_topics_and_questions})
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))

@router.get('/me', response_model=User)
async def get_user_info(request: Request):
    try:
        user = request.state.user
        return JSONResponse(status_code=200, content= res_ok(data=user))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete('/')
async def delete_user(request: Request):
    try:
        user_repo = UserRepository()
        user = request.state.user
        await user_repo.delete_user(user["uid"])
        
        return JSONResponse(status_code=200, content= res_ok(data={id: user["uid"]}))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
