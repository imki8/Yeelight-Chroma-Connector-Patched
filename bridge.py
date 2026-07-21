import socket
import struct
import json
import threading
import time

# Configuration
REAL_LAMP_IP = "192.168.1.124"
REAL_LAMP_TCP_PORT = 55443
BRIDGE_UDP_PORT = 55444

MCAST_GRP = '239.255.255.250'
MCAST_PORT = 1982

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

LOCAL_IP = get_lan_ip()

def get_ssdp_reply():
    return (
        "HTTP/1.1 200 OK\r\n"
        "Cache-Control: max-age=3600\r\n"
        "Date: \r\n"
        "Ext: \r\n"
        f"Location: yeelight://{LOCAL_IP}:{BRIDGE_UDP_PORT}\r\n"
        "Server: POSIX UPnP/1.0 YGLC/1\r\n"
        "id: 0x0000000012345678\r\n"
        "model: color\r\n"
        "fw_ver: 35\r\n"
        "support: get_prop set_default set_power toggle set_bright start_cf stop_cf set_scene cron_add cron_get cron_del set_ct_abx udp_sess_new udp_sess_keep_alive udp_new bg_set_rgb bg_set_scene\r\n"
        "power: on\r\n"
        "bright: 100\r\n"
        "color_mode: 1\r\n"
        "ct: 4000\r\n"
        "rgb: 16711680\r\n"
        "hue: 100\r\n"
        "sat: 100\r\n"
        "name: RazerBridge\r\n\r\n"
    ).encode('utf-8')

tcp_socket = None

def get_tcp_socket():
    global tcp_socket
    if tcp_socket is None:
        try:
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.settimeout(2.0)
            tcp_socket.connect((REAL_LAMP_IP, REAL_LAMP_TCP_PORT))
            print(f"Connected to real lamp via TCP ({REAL_LAMP_IP})")
        except Exception as e:
            print(f"Failed to connect to lamp: {e}")
            tcp_socket = None
    return tcp_socket

def ssdp_listener():
    # Socket for broadcasting our presence
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    broadcast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    
    # We also listen just in case
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.bind(('', MCAST_PORT))
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    try:
        listen_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except:
        pass
    
    print(f"Broadcasting fake lamp profile to {MCAST_GRP}:{MCAST_PORT} every 2 seconds...")
    print(f"Also sending direct unicast to {LOCAL_IP}:{MCAST_PORT}...")
    
    # Run a sub-thread to continuously announce the lamp
    def announce():
        while True:
            try:
                # Multicast
                broadcast_sock.sendto(get_ssdp_reply(), (MCAST_GRP, MCAST_PORT))
                # Direct Unicast to the Official App (bypasses all multicast loopback issues)
                broadcast_sock.sendto(get_ssdp_reply(), (LOCAL_IP, MCAST_PORT))
                broadcast_sock.sendto(get_ssdp_reply(), ('127.0.0.1', MCAST_PORT))
            except Exception as e:
                pass
            time.sleep(2)
            
    threading.Thread(target=announce, daemon=True).start()
    
    while True:
        try:
            data, addr = listen_sock.recvfrom(1024)
            msg = data.decode('utf-8', errors='ignore')
            if "M-SEARCH" in msg and "wifi_bulb" in msg:
                resp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                resp_sock.sendto(get_ssdp_reply(), addr)
                resp_sock.close()
        except Exception as e:
            time.sleep(1)

def udp_proxy():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', BRIDGE_UDP_PORT))
    print(f"Listening for UDP Commands from Official App on port {BRIDGE_UDP_PORT}...")
    
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            msg = data.decode('utf-8', errors='ignore').strip()
            
            if not msg:
                continue
                
            try:
                j = json.loads(msg)
                method = j.get("method")
                
                # Handle UDP Handshake
                if method in ["udp_new", "udp_sess_new"]:
                    msg_id = j.get("id", 1)
                    reply = json.dumps({"id": msg_id, "result": ["token123"]}) + "\r\n"
                    sock.sendto(reply.encode('utf-8'), addr)
                    continue
                elif method == "udp_sess_keep_alive":
                    msg_id = j.get("id", 1)
                    reply = json.dumps({"id": msg_id, "result": ["ok"]}) + "\r\n"
                    sock.sendto(reply.encode('utf-8'), addr)
                    continue
                
                # It's a color command (set_rgb, bg_set_rgb, etc)
                # Strip token/sid for actual commands
                if "token" in j:
                    del j["token"]
                if "sid" in j:
                    del j["sid"]
                    
                clean_msg = json.dumps(j) + "\r\n"
                
                # Send to TCP
                tsock = get_tcp_socket()
                if tsock:
                    try:
                        tsock.sendall(clean_msg.encode('utf-8'))
                    except Exception as e:
                        # Reconnect on next packet
                        global tcp_socket
                        if tcp_socket:
                            tcp_socket.close()
                        tcp_socket = None
                        
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {msg}")
                
        except Exception as e:
            print(f"UDP Proxy Error: {e}")

if __name__ == '__main__':
    print("==========================================")
    print("       Yeelight Razer Bridge active       ")
    print(f"   Target Lamp: {REAL_LAMP_IP}:{REAL_LAMP_TCP_PORT} ")
    print("==========================================")
    print("1. Leave this window open.")
    print("2. Open the OFFICIAL Yeelight Chroma Connector.")
    print("3. The lamp 'RazerBridge' should appear.")
    print("4. Check 'Enable Chroma' and enjoy!")
    print("==========================================")
    
    # Start SSDP thread
    t1 = threading.Thread(target=ssdp_listener, daemon=True)
    t1.start()
    
    # Run UDP proxy in main thread
    udp_proxy()
