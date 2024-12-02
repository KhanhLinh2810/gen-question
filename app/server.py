import subprocess
import time
import requests

# Hàm để khởi động server với Uvicorn
def start_server():
    # Đảm bảo sử dụng đúng virtualenv nếu cần thiết
    uvicorn_command = '/root/miniconda3/envs/py308/bin/uvicorn test:app --reload'
    subprocess.Popen(uvicorn_command, shell=True)
    print("Server đang chạy...")

# Hàm gửi yêu cầu POST đến /login
def login():
    url = 'http://103.138.113.68/login'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        "identifier": "new_user",
        "password": "12345678"
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        return response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gửi yêu cầu đăng nhập: {e}")
        return None

# Hàm để kiểm tra và khởi động lại server nếu cần thiết
def monitor_and_restart():
    while True:
        print("Đang kiểm tra trạng thái server...")
        
        # Gửi yêu cầu POST đến /login
        login_response = login()
        
        if login_response != 200 and login_response is not None:
            print(f"Đăng nhập thất bại (HTTP code: {login_response}). Đang khởi động lại server...")
            
            # Dừng ứng dụng Uvicorn và khởi động lại server
            subprocess.call(['pkill', '-f', 'uvicorn'])
            start_server()

        # Kiểm tra lại sau mỗi 20 giây
        time.sleep(20)

if __name__ == '__main__':
    start_server()  # Bắt đầu chạy server
    time.sleep(30)  # Chờ 30 giây trước khi tiếp tục
    monitor_and_restart()  # Bắt đầu theo dõi và khởi động lại server nếu cần
