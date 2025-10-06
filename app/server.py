import subprocess
import time
import requests

# Hàm để khởi động server với Uvicorn
def start_server():
    # Đảm bảo sử dụng đúng virtualenv nếu cần thiết
    uvicorn_command = '/root/miniconda3/envs/py308/bin/uvicorn test:app --reload'
    subprocess.Popen(uvicorn_command, shell=True)
    print("Server đang chạy...")

# Hàm gửi yêu cầu POST đến /login với thời gian chờ là 8 giây
def login():
    url = 'http://103.138.113.68/login'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        "id": "new_user",
        "password": "12345678"
    }

    try:
        # Thêm tham số timeout để chờ 8 giây
        response = requests.post(url, json=data, headers=headers, timeout=8)
        return response.status_code
    except requests.exceptions.Timeout:
        print("Yêu cầu đăng nhập bị timeout sau 8 giây.")
        subprocess.call(['pkill', '-f', 'uvicorn'])
        start_server()
        return None
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gửi yêu cầu đăng nhập: {e}")
        subprocess.call(['pkill', '-f', 'uvicorn'])
        start_server()
        return None

# Hàm để kiểm tra và khởi động lại server nếu cần thiết
def monitor_and_restart():
    while True:
        print("Đang kiểm tra trạng thái server...")
        
        # Gửi yêu cầu POST đến /login
        login_response = login()
        print(login_response)
        
        if login_response != 200 and login_response is not None:
            print(f"Đăng nhập thất bại (HTTP code: {login_response}). Đang khởi động lại server...")
            
            # Dừng ứng dụng Uvicorn và khởi động lại server
            # subprocess.call(['pkill', '-f', 'uvicorn'])
            # start_server()

        # Kiểm tra lại sau mỗi 80 giây
        time.sleep(80)

if __name__ == '__main__':
    start_server()  # Bắt đầu chạy server
    time.sleep(80)  # Chờ 80 giây trước khi tiếp tục
    monitor_and_restart()  # Bắt đầu theo dõi và khởi động lại server nếu cần
