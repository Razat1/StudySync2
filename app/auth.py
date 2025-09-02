from fastapi import Request, HTTPException
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import User
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def require_user(request: Request, db: Session) -> User:
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user

def add_session_middleware(app):
    secret = os.getenv("SECRET_KEY", "dev-secret")
    app.add_middleware(SessionMiddleware, secret_key=secret)
