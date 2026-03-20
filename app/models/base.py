from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Integer, SmallInteger, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Column
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv
from sqlalchemy.orm import relationship

load_dotenv()

MYSQL_USER = os.getenv("DB_USER", "root")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "password")
MYSQL_HOST = os.getenv("DB_HOST", "localhost")
MYSQL_DB = os.getenv("DB_NAME", "faq_db_v1")

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}?charset=utf8mb4"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()