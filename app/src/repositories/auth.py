from src.loaders.database import get_database
from models import User
from sqlalchemy import select, or_
from fastapi import HTTPException

import bcrypt
import jwt
import datetime

from src.interface import ILogin

class AuthRepository:
    def __init__(self):
        self.db = get_database()
 
    async def authenticate_user(self, data: ILogin):
        query = select(User).where(
            or_(
                User.username == data.username_or_email, 
                User.email == data.username_or_email
            )
        )
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=401, detail="auth.username_not_match")
        
        # Check the password
        if not bcrypt.checkpw(data.password.encode('utf-8'), user.password.encode('utf-8')):
            raise HTTPException(status_code=401, detail="auth.password_not_match")
        
        # Generate a JWT token
        token = jwt.encode({
            'uid': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=3)
        }, 'your_jwt_secret', algorithm='HS256')
        
        return token, user.id
    