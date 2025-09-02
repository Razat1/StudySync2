from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .db import Base, engine
from .models import User
from .auth import get_db, hash_password, verify_password, add_session_middleware

app = FastAPI(title="StudySync2")
add_session_middleware(app)

templates = Jinja2Templates(directory="app/templates")
Base.metadata.create_all(bind=engine)

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("auth_signup.html", {"request": request, "user": None, "error": None})

@app.post("/signup", response_class=HTMLResponse)
def signup(request: Request, email: str = Form(...), display_name: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse("auth_signup.html", {"request": request, "user": None, "error": "Email already registered"})
    u = User(email=email, display_name=display_name, password_hash=hash_password(password))
    db.add(u)
    db.commit()
    db.refresh(u)
    request.session["user_id"] = u.id
    return RedirectResponse("/", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("auth_login.html", {"request": request, "user": None, "error": None})

@app.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == email).first()
    if not u or not verify_password(password, u.password_hash):
        return templates.TemplateResponse("auth_login.html", {"request": request, "user": None, "error": "Invalid credentials"})
    request.session["user_id"] = u.id
    return RedirectResponse("/", status_code=303)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
