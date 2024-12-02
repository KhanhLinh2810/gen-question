#!/bin/bash

# Kiểm tra trạng thái server bằng yêu cầu POST
while true; do
    # Gửi yêu cầu POST
    response=$(curl -s -o /dev/null -w "%{http_code}" -X 'POST' \
      'http://103.138.113.68/get-question' \
      -H 'accept: application/json' \
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOjEsImV4cCI6MTczMzEyNjY5MH0.T_UBitDCTgiEsH8bi4rradPRkaXx7VgWp6g9VXICsPE' \
      -H 'Content-Type: application/json' \
      -d '{
      "context": "Biến đổi khí hậu đang gây ảnh hưởng nghiêm trọng.",
      "name": "Vấn đề hôm nay",
      "tags": ["Đời sống", "Xã hội"]
    }')

    # Kiểm tra mã trạng thái HTTP trả về
    if [ "$response" -ne 200 ]; then
        echo "Yêu cầu thất bại (HTTP code: $response). Đang khởi động lại server..."
        pkill -f 'uvicorn'  # Dừng ứng dụng Uvicorn
        nohup /root/miniconda3/envs/py308/bin/uvicorn test:app --host 0.0.0.0 --port 8000 --reload &  # Khởi động lại ứng dụng Uvicorn
    fi
    sleep 10  # Kiểm tra lại sau mỗi 10 giây
done
