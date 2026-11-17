import requests
import socket
import ssl
import datetime
import dns.resolver
from urllib.parse import urlparse

# Real Chrome browser ki tarah behave karne ke liye
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def check_https(url):
    try:
        response = requests.get(url, timeout=5, allow_redirects=True, headers=HEADERS)
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

def check_ssl_expiry(hostname):
    """Check SSL Certificate Expiry Date"""
    if not hostname:
        return "Unknown", 0
        
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                expiry_date_str = cert['notAfter']
                # Format: 'Nov 16 12:00:00 2026 GMT'
                expiry_date = datetime.datetime.strptime(expiry_date_str, '%b %d %H:%M:%S %Y %Z')
                days_left = (expiry_date - datetime.datetime.utcnow()).days
                return expiry_date.strftime('%Y-%m-%d'), days_left
    except Exception:
        return "Not Found", 0

def check_dns_records(hostname):
    """Check A and MX records"""
    if not hostname:
        return "Unknown", "Unknown"
    
    a_record = "Not Found"
    mx_record = "Not Found"
    
    try:
        answers = dns.resolver.resolve(hostname, 'A')
        a_record = ", ".join([str(rdata) for rdata in answers])
    except Exception:
        pass
        
    try:
        answers = dns.resolver.resolve(hostname, 'MX')
        mx_record = ", ".join([str(rdata.exchange) for rdata in answers])
    except Exception:
        pass
        
    return a_record, mx_record

def run_scan(url):
    hostname = urlparse(url).hostname
    result = {
        "https": False,
        "missing_headers": [],
        "open_ports": [],
        "ssl_expiry_date": "N/A",
        "ssl_days_left": 0,
        "dns_a": "N/A",
        "dns_mx": "N/A",
        "error": None
    }
    
    try:
        # 1. HTTPS & Headers
        is_https, response = check_https(url)
        if not response:
            result["error"] = "Website down or invalid URL."
            return result
            
        result["https"] = is_https
        result["missing_headers"] = check_headers(response)
        
        # 2. Ports
        result["open_ports"] = check_ports(url)
        
        # 3. SSL & DNS (Sirf tab check karo jab hostname valid ho)
        if hostname:
            result["ssl_expiry_date"], result["ssl_days_left"] = check_ssl_expiry(hostname)
            result["dns_a"], result["dns_mx"] = check_dns_records(hostname)
            
    except Exception as e:
        result["error"] = str(e)
        
    return result

if __name__ == "__main__":
    print(run_scan("https://google.com"))