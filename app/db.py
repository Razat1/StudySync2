from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database stored as a file in your project folder
DATABASE_URL = "sqlite:///./studysync.db"

# Create the engine (the connection to the database)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Each request to the database will use this SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class that our models (tables) will inherit from
Base = declarative_base()
