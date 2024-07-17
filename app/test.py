import bcrypt

# Lấy mật khẩu từ người dùng (thường là một chuỗi)
password = "12345678"

# Hash mật khẩu
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

print(hashed_password)
print(hashed_password.decode('utf-8'))