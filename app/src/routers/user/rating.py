from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse


from src.interface import *
from src.repositories import RatingRepository
from src.utils import res_ok


router = APIRouter(
    prefix="/ratings",      # Tất cả endpoint trong router này bắt đầu bằng /ratings
    tags=["ratings"],       # Hiển thị trong docs (Swagger UI)
)

@router.post('/')
async def create_or_update_rating(body: ICreateRating, request: Request):
    try:
        rating_repo = RatingRepository()
        user_id = request.state.user["uid"]

        exist_rating = await rating_repo.get_many(user_id, body.question_id)
        if exist_rating:
            await rating_repo.update(user_id, body)
        else:
            await rating_repo.create_rating(user_id, body)

        return JSONResponse(status_code=200, content= res_ok())     
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
 

@router.delete("/{question_id}")
async def delete_rating(request: Request, question_id: int):
    try:
        rating_repo = RatingRepository()
        user_id = request.state.user["uid"]

        await rating_repo.delete_by_user_and_question(user_id, question_id)

        return JSONResponse(status_code=200, content=res_ok(message="Rating deleted successfully"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
