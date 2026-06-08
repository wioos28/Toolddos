#!/usr/bin/env python3
# proxy_generator.py - Tạo proxy HTTP/HTTPS hoạt động thực tế, lưu vào file

import requests
import threading
import queue
import time
import sys
from urllib.parse import urlparse

VERSION = "1.0"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 5
TEST_URL = "http://httpbin.org/ip"
THREADS = 100
OUTPUT_FILE = "working_proxies.txt"

# Nguồn proxy miễn phí
PROXY_SOURCES = [
    "https://free-proxy-list.net/",
    "https://www.sslproxies.org/",
    "https://www.us-proxy.org/",
    "https://www.socks-proxy.net/",
    "https://raw.githubusercontent.com/komutan234/Proxy-List-Free/main/proxies/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/http/data.txt"
]

def fetch_proxies_from_url(url):
    proxies = set()
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=10)
        for line in resp.text.split("\n"):
            line = line.strip()
            if ":" in line and line.count(":") == 1:
                ip, port = line.split(":")
                if ip.replace(".", "").isdigit() and port.isdigit():
                    proxies.add(f"{ip}:{port}")
    except:
        pass
    return proxies

def collect_all_proxies():
    all_proxies = set()
    print("[*] Đang thu thập proxy từ các nguồn...")
    for url in PROXY_SOURCES:
        proxies = fetch_proxies_from_url(url)
        all_proxies.update(proxies)
        print(f"    {url.split('/')[2]}: {len(proxies)} proxy")
    print(f"[+] Tổng proxy thô: {len(all_proxies)}")
    return list(all_proxies)

def check_proxy(proxy):
    proxy_dict = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
    try:
        start = time.time()
        r = requests.get(TEST_URL, proxies=proxy_dict, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        if r.status_code == 200:
            latency = round(time.time() - start, 3)
            return (proxy, latency)
    except:
        pass
    return None

def worker(proxy_queue, result_list, lock):
    while True:
        try:
            proxy = proxy_queue.get_nowait()
        except:
            break
        res = check_proxy(proxy)
        if res:
            with lock:
                result_list.append(res)
        proxy_queue.task_done()

def main():
    proxies = collect_all_proxies()
    if not proxies:
        print("[-] Không có proxy nào. Kiểm tra mạng.")
        sys.exit(1)
    
    q = queue.Queue()
    for p in proxies:
        q.put(p)
    
    results = []
    lock = threading.Lock()
    threads = []
    for _ in range(min(THREADS, len(proxies))):
        t = threading.Thread(target=worker, args=(q, results, lock))
        t.start()
        threads.append(t)
    
    q.join()
    for t in threads:
        t.join()
    
    # Sắp xếp theo độ trễ tăng dần
    results.sort(key=lambda x: x[1])
    
    print(f"\n[+] Số proxy hoạt động: {len(results)}")
    if results:
        with open(OUTPUT_FILE, "w") as f:
            for proxy, lat in results:
                f.write(f"{proxy}\n")
        print(f"[+] Đã lưu vào {OUTPUT_FILE}")
        print("[+] 10 proxy nhanh nhất:")
        for i, (proxy, lat) in enumerate(results[:10], 1):
            print(f"    {i}. {proxy} - {lat}s")
    else:
        print("[-] Không tìm thấy proxy hoạt động nào.")

if __name__ == "__main__":
    main()
