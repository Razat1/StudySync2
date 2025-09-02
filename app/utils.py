import os
from fastapi import UploadFile
from pdfminer.high_level import extract_text

UPLOAD_DIR = "app/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_upload(file: UploadFile) -> str:
    """Save uploaded file and return path"""
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return file_path

def extract_topics_from_file(path: str):
    """Very basic text extraction from PDF/TXT"""
    topics = []
    if path.lower().endswith(".pdf"):
        text = extract_text(path)
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

    # naive split into lines (improve later)
    for line in text.splitlines():
        line = line.strip()
        if line and len(line.split()) < 12:  # treat short lines as topics
            topics.append(line)

    return topics
