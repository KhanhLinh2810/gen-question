from pydantic import BaseModel

class ICreateRating(BaseModel):
    """Rating questions."""
    id: str
    user_id: int
    question_id: int
    rating_value: int

class IDeleteRating(BaseModel):
    id: str
    name: str
    question_id: str
