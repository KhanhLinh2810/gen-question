from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional

class JWTBearer(HTTPBearer):
    def __init__(self, db, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self._db = db  # Lưu db vào thuộc tính của class

    async def __call__(self, request: Request) -> Optional[str]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")
    
    def verify_jwt(self, token: str) -> bool:
        try:
            # Decode the JWT token để lấy user UID
            payload = jwt.decode(token, "your_jwt_secret", algorithms=["HS256"])
            uid = payload.get('uid')  # Giả định UID nằm trong payload

            # Lấy token hiện tại từ Firestore để kiểm tra
            user_ref = self._db.collection('users').document(uid).get()
            current_token = user_ref.get('current_token')

            if current_token != token:
                raise HTTPException(status_code=403, detail="Token expired due to new login")

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=403, detail="Invalid token")

        return True
