from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from database import Base


def now():
    """Current UTC time as a naive datetime (SQLite stores naive values)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(120))
    email = Column(String(120), unique=True, index=True)
    password_hash = Column(String(255))
    role = Column(String(120), default="student")
    is_verified = Column(Boolean, default=False)
    email_alerts = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)


class Otp(Base):
    __tablename__ = "otps"
    id = Column(Integer, primary_key=True)
    email = Column(String(120), index=True)
    code_hash = Column(String(255))
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=now)
    expires_at = Column(DateTime)


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    branch = Column(String(120), default="CSE")
    cgpa = Column(Float, default=0)
    backlogs = Column(Integer, default=0)
    aptitude = Column(Float, default=0)
    coding = Column(Float, default=0)
    dsa = Column(Float, default=0)
    sql_score = Column(Float, default=0)
    projects = Column(Integer, default=0)
    internship = Column(Integer, default=0)
    certifications = Column(Integer, default=0)
    communication = Column(Float, default=0)
    tenth_pct = Column(Float, default=0)
    twelfth_pct = Column(Float, default=0)
    grad_year = Column(Integer, default=2027)
    backlog_history = Column(Integer, default=0)
    internship_type = Column(String(20), default="none")
    cert_type = Column(String(20), default="none")
    preferred_domain = Column(String(60), default="Not sure")


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String(120))
    min_cgpa = Column(Float, default=0)
    max_backlogs = Column(Integer, default=0)
    min_aptitude = Column(Float, default=0)
    min_coding = Column(Float, default=0)
    role = Column(String(120))
    domain = Column(String(60))
    ctc_lpa = Column(Float, default=0)
    min_tenth = Column(Float, default=0)
    min_twelfth = Column(Float, default=0)
    branches = Column(String(120), default="ALL")
    min_dsa = Column(Float, default=0)
    min_sql = Column(Float, default=0)
    internship_req = Column(Integer, default=0)


class Test(Base):
    __tablename__ = "tests"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    test_type = Column(String(120))
    score = Column(Float)
    date = Column(DateTime, default=now)


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    category = Column(String(40), index=True)
    text = Column(Text)
    options = Column(Text)  # options joined by "||"
    answer = Column(Integer)
    explanation = Column(Text)


class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True)
    skill = Column(String(40), index=True)
    title = Column(String(200))
    platform = Column(String(120))
    url = Column(String(300))
    level = Column(String(40))
    note = Column(Text)
