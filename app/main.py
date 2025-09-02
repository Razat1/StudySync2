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
from sqlalchemy.orm import Session
from .services import create_study_guide, add_topics, get_guide, get_topics, set_selected


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
def upload_file(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    # save file
    path = save_upload(file)
    topics = extract_topics_from_file(path)

    # remember in session for dashboard/questions
    request.session["last_upload_path"] = path
    request.session["last_upload_name"] = os.path.basename(path)

    # tie to current user if logged in
    uid = request.session.get("user_id")

    # create study guide row
    guide = create_study_guide(db, user_id=uid, filename=path, original_name=file.filename)

    # add extracted topics
    if topics:
        add_topics(db, guide.id, topics)

    # go to topics page
    return RedirectResponse(f"/topics/{guide.id}", status_code=303)



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

@app.get("/topics/{guide_id}", response_class=HTMLResponse)
def topics_page(guide_id: int, request: Request, db: Session = Depends(get_db)):
    guide = get_guide(db, guide_id)
    if not guide:
        return RedirectResponse("/upload", status_code=303)
    topics = get_topics(db, guide_id)
    # pass logged-in user (optional greeting in navbar)
    from .models import User
    user = None
    uid = request.session.get("user_id")
    if uid:
        user = db.query(User).filter(User.id == uid).first()
    return templates.TemplateResponse("topics.html", {"request": request, "user": user, "guide": guide, "topics": topics})

@app.post("/topics/{guide_id}/save")
async def save_topics(guide_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    checked = {k for k in form.keys() if k.startswith("topic_")}
    ids_checked = {int(k.split("_")[1]) for k in checked}

    # update all topics
    for t in get_topics(db, guide_id):
        set_selected(db, t.id, t.id in ids_checked)

    return RedirectResponse(f"/topics/{guide_id}", status_code=303)

@app.post("/topics/{guide_id}/add")
async def add_manual(guide_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    raw = (form.get("raw_topics") or "").strip()
    if raw:
        titles = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        add_topics(db, guide_id, titles)
    return RedirectResponse(f"/topics/{guide_id}", status_code=303)

@app.get("/questions/{topic_id}", response_class=HTMLResponse)
def questions_for_topic(topic_id: int, request: Request, db: Session = Depends(get_db)):
    from .models import Topic
    t = db.query(Topic).filter(Topic.id == topic_id).first()
    if not t:
        return RedirectResponse("/upload", status_code=303)

    # build questions from this single topic
    qs = generate_dummy_questions([t.title], num_questions=5)

    # optional user in navbar
    from .models import User
    user = None
    uid = request.session.get("user_id")
    if uid:
        user = db.query(User).filter(User.id == uid).first()

    return templates.TemplateResponse(
        "questions.html",
        {"request": request, "user": user, "questions": qs}
    )

