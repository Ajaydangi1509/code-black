import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
import os
import sqlite3
import time
from typing import Literal
from datetime import datetime
import random
import base64  # <-- LOGO FIX KE LIYE ADD KIYA

# --- SYNC PLAYWRIGHT IMPORT ---
from playwright.sync_api import sync_playwright

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field, field_validator

# --- SCANNER IMPORT ---
from app.scanner import run_scan
# ----------------------

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", ROOT.parent / "codeblack.db"))
templates = Jinja2Templates(directory=str(ROOT / "templates"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS enquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT,
                country TEXT NOT NULL,
                service TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                role TEXT NOT NULL,
                portfolio TEXT,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new'
            )
        """)
    yield

app = FastAPI(
    title="Code Black Security & Technologies",
    description="Company website and enquiry API",
    version="1.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

RATE_BUCKETS: dict[str, list[float]] = {}
RATE_LIMIT = 8
RATE_WINDOW = 60

def allowed_request(request: Request) -> bool:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    recent = [stamp for stamp in RATE_BUCKETS.get(client_ip, []) if now - stamp < RATE_WINDOW]
    if len(recent) >= RATE_LIMIT:
        RATE_BUCKETS[client_ip] = recent
        return False
    recent.append(now)
    RATE_BUCKETS[client_ip] = recent
    return True

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; font-src 'self' data:; connect-src 'self'; "
        "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    )
    return response

# --- PYDANTIC MODELS ---
class LeadPayload(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    company: str = Field(default="", max_length=120)
    country: str = Field(min_length=2, max_length=80)
    service: Literal[
        "Web Application VAPT",
        "Network Security Assessment",
        "Vulnerability Assessment",
        "Cybersecurity Consultation",
        "Security Awareness Training",
        "Not sure yet",
    ]
    message: str = Field(min_length=20, max_length=3000)
    website: str = Field(default="", max_length=200)

    @field_validator("name", "country", "message")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

class ApplicationPayload(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    role: Literal["Security Research Intern", "Web Development Intern", "Python / Automation Intern"]
    portfolio: str = Field(default="", max_length=300)
    message: str = Field(min_length=20, max_length=2000)
    website: str = Field(default="", max_length=200)

    @field_validator("name", "message")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

class ScanRequest(BaseModel):
    url: str

# --- ROUTES ---
def render_page(request: Request, page: str, title: str, description: str):
    return templates.TemplateResponse(
        request=request,
        name=page,
        context={"request": request, "title": title, "description": description},
    )

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return render_page(request, "home.html", "Code Black | Cybersecurity, clearly delivered", "Responsible cybersecurity services for modern businesses.")

@app.get("/services", response_class=HTMLResponse)
async def services(request: Request):
    return render_page(request, "services.html", "Services | Code Black", "Web application security, network assessments, vulnerability reviews, consultation and awareness.")

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return render_page(request, "about.html", "About | Code Black", "Learn about the principles behind Code Black Security & Technologies.")

@app.get("/careers", response_class=HTMLResponse)
async def careers(request: Request):
    return render_page(request, "careers.html", "Careers | Code Black", "Express interest in future learning and internship opportunities at Code Black.")

@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return render_page(request, "contact.html", "Contact | Code Black", "Discuss your cybersecurity requirements with Code Black.")

@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return render_page(request, "privacy.html", "Privacy | Code Black", "How Code Black handles information submitted through this website.")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "code-black-website"}

@app.post("/api/enquiries")
async def create_enquiry(payload: LeadPayload, request: Request):
    if not allowed_request(request):
        return JSONResponse({"ok": False, "message": "Too many submissions. Please wait a minute and try again."}, status_code=429)
    if payload.website:
        return {"ok": True, "message": "Thank you. Your enquiry has been received."}
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO enquiries (name,email,company,country,service,message)
               VALUES (?,?,?,?,?,?)""",
            (payload.name, str(payload.email), payload.company.strip(), payload.country.strip(),
             payload.service, payload.message.strip()),
        )
    return {"ok": True, "message": "Thanks — your enquiry has been received. We'll review it and follow up."}

@app.post("/api/applications")
async def create_application(payload: ApplicationPayload, request: Request):
    if not allowed_request(request):
        return JSONResponse({"ok": False, "message": "Too many submissions. Please wait a minute and try again."}, status_code=429)
    if payload.website:
        return {"ok": True, "message": "Thank you. Your application of interest has been received."}
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO applications (name,email,role,portfolio,message)
               VALUES (?,?,?,?,?)""",
            (payload.name, str(payload.email), payload.role, payload.portfolio.strip(), payload.message.strip()),
        )
    return {"ok": True, "message": "Thanks for your interest. We'll contact you if a suitable opportunity opens."}

# --- SCANNER API ROUTE ---
@app.post("/api/scan")
async def scan_website(payload: ScanRequest, request: Request):
    if not allowed_request(request):
        return JSONResponse({"ok": False, "message": "Too many requests. Please wait."}, status_code=429)
    
    url = payload.url.strip()
    if not url.startswith("http"):
        url = "http://" + url
        
    result = run_scan(url)
    return {"ok": True, "data": result}

# --- HELPER FUNCTION FOR PLAYWRIGHT (Sync) ---
def generate_pdf_sync(html_content: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = page.pdf(
            format="A4", 
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"}
        )
        browser.close()
        return pdf_bytes

# --- PDF REPORT ROUTE ---
@app.get("/api/download_report")
async def download_report(url: str, https: bool, missing_headers: str):
    headers_list = missing_headers.split(",") if missing_headers else []
    
    score = 100
    if not https: score -= 40
    score -= (len(headers_list) * 10)
    if score < 0: score = 0
    
    score_color = "#FF4D4D" if score < 50 else ("#FFA500" if score < 80 else "#38B000")
    
    # --- BASE64 LOGO FIX ---
    logo_file_path = ROOT / "static" / "logo.png"
    try:
        with open(logo_file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        logo_data_uri = f"data:image/png;base64,{encoded_string}"
    except FileNotFoundError:
        logo_data_uri = "" # Fallback if image is missing
    
    context = {
        "target_url": url,
        "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "report_id": random.randint(1000, 9999),
        "https": https,
        "missing_headers": headers_list,
        "score": score,
        "score_color": score_color,
        "logo_path": logo_data_uri  # <-- Base64 URI sent to template
    }
    
    # HTML Render karo
    html_content = templates.get_template("report.html").render(context)
    
    # Playwright PDF generation ko alag thread mein chalao (Windows fix)
    pdf_bytes = await asyncio.to_thread(generate_pdf_sync, html_content)
    
    # PDF return karo
    return Response(
        content=pdf_bytes, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=CodeBlack_Report.pdf"}
    )