from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from src.interface import *
from src.repositories import TopicRepository
from src.utils import res_ok

router = APIRouter(
    prefix="/questions",      # Tất cả endpoint trong router này bắt đầu bằng /auth
    tags=["questions"],       # Hiển thị trong docs (Swagger UI)
)

@router.put('/')
async def change_topic_name(topic: str, new_topic: str, request: Request):
    try:
        topic_repo = TopicRepository()
        user_id = request.state.user["uid"]
        await topic_repo.change_topic_name(user_id, topic, new_topic)
        return JSONResponse(status_code=200, content= res_ok())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.delete('/')
async def delete_topic(topic: str, request: Request):
    try:
        topic_repo = TopicRepository()
        user_id = request.state.user["uid"]
        await topic_repo.delete_question_by_topic(user_id, topic)
        return JSONResponse(status_code=200, content= res_ok())

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
   