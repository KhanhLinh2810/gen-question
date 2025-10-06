from pydantic import BaseModel

class User(BaseModel):
    uid: str
    email: str
    username: str