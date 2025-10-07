from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
import jwt

from models import User

class JWTBearer(HTTPBearer):
    def __init__(self, db: AsyncSession, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self._db = db

    async def __call__(self, request: Request) -> Optional[str]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials:
            if credentials.scheme != "Bearer":
                raise HTTPException(status_code=403, detail="auth.invalid_scheme")
            
            user = await self.verify_jwt(credentials.credentials)
            request.state.user = user
            return credentials.credentials

        raise HTTPException(status_code=403, detail="auth.missing_credentials")

    async def verify_jwt(self, token: str) -> User:
        try:
            payload = jwt.decode(token, "your_jwt_secret", algorithms=["HS256"])
            uid = payload.get("uid")

            query = select(User).where(User.id == uid)
            result = await self._db.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(status_code=403, detail="auth.unauthority")
            return user

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail="auth.expired_token")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=403, detail="auth.invalid_token")
