from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="StudySync2")

@app.get("/", response_class=HTMLResponse)
def home():
    return "<h1>Welcome to StudySync2 🚀</h1><p>Your app is running!</p>"
