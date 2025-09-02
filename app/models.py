from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)

class StudyGuide(Base):
    __tablename__ = "study_guides"

    id = Column(Integer, primary_key=True, index=True)
    # for now tie a guide to whoever uploads during this session (we'll improve later)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String, nullable=False)        # full path on disk
    original_name = Column(String, nullable=False)   # what the user uploaded
    exam_board = Column(String, nullable=True)       # optional: "AQA", "Edexcel"
    year = Column(String, nullable=True)

    topics = relationship("Topic", back_populates="guide", cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    study_guide_id = Column(Integer, ForeignKey("study_guides.id"), nullable=False)
    title = Column(String, nullable=False)
    selected = Column(Boolean, default=False)

    guide = relationship("StudyGuide", back_populates="topics")