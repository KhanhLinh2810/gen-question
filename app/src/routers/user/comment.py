from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from datetime import datetime


from src.interface import *
from src.repositories import CommentRepository
from src.utils import res_ok

# comment of question
router = APIRouter(
    prefix="/comments",      # Tất cả endpoint trong router này bắt đầu bằng /comment
    tags=["comments"],       # Hiển thị trong docs (Swagger UI)
)

@router.post('/')
async def create_comment(body: ICreateComment, request: Request):
    try:
        comment_repo = CommentRepository()
        user_id = request.state.user["uid"]
        comment = await comment_repo.create_comment(user_id, body)
        return JSONResponse(status_code=200, content=res_ok(comment))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete('/{comment_id}')
async def delete_comment(request: Request, comment_id: int):
    try:
        comment_repo = CommentRepository()
        user_id = request.state.user["uid"]

        await comment_repo.find_and_check_authority(user_id, comment_id)
        await comment_repo.delete_by_id(comment_id)

        return JSONResponse(status_code=200, content=res_ok())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
   