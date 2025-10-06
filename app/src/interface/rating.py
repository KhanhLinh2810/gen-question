from pydantic import BaseModel

class ICreateRating(BaseModel):
    """Rating questions."""
    id: str
    name: str
    question_id: str
    rate: int

class IDeleteRating(BaseModel):
    id: str
    name: str
    question_id: str
