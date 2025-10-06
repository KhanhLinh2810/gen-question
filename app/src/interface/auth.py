from pydantic import BaseModel, EmailStr, constr

class IRegister(BaseModel):
    email: EmailStr
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=6)

class ILogin(BaseModel):
    id: str  # email or username
    password: str

class IChangePassword(BaseModel):
    password: str
    new_password: str

