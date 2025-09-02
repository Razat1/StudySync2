import os
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .db import Base, engine
from .models import User
from .auth import get_db, hash_password, verify_password, add_session_middleware
from fastapi import UploadFile, File
from .utils import save_upload, extract_topics_from_file
from fastapi.staticfiles import StaticFiles
from .question_gen import generate_dummy_questions


app = FastAPI(title="StudySync2")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
add_session_middleware(app)

templates = Jinja2Templates(directory="app/templates")
Base.metadata.create_all(bind=engine)

def current_user(request, db):
    uid = request.session.get("user_id")
    return db.query(User).filter(User.id == uid).first() if uid else None

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "user": None})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    filename = request.session.get("last_upload_name")  # set in /upload
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "filename": filename}
    )

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
    return RedirectResponse("/dashboard", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("auth_login.html", {"request": request, "user": None, "error": None})

@app.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == email).first()
    if not u or not verify_password(password, u.password_hash):
        return templates.TemplateResponse("auth_login.html", {"request": request, "user": None, "error": "Invalid credentials"})
    request.session["user_id"] = u.id
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse(
        "upload.html", {"request": request, "user": None, "topics": None}
    )

@app.post("/upload", response_class=HTMLResponse)
def upload_file(request: Request, file: UploadFile = File(...)):
    path = save_upload(file)
    topics = extract_topics_from_file(path)

    # remember latest upload in the session for dashboard & questions
    request.session["last_upload_path"] = path
    request.session["last_upload_name"] = os.path.basename(path)

    return RedirectResponse("/questions", status_code=303)


@app.get("/questions", response_class=HTMLResponse)
def questions(request: Request):
    from .utils import extract_topics_from_file
    path = request.session.get("last_upload_path")
    if not path or not os.path.exists(path):
        # No upload yet → send them to upload first
        return RedirectResponse("/upload", status_code=303)

    topics = extract_topics_from_file(path)
    qs = generate_dummy_questions(topics)
    return templates.TemplateResponse(
        "questions.html",
        {"request": request, "user": None, "questions": qs}
    )

