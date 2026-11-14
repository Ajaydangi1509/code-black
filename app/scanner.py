import requests
import socket
from urllib.parse import urlparse

def check_https(url):
    try:
        response = requests.get(url, timeout=5, allow_redirects=True)
        is_https = response.url.startswith("https")
        return is_https, response
    except requests.exceptions.RequestException:
        return False, None

def check_headers(response):
    if not response:
        return []
        
    headers_to_check = [
        'Strict-Transport-Security',
        'X-Frame-Options',
        'Content-Security-Policy',
        'X-Content-Type-Options'
    ]
    missing_headers = []
    for header in headers_to_check:
        if header not in response.headers:
            missing_headers.append(header)
    return missing_headers

def check_ports(url):
    hostname = urlparse(url).hostname
    if not hostname:
        return []

    open_ports = []
    for port in [80, 443, 22]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex((hostname, port))
        if result == 0:
            open_ports.append(port)
        s.close()
    return open_ports

# Ye function FastAPI se call hoga
def run_scan(url):
    result = {
        "https": False,
        "missing_headers": [],
        "open_ports": [],
        "error": None
    }
    
    try:
        # 1. HTTPS
        is_https, response = check_https(url)
        if not response:
            result["error"] = "Website down or invalid URL."
            return result
            
        result["https"] = is_https
        
        # 2. Headers
        result["missing_headers"] = check_headers(response)
        
        # 3. Ports
        result["open_ports"] = check_ports(url)
        
    except Exception as e:
        result["error"] = str(e)
        
    return result

# Local testing ke liye (Terminal me run kar sakte ho)
if __name__ == "__main__":
    print(run_scan("https://example.com"))