from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from src.interface import *
from src.loaders.database import auth_scheme, fs


router = APIRouter(
    prefix="/questions",      # Tất cả endpoint trong router này bắt đầu bằng /auth
    tags=["questions"],       # Hiển thị trong docs (Swagger UI)
)

@router.put('/')
async def change_topic_name(topic: str, new_topic: str, token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
        uid = user_data['uid']
        response = fs.change_topic_name(uid, topic, new_topic)
        return JSONResponse(content=response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.delete('/')
async def delete_topic(topic_delete: str, token: str = Depends(auth_scheme)):
    try:
        user_data = fs.get_user_by_token(token)
        uid = user_data['uid']
        
        success = fs.delete_topic_by_uid(uid, topic_delete)
        
        if success:
            return JSONResponse(content={'status': 200, 'message': 'Topic deleted successfully'})
        else:
            raise HTTPException(status_code=500, detail="Failed to delete topic")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
   