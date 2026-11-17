import requests
import socket
import ssl
import datetime
import dns.resolver
from urllib.parse import urlparse

# Real Chrome browser ki tarah behave karne ke liye (WAF bypass mein help karega)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def check_https(url):
    try:
        response = requests.get(url, timeout=10, allow_redirects=True, headers=HEADERS)
        is_https = response.url.startswith("https")
        return is_https, response
    except requests.exceptions.Timeout:
        return False, "TIMEOUT"
    except requests.exceptions.ConnectionError:
        return False, "CONNECTION_BLOCKED"
    except requests.exceptions.RequestException:
        return False, "ERROR"

def check_headers(response):
    if not response or isinstance(response, str):
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
    if not hostname:
        return "Unknown", 0
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                expiry_date_str = cert['notAfter']
                expiry_date = datetime.datetime.strptime(expiry_date_str, '%b %d %H:%M:%S %Y %Z')
                days_left = (expiry_date - datetime.datetime.utcnow()).days
                return expiry_date.strftime('%Y-%m-%d'), days_left
    except Exception:
        return "Not Found", 0

def check_dns_records(hostname):
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
        is_https, response = check_https(url)
        
        if isinstance(response, str):
            if response == "TIMEOUT":
                result["error"] = "Request timed out. The website might be blocking our scanner."
            elif response == "CONNECTION_BLOCKED":
                result["error"] = "Connection blocked by the website's security (WAF)."
            else:
                result["error"] = "Unable to connect to the website."
            return result

        result["https"] = is_https
        result["missing_headers"] = check_headers(response)
        result["open_ports"] = check_ports(url)
        
        if hostname:
            result["ssl_expiry_date"], result["ssl_days_left"] = check_ssl_expiry(hostname)
            result["dns_a"], result["dns_mx"] = check_dns_records(hostname)
            
    except Exception as e:
        result["error"] = f"Internal Error: {str(e)}"
        
    return result