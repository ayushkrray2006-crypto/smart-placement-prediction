import csv
import io
import os
import secrets
from pathlib import Path
from datetime import timedelta

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import email_service
import features
import ml_service
import models
import rules
import seed_data
from database import Base, SessionLocal, engine, get_db

SECRET = os.getenv("JWT_SECRET", "change-me-before-deployment")
OTP_MINUTES, MAX_ATTEMPTS, RESEND_SECONDS = 10, 5, 60
PROFILE_FIELDS = ["branch", "cgpa", "backlogs", "aptitude", "coding", "dsa",
                  "sql_score", "projects", "internship", "certifications", "communication"]

pwd = CryptContext(schemes=["pbkdf2_sha256"])
oauth2 = OAuth2PasswordBearer(tokenUrl="login")
Base.metadata.create_all(engine)
seed_data.setup(engine, Base, SessionLocal)

app = FastAPI(title="Smart Placement System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def seed_admin():
    """Create the default admin once. Change the password via ADMIN_PASSWORD."""
    db = SessionLocal()
    try:
        if not db.query(models.User).filter_by(role="admin").first():
            email = os.getenv("ADMIN_EMAIL", "admin@placement.local").lower()
            db.add(models.User(name="Placement Cell", email=email, role="admin",
                               password_hash=pwd.hash(os.getenv("ADMIN_PASSWORD", "Admin@123")),
                               is_verified=True, email_alerts=False))
            db.commit()
            print(f"Default admin created: {email}")
    finally:
        db.close()


seed_admin()


# ---------- schemas ----------

class RegisterIn(BaseModel):
    name: str = Field(min_length=2)
    email: str
    password: str = Field(min_length=6)


class OtpIn(BaseModel):
    email: str
    code: str


class EmailIn(BaseModel):
    email: str


class ProfileIn(BaseModel):
    branch: str = "CSE"
    cgpa: float = Field(ge=0, le=10)
    backlogs: int = Field(0, ge=0, le=20)
    projects: int = Field(0, ge=0, le=20)
    internship: int = Field(0, ge=0, le=1)
    certifications: int = Field(0, ge=0, le=20)
    email_alerts: bool = True


class TestIn(BaseModel):
    test_type: str
    score: float = Field(ge=0, le=100)


class CompanyIn(BaseModel):
    name: str = Field(min_length=1)
    min_cgpa: float = Field(0, ge=0, le=10)
    max_backlogs: int = Field(0, ge=0)
    min_aptitude: float = Field(0, ge=0, le=100)
    min_coding: float = Field(0, ge=0, le=100)


# ---------- helpers and dependencies ----------

def make_token(user):
    claims = {"sub": user.email, "exp": models.now() + timedelta(hours=8)}
    return jwt.encode(claims, SECRET, algorithm="HS256")


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)):
    try:
        email = jwt.decode(token, SECRET, algorithms=["HS256"])["sub"]
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.query(models.User).filter_by(email=email).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


