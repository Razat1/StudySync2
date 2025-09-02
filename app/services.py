from typing import Optional
from sqlalchemy.orm import Session
from .models import StudyGuide, Topic

def create_study_guide(
    db: Session,
    user_id: Optional[int],
    filename: str,
    original_name: str,
    exam_board: Optional[str] = None,
    year: Optional[str] = None,
) -> StudyGuide:
    sg = StudyGuide(
        user_id=user_id,
        filename=filename,
        original_name=original_name,
        exam_board=exam_board,
        year=year,
    )
    db.add(sg)
    db.commit()
    db.refresh(sg)
    return sg

def add_topics(db: Session, study_guide_id: int, titles: list[str]) -> None:
    for t in titles:
        if t.strip():
            db.add(Topic(study_guide_id=study_guide_id, title=t.strip(), selected=False))
    db.commit()

def get_guide(db: Session, guide_id: int) -> Optional[StudyGuide]:
    return db.query(StudyGuide).filter(StudyGuide.id == guide_id).first()

def get_topics(db: Session, guide_id: int) -> list[Topic]:
    return db.query(Topic).filter(Topic.study_guide_id == guide_id).all()

def set_selected(db: Session, topic_id: int, selected: bool) -> None:
    t = db.query(Topic).filter(Topic.id == topic_id).first()
    if t:
        t.selected = selected
        db.commit()
