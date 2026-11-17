import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

raw_db_url = os.environ.get("DATABASE_URL")

if raw_db_url:
    # Render 'postgres://' deta hai, use theek karo aur psycopg2 use karne ko force karo
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    
    # Ye line SQLAlchemy ko force karegi ki wo psycopg2 use kare, psycopg nahi
    if raw_db_url.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    else:
        SQLALCHEMY_DATABASE_URL = raw_db_url
else:
    # Local testing ke liye SQLite fallback
    SQLALCHEMY_DATABASE_URL = "sqlite:///./codeblack.db"

# Engine setup (SQLite ke liye alag config chahiye hota hai)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()