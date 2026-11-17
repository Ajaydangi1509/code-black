import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
import os
import time
from typing import Literal
from datetime import datetime
import random
import base64
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field, field_validator

import sqlalchemy as sa
from sqlalchemy.orm import Session
from app.database import engine, Base, get_db

from app.scanner import run_scan

ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))

# --- DATABASE MODELS ---
class Enquiry(Base):
    __tablename__ = "enquiries"
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    name = sa.Column(sa.String, index=True)
    email = sa.Column(sa.String, index=True)
    company = sa.Column(sa.String)
    country = sa.Column(sa.String)
    service = sa.Column(sa.String)
    message = sa.Column(sa.Text)
    status = sa.Column(sa.String, default="new")

class Application(Base):
    __tablename__ = "applications"
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    name = sa.Column(sa.String, index=True)
    email = sa.Column(sa.String, index=True)
    role = sa.Column(sa.String)
    portfolio = sa.Column(sa.String)
    message = sa.Column(sa.Text)
    status = sa.Column(sa.String, default="new")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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

class LeadPayload(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    company: str = Field(default="", max_length=120)
    country: str = Field(min_length=2, max_length=80)
    service: Literal["Web Application VAPT", "Network Security Assessment", "Vulnerability Assessment", "Cybersecurity Consultation", "Security Awareness Training", "Not sure yet"]
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
    url: str = Field(min_length=4, max_length=250)

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
async def create_enquiry(payload: LeadPayload, request: Request, db: Session = Depends(get_db)):
    if not allowed_request(request):
        return JSONResponse({"ok": False, "message": "Too many submissions. Please wait."}, status_code=429)
    if payload.website:
        return {"ok": True, "message": "Thank you. Your enquiry has been received."}
    
    new_enquiry = Enquiry(
        name=payload.name, email=str(payload.email), company=payload.company.strip(), 
        country=payload.country.strip(), service=payload.service, message=payload.message.strip()
    )
    db.add(new_enquiry)
    db.commit()
    db.refresh(new_enquiry)
    return {"ok": True, "message": "Thanks — your enquiry has been received."}

@app.post("/api/applications")
async def create_application(payload: ApplicationPayload, request: Request, db: Session = Depends(get_db)):
    if not allowed_request(request):
        return JSONResponse({"ok": False, "message": "Too many submissions. Please wait."}, status_code=429)
    if payload.website:
        return {"ok": True, "message": "Thank you. Your application of interest has been received."}
    
    new_application = Application(
        name=payload.name, email=str(payload.email), role=payload.role, 
        portfolio=payload.portfolio.strip(), message=payload.message.strip()
    )
    db.add(new_application)
    db.commit()
    db.refresh(new_application)
    return {"ok": True, "message": "Thanks for your interest. We'll contact you if an opportunity opens."}

@app.post("/api/scan")
async def scan_website(payload: ScanRequest, request: Request):
    if not allowed_request(request):
        return JSONResponse({"ok": False, "message": "Too many requests. Please wait."}, status_code=429)
    
    url = payload.url.strip()
    if not url.startswith("http"):
        url = "http://" + url
        
    parsed_url = urlparse(url)
    if not parsed_url.netloc:
        return JSONResponse({"ok": False, "message": "Invalid URL format provided."}, status_code=400)
        
    result = run_scan(url)
    return {"ok": True, "data": result}

def generate_pdf_sync(html_content: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = page.pdf(format="A4", print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()
        return pdf_bytes

@app.get("/api/download_report")
async def download_report(url: str, https: bool, missing_headers: str, ssl_days: int = 0, dns_a: str = "N/A", dns_mx: str = "N/A"):
    headers_list = missing_headers.split(",") if missing_headers else []
    
    score = 100
    if not https: score -= 50
    for header in headers_list:
        if header == "Content-Security-Policy": score -= 20
        elif header == "X-Frame-Options": score -= 15
        elif header == "Strict-Transport-Security": score -= 10
        else: score -= 5
    if ssl_days > 0 and ssl_days < 30: score -= 10
    if score < 0: score = 0
    score_color = "#FF4D4D" if score < 50 else ("#FFA500" if score < 80 else "#38B000")
    
    logo_file_path = ROOT / "static" / "logo.png"
    try:
        with open(logo_file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        logo_data_uri = f"data:image/png;base64,{encoded_string}"
    except FileNotFoundError:
        logo_data_uri = ""

    if len(dns_a) > 60:
        dns_a = dns_a[:60] + "... (multiple IPs)"
    if len(dns_mx) > 60:
        dns_mx = dns_mx[:60] + "..."
    
    context = {
        "target_url": url, "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "report_id": random.randint(1000, 9999), "https": https,
        "missing_headers": headers_list, "score": score, "score_color": score_color,
        "logo_path": logo_data_uri, "ssl_days": ssl_days, "dns_a": dns_a, "dns_mx": dns_mx
    }
    
    html_content = templates.get_template("report.html").render(context)
    pdf_bytes = await asyncio.to_thread(generate_pdf_sync, html_content)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=CodeBlack_Report.pdf"})