import os
import re
from typing import List, Optional
from fastapi import UploadFile
from pdfminer.high_level import extract_text

# -------------------------------
# File Upload Handling
# -------------------------------

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_upload(file: UploadFile) -> str:
    """Save uploaded file and return path."""
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return file_path


# -------------------------------
# PDF Text Extraction
# -------------------------------

def extract_text_from_pdf(path: str) -> str:
    """Extract raw text from a PDF file."""
    try:
        return extract_text(path)
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""


# -------------------------------
# Config: Subject Boundaries
# -------------------------------

NEXT_SUBJECT = [
    "English",
    "Mathematics",
    "Biology",
    "Chemistry",
    "Physics",
    "Combined Science",
    "History",
    "Geography",
    "Art",
    "Business",
    "Computer Science",
    "Drama",
    "Music",
    "Physical Education",
    "Religious Studies",
    "French",
    "German",
    "Spanish",
    "Design and Technology",
    "Food Preparation and Nutrition",
    "Media Studies",
    "Classical Civilisation",
]


# -------------------------------
# Topic Extraction
# -------------------------------

# -------------------------------
# Topic Extraction – Maths only, concise
# -------------------------------

MATH_FAMILY = {
    "number",
    "algebra",
    "ratio",
    "proportion",
    "rates of change",
    "geometry",
    "measures",
    "probability",
    "statistics",
}

PAPER_KEYS = ("paper 1h", "paper 2h", "paper 3h", "non calculator", "calculator")

DROP_STARTS = (
    "head of subject", "aims", "what will i study", "how will i be assessed",
    "further information", "extra-curricular", "extra-curricular opportunities",
)
# if a line starts with any of those (case-insensitive), skip it

def _slice_subject(lines, focus_subject: str) -> list[str]:
    """Return only the lines from <focus_subject> up to the next subject headline."""
    # Known subject headers to detect "next subject"
    next_subjects = [
        "English Language", "English Literature", "Mathematics",
        "Biology", "Chemistry", "Physics", "Combined Science",
        "MFL", "Modern Foreign Languages", "French", "German", "Spanish",
        "Art and Design", "Business Studies", "Classical Civilisation",
        "Computer Science", "Drama", "Design and Technology",
        "Design Technology; Fashion & Textiles", "Fashion and Textiles",
        "Food Preparation and Nutrition", "Geography", "History",
        "Media Studies", "Music", "Physical Education", "Religious Studies",
    ]

    # find start (exact first, loose fallback)
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().lower() == focus_subject.lower():
            start = i
            break
    if start is None:
        for i, ln in enumerate(lines):
            if focus_subject.lower() in ln.lower():
                start = i
                break
    if start is None:
        return lines  # fallback

    # find end (next header)
    end = len(lines)
    for j in range(start + 1, len(lines)):
        for header in next_subjects:
            if lines[j].strip().lower().startswith(header.lower()) and header.lower() != focus_subject.lower():
                end = j
                break
        if end != len(lines):
            break

    return lines[start:end]

def _extract_overview_items(line: str) -> list[str]:
    """
    Parse 'Overview of content: Number, Algebra, Ratio...' into individual items.
    """
    low = line.lower()
    if "overview of content" not in low:
        return []
    # take text after the colon, if present
    after = line.split(":", 1)[1] if ":" in line else line
    parts = [p.strip(" .;–-") for p in after.split(",")]
    out = []
    for p in parts:
        if not p:
            continue
        pl = p.lower()
        # keep only math families, allow short variants like 'Ratio' to map to 'Ratio, proportion and rates of change'
        if any(k in pl for k in MATH_FAMILY):
            out.append(p)
    return out

def _is_math_topic(line: str) -> bool:
    """
    Accept only concise maths items:
    - A family topic (Number, Algebra, Ratio/Proportion/Rates of change, Geometry/Measures, Probability, Statistics)
    - An exam board line
    - A paper line (Paper 1H/2H/3H, calculator/non-calculator)
    Everything else is rejected.
    """
    s = line.strip().strip("•-–").strip()
    if not s:
        return False

    low = s.lower()

    # quick drops
    if any(low.startswith(ds) for ds in DROP_STARTS):
        return False
    if len(s.split()) > 8:
        return False  # prevent long sentences


    # paper / calculator lines
    if any(k in low for k in PAPER_KEYS):
        return True

    # family topics (allow 'Geometry and measures' or either word alone)
    if any(k in low for k in MATH_FAMILY):
        # but avoid sentences like 'students will...' etc.
        if any(w in low for w in ("students", "develop", "acquire", "comprehend", "communicate", "confidence")):
            return False
        return True

    return False

def extract_topics_from_file(path: str, focus_subject: Optional[str] = "Mathematics") -> List[str]:
    """
    Extract concise Maths topics from the PDF/TXT. If focus_subject is provided,
    we slice to that subject section first.
    """
    if path.lower().endswith(".pdf"):
        try:
            raw = extract_text(path) or ""
        except Exception:
            raw = ""
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()

    if not raw:
        return ["Could not extract any text from the file."]

    # normalise & split
    raw = raw.replace("\xa0", " ")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in raw.splitlines() if ln.strip()]

    if focus_subject:
        lines = _slice_subject(lines, focus_subject)

    topics: list[str] = []
    seen = set()

    for ln in lines:
        # If it's an overview line, expand to items
        overview_items = _extract_overview_items(ln)
        if overview_items:
            for it in overview_items:
                key = it.lower()
                if key not in seen:
                    seen.add(key)
                    topics.append(it)
            continue

        # Otherwise, evaluate single line
        if _is_math_topic(ln):
            key = ln.lower()
            if key not in seen:
                seen.add(key)
                topics.append(ln)

    # If nothing matched, give a minimal fallback of the canonical families
    if not topics:
        topics = [
            "Number",
            "Algebra",
            "Ratio, proportion and rates of change",
            "Geometry and measures",
            "Probability",
            "Statistics",
        ]

    return topics


# ------------------------------- uvicorn app.main:app --reload --port 8002