def admin_only(user=Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admins only")
    return user


def my_student(user=Depends(current_user), db: Session = Depends(get_db)):
    s = db.query(models.Student).filter_by(user_id=user.id).first()
    if not s:
        raise HTTPException(404, "Student profile not found")
    return s


def student_rows(db, alerts_only=False):
    q = (db.query(models.Student, models.User)
         .join(models.User, models.User.id == models.Student.user_id)
         .filter(models.User.is_verified.is_(True)))
    if alerts_only:
        q = q.filter(models.User.email_alerts.is_(True))
    return q.all()


def issue_otp(db, user, bg):
    last = (db.query(models.Otp).filter_by(email=user.email)
            .order_by(models.Otp.id.desc()).first())
    if last and (models.now() - last.created_at).total_seconds() < RESEND_SECONDS:
        raise HTTPException(429, f"Wait {RESEND_SECONDS} seconds before requesting another code")
    db.query(models.Otp).filter_by(email=user.email).delete()
    code = f"{secrets.randbelow(10 ** 6):06d}"
    db.add(models.Otp(email=user.email, code_hash=pwd.hash(code),
                      expires_at=models.now() + timedelta(minutes=OTP_MINUTES)))
    db.commit()
    bg.add_task(email_service.otp_mail, user.email, user.name, code)


def authenticate(db, form, role):
    user = db.query(models.User).filter_by(email=form.username.strip().lower()).first()
    if not user or user.role != role or not pwd.verify(form.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return user


# ---------- registration, OTP and login ----------

@app.post("/register")
def register(d: RegisterIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    email = d.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Enter a valid email")
    user = db.query(models.User).filter_by(email=email).first()
    if user and user.is_verified:
        raise HTTPException(400, "Email already registered")
    if user:  # unverified earlier attempt: update details and resend the code
        user.name, user.password_hash = d.name.strip(), pwd.hash(d.password)
    else:
        user = models.User(name=d.name.strip(), email=email, password_hash=pwd.hash(d.password))
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(models.Student(user_id=user.id))
    db.commit()
    issue_otp(db, user, bg)
    return {"message": "Verification code sent"}


@app.post("/resend-otp")
def resend_otp(d: EmailIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(email=d.email.strip().lower()).first()
    if not user or user.is_verified:
        raise HTTPException(400, "Nothing to verify for this email")
    issue_otp(db, user, bg)
    return {"message": "New code sent"}


@app.post("/verify-otp")
def verify_otp(d: OtpIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(email=d.email.strip().lower()).first()
    otp = db.query(models.Otp).filter_by(email=user.email).first() if user else None
    if not user or not otp:
        raise HTTPException(400, "Request a new code")
    if otp.expires_at < models.now():
        raise HTTPException(400, "Code expired. Request a new one")
    if otp.attempts >= MAX_ATTEMPTS:
        raise HTTPException(429, "Too many wrong attempts. Request a new code")
    if not pwd.verify(d.code.strip(), otp.code_hash):
        otp.attempts += 1
        db.commit()
        raise HTTPException(400, f"Wrong code. {MAX_ATTEMPTS - otp.attempts} attempts left")
    user.is_verified = True
    db.delete(otp)
    db.commit()
    bg.add_task(email_service.welcome_mail, user.email, user.name)
    return {"message": "Email verified"}


@app.post("/login")
def student_login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate(db, form, "student")
    if not user.is_verified:
        raise HTTPException(403, "Email not verified")
    return {"access_token": make_token(user), "token_type": "bearer", "role": "student"}


@app.post("/admin/login")
def admin_login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate(db, form, "admin")
    return {"access_token": make_token(user), "token_type": "bearer", "role": "admin"}


# ---------- student endpoints ----------

@app.post("/tests")
def submit_test(d: TestIn, s=Depends(my_student), db: Session = Depends(get_db)):
    if d.test_type not in rules.ADVICE:
        raise HTTPException(400, "Unknown test type")
    db.add(models.Test(student_id=s.id, test_type=d.test_type, score=d.score))
    setattr(s, d.test_type, d.score)
    db.commit()
    return {"message": "Score saved"}


@app.get("/predict")
def predict(s=Depends(my_student)):
    return ml_service.predict_readiness(s)


# ---------- admin endpoints ----------

@app.post("/admin/send-reminders")
def send_reminders(bg: BackgroundTasks, _=Depends(admin_only), db: Session = Depends(get_db)):
    sent = 0
    for s, u in student_rows(db, alerts_only=True):
        weak = rules.recommendations(s)
        if weak:
            bg.add_task(email_service.reminder_mail, u.email, u.name, weak[:3])
            sent += 1
    return {"message": f"Preparation reminders queued for {sent} students."}


@app.get("/admin/stats")
def stats(_=Depends(admin_only), db: Session = Depends(get_db)):
    rows = [s for s, _u in student_rows(db)]
    n = len(rows) or 1
    pending = db.query(models.User).filter_by(role="student", is_verified=False).count()
    return {"students": len(rows), "pending": pending,
            "avg_cgpa": round(sum(s.cgpa for s in rows) / n, 2),
            "avg_aptitude": round(sum(s.aptitude for s in rows) / n, 1),
            "avg_coding": round(sum(s.coding for s in rows) / n, 1)}


@app.get("/admin/students")
def list_students(_=Depends(admin_only), db: Session = Depends(get_db)):
    out = []
    for s, u in student_rows(db):
        out.append({"name": u.name, "email": u.email, "cgpa": s.cgpa, "backlogs": s.backlogs,
                    "aptitude": s.aptitude, "coding": s.coding,
                    "readiness": ml_service.predict_readiness(s)["readiness_score"]})
    return out


@app.delete("/admin/companies/{company_id}")
def delete_company(company_id: int, _=Depends(admin_only), db: Session = Depends(get_db)):
    company = db.get(models.Company, company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    db.delete(company)
    db.commit()
    return {"message": "Company removed"}


@app.get("/admin/export")
def export_students(_=Depends(admin_only), db: Session = Depends(get_db)):
    rows = list_students(None, db)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Name", "Email", "CGPA", "Backlogs", "Aptitude", "Coding", "Readiness %"])
    for r in rows:
        writer.writerow([r["name"], r["email"], r["cgpa"], r["backlogs"],
                         r["aptitude"], r["coding"], r["readiness"]])
    return Response(out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=students.csv"})


features.register(app, current_user, admin_only, my_student, get_db, student_rows)


# Serve the website (landing page, login, dashboards). Must stay LAST.
app.mount("/", StaticFiles(directory=Path(__file__).parent.parent / "frontend", html=True),
          name="site")
