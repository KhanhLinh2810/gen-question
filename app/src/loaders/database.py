from src.middleware import JWTBearer
from src.service.firebase_service import FirebaseService, SessionLocal


# initialize fireabse client
asyncSession = SessionLocal()
fs = FirebaseService(asyncSession)

# Định nghĩa một biến dùng cho xác thực
auth_scheme = JWTBearer(fs.db)