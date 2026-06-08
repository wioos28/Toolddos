#!/usr/bin/env python3
# proxy_generator.py - Tạo proxy hoạt động thực tế, lưu vào working_proxies.txt

import requests
import threading
import queue
import time
import sys

VERSION = "1.1"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 5
TEST_URL = "http://httpbin.org/ip"
THREADS = 100
OUTPUT_FILE = "working_proxies.txt"

# Nguồn proxy miễn phí (đã sửa lỗi URL github)
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

def fetch_proxies_from_url(url):
    proxies = set()
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        for line in resp.text.splitlines():
            line = line.strip()
            if ":" in line and line.count(":") == 1:
                ip, port = line.split(":")
                if ip.replace(".", "").replace(":", "").isdigit() and port.isdigit():
                    proxies.add(f"{ip}:{port}")
    except Exception as e:
        pass
    return proxies

def collect_all_proxies():
    all_proxies = set()
    print("[*] Đang thu thập proxy từ các nguồn...")
    for url in PROXY_SOURCES:
        proxies = fetch_proxies_from_url(url)
        all_proxies.update(proxies)
        domain = url.split("/")[2] if "//" in url else url[:30]
        print(f"    {domain}: {len(proxies)} proxy")
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

def worker(proxy_queue, result_list, lock, stop_event):
    while not stop_event.is_set():
        try:
            proxy = proxy_queue.get(timeout=0.5)
        except queue.Empty:
            break
        res = check_proxy(proxy)
        if res:
            with lock:
                result_list.append(res)
        proxy_queue.task_done()

def main():
    proxies = collect_all_proxies()
    if not proxies:
        print("[-] Không có proxy nào. Kiểm tra mạng hoặc nguồn.")
        sys.exit(1)
    
    q = queue.Queue()
    for p in proxies:
        q.put(p)
    
    results = []
    lock = threading.Lock()
    stop_event = threading.Event()
    threads = []
    num_threads = min(THREADS, len(proxies))
    for _ in range(num_threads):
        t = threading.Thread(target=worker, args=(q, results, lock, stop_event))
        t.daemon = True
        t.start()
        threads.append(t)
    
    # Chờ tối đa TIMEOUT*2 giây cho mỗi proxy
    timeout_total = TIMEOUT * 2 * (len(proxies) // num_threads + 1)
    q.join()
    stop_event.set()
    for t in threads:
        t.join(timeout=1)
    
    # Sắp xếp theo độ trễ
    results.sort(key=lambda x: x[1])
    
    print(f"\n[+] Số proxy hoạt động: {len(results)}")
    if results:
        with open(OUTPUT_FILE, "w") as f:
            for proxy, lat in results:
                f.write(f"{proxy}\n")
        print(f"[+] Đã lưu {len(results)} proxy vào {OUTPUT_FILE}")
        print("[+] 10 proxy nhanh nhất:")
        for i, (proxy, lat) in enumerate(results[:10], 1):
            print(f"    {i}. {proxy} - {lat}s")
        # Kiểm tra thực tế proxy đầu tiên
        test_proxy = results[0][0]
        try:
            test_url = "http://httpbin.org/ip"
            proxies = {"http": f"http://{test_proxy}", "https": f"https://{test_proxy}"}
            r = requests.get(test_url, proxies=proxies, timeout=5)
            print(f"[✓] Kiểm tra proxy đầu: {test_proxy} -> IP thật: {r.json().get('origin', 'OK')}")
        except:
            print(f"[!] Proxy đầu có vẻ chậm hoặc chết, nhưng vẫn được ghi nhận.")
    else:
        print("[-] Không tìm thấy proxy hoạt động nào. Thử lại sau ít phút.")
        # Tạo file rỗng để tránh lỗi không tìm thấy (nhưng ddos_proxy sẽ báo lỗi)
        open(OUTPUT_FILE, "w").close()
        sys.exit(1)

if __name__ == "__main__":
    main()
