from pydantic import BaseModel

class ICreateComment(BaseModel):
    id: str
    user_id: int
    question_id: int
    comment_text: str 