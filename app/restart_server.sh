#!/bin/bash

# Kiểm tra trạng thái server bằng yêu cầu POST đến /login
while true; do
    # Gửi yêu cầu POST đến /login
    login_response=$(curl -s -o /dev/null -w "%{http_code}" -X 'POST' \
      'http://103.138.113.68/login' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "id": "new_user",
      "password": "12345678"
    }')

    # Kiểm tra mã trạng thái HTTP trả về từ /login
    if [ "$login_response" -ne 200 ]; then
        echo "Đăng nhập thất bại (HTTP code: $login_response). Đang khởi động lại server..."
        
        # Dừng ứng dụng Uvicorn
        pkill -f 'uvicorn'
        
        # Khởi động lại ứng dụng Uvicorn
        nohup /root/miniconda3/envs/py308/bin/uvicorn test:app --reload &

    else
        echo "Đăng nhập thành công. Tiếp tục kiểm tra lại server..."
    fi

    # Kiểm tra lại sau mỗi 20 giây
    sleep 20
done
