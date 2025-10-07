from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    uid: str
    email: str
    username: str

class IFilterUser(BaseModel):
    email: Optional[str]
    username: Optional[str]
    email_or_username: Optional[str]