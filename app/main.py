"""Main python file for flask application.

This module handles all API requests.

@Author: Karthick T. Sharma
"""

from fastapi import FastAPI

import pytesseract

from src.routers.guest import public
from src.routers.user import user

# FastAPI setup
app = FastAPI()

# Chỉ định đường dẫn đến tệp thực thi Tesseract nếu không nằm trong PATH
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\Admin\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'  # Đường dẫn dành cho Windows
# Đối với Ubuntu hoặc macOS, bạn có thể bỏ qua dòng này nếu Tesseract đã được thêm vào PATH

app.include_router(public.router)
app.include_router(user.router)