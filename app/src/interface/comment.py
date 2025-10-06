from pydantic import BaseModel

class ICreateComment(BaseModel):
    id: str
    name: str
    question_id: str
    comment: str 

class IDeleteComment(BaseModel):
    id: str
    name: str
    question_id: str
    comment_id: int
