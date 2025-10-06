from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse


from src.interface import *
from src.loaders.database import fs



router = APIRouter(
    prefix="/public",      # Tất cả endpoint trong router này bắt đầu bằng /auth
    tags=["public"],       # Hiển thị trong docs (Swagger UI)
)

@router.get('/users/topics')
async def get_list_topics_of_user(user_id: str):
    try:
        users_ref = fs._db.collection('users')
        user_query = users_ref.where('email', '==', user_id).limit(1).get()
        if not user_query:
            user_query = users_ref.where('username', '==', user_id).limit(1).get()
       
        if not user_query:
            raise ValueError("Invalid email/username")
 
        user_data = user_query[0].to_dict()
        uid = user_data['uid']
        
        all_topics_and_questions = fs.get_all_topics_and_questions_by_uid(uid)
        
        return JSONResponse(content={'status': 200, 'data': all_topics_and_questions})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/users')    
async def get_user(id: str):
    try:
        users_ref = fs._db.collection('users')
        user_query = users_ref.where('email', '==', id).limit(1).get()
        if not user_query:
            user_query = users_ref.where('username', '==', id).limit(1).get()
       
        if not user_query:
            raise ValueError("Invalid email/username")
        user_data = user_query[0].to_dict()
        return JSONResponse(content={'status': 200, 'data': user_data})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
 