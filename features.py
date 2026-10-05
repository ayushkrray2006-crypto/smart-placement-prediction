import random
from datetime import datetime
from typing import Literal

from fastapi import BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import email_service
import matching
import ml_service
import models

SKILLS = list(matching.SKILL_NAMES)
PROFILE_FIELDS = ["branch", "grad_year", "tenth_pct", "twelfth_pct", "cgpa", "backlogs",
                  "backlog_history", "internship_type", "cert_type", "certifications", "projects",
                  "preferred_domain", "aptitude", "coding", "dsa", "sql_score", "communication"]
DEFAULTS = {"branch": "CSE", "grad_year": 2027, "internship_type": "none", "cert_type": "none",
            "preferred_domain": "Not sure"}


class ProfileIn(BaseModel):
    branch: str = "CSE"
    grad_year: int = Field(2027, ge=2020, le=2035)
    tenth_pct: float = Field(0, ge=0, le=100)
    twelfth_pct: float = Field(0, ge=0, le=100)
    cgpa: float = Field(ge=0, le=10)
    backlogs: int = Field(0, ge=0, le=20)
    backlog_history: int = Field(0, ge=0, le=1)
    internship_type: Literal["none", "short", "medium", "long"] = "none"
    cert_type: Literal["none", "course", "vendor", "both"] = "none"
    certifications: int = Field(0, ge=0, le=20)
    projects: int = Field(0, ge=0, le=20)
    preferred_domain: str = "Not sure"
    email_alerts: bool = True


class CompanyIn(BaseModel):
    name: str = Field(min_length=1)
    role: str = Field("Software Engineer", min_length=1)
    domain: str = "IT Services"
    ctc_lpa: float = Field(0, ge=0)
    min_cgpa: float = Field(0, ge=0, le=10)
    min_tenth: float = Field(0, ge=0, le=100)
    min_twelfth: float = Field(0, ge=0, le=100)
    max_backlogs: int = Field(0, ge=0)
    branches: str = "ALL"
    min_aptitude: float = Field(0, ge=0, le=100)
    min_coding: float = Field(0, ge=0, le=100)
    min_dsa: float = Field(0, ge=0, le=100)
    min_sql: float = Field(0, ge=0, le=100)
    internship_req: int = Field(0, ge=0, le=2)


class QuestionIn(BaseModel):
    category: str
    text: str = Field(min_length=5)
    options: list[str] = Field(min_length=2, max_length=6)
    answer: int = Field(ge=0)
    explanation: str = ""


class QuizIn(BaseModel):
    category: str
    answers: dict[str, int]


def resources_by_skill(db):
    out = {}
    for r in db.query(models.Resource).order_by(models.Resource.id).all():
        out.setdefault(r.skill, []).append({"title": r.title, "platform": r.platform,
                                            "url": r.url, "level": r.level, "note": r.note})
    return {k: v[:3] for k, v in out.items()}


def ranked_matches(s, db):
    rows = [matching.match_company(s, c) for c in db.query(models.Company).all()]
    rows.sort(key=lambda r: (not r["eligible"], -r["match"]))
    return rows


def build_report(s, user, db):
    pred = ml_service.predict_readiness(s)
    matches = ranked_matches(s, db)
    plan = matching.recommendations(s, resources_by_skill(db))
    roles = sorted([m for m in matches if m["eligible"] or m["match"] >= 70],
                   key=lambda m: (not m["domain_fit"], not m["eligible"], -m["match"]))[:5]
    tests = (db.query(models.Test).filter_by(student_id=s.id)
             .order_by(models.Test.id.desc()).limit(10).all())
    history = [{"test": matching.SKILL_NAMES.get(t.test_type, t.test_type), "score": t.score,
                "date": t.date.strftime("%d %b %Y") if t.date else ""} for t in tests]
    score = lambda k: float(getattr(s, k) or 0)
    strong = [matching.SKILL_NAMES[k] for k in SKILLS if score(k) >= 70]
    weak = [matching.SKILL_NAMES[k] for k in SKILLS if score(k) < 60]
    summary = (f"{user.name} has a placement readiness of {pred['readiness_score']}% "
               f"({pred['band']}) and can currently apply to {sum(m['eligible'] for m in matches)} "
               f"of {len(matches)} listed roles. "
               + (f"Strong areas: {', '.join(strong)}. " if strong else "")
               + (f"Focus on: {', '.join(weak)}." if weak else "No major weak skill areas."))
    profile = {f: (getattr(s, f) if getattr(s, f) is not None else DEFAULTS.get(f, 0))
               for f in PROFILE_FIELDS}
    return {"name": user.name, "email": user.email, "generated": datetime.now().strftime("%d %b %Y"),
            "profile": profile, "readiness": pred, "summary": summary, "matches": matches[:10],
            "roles": roles, "plan": plan, "history": history,
            "eligible_count": sum(m["eligible"] for m in matches), "total_roles": len(matches)}


def report_sections(r):
    p = r["profile"]
    return [
        ("Summary", [r["summary"]]),
        ("Academics", [f"10th: {p['tenth_pct']}%", f"12th: {p['twelfth_pct']}%", f"CGPA: {p['cgpa']}",
                       f"Active backlogs: {p['backlogs']}", f"Branch: {p['branch']} (batch {p['grad_year']})"]),
        ("Experience", [f"Internship: {p['internship_type']}", f"Certifications: {p['cert_type']} ({p['certifications']})",
                        f"Projects: {p['projects']}", f"Preferred domain: {p['preferred_domain']}"]),
        ("Skill scores", [f"{matching.SKILL_NAMES[k]}: {p[k]}" for k in SKILLS]),
        ("Suggested roles", [f"{m['company']} - {m['role']}: {m['match']}% match, "
                             f"{'eligible' if m['eligible'] else 'not yet eligible'}" for m in r["roles"]] or ["None yet"]),
        ("Preparation plan", [f"{i['priority']}. {i['skill']}: {i['advice']}" for i in r["plan"]] or ["No weak areas"]),
    ]


def register(app, current_user, admin_only, my_student, get_db, student_rows):
    @app.get("/profile")
    def get_profile(s=Depends(my_student), user=Depends(current_user)):
        d = {f: (getattr(s, f) if getattr(s, f) is not None else DEFAULTS.get(f, 0)) for f in PROFILE_FIELDS}
        d.update(name=user.name, email=user.email, email_alerts=bool(user.email_alerts))
        return d

    @app.put("/profile")
    def update_profile(d: ProfileIn, s=Depends(my_student), user=Depends(current_user),
                       db: Session = Depends(get_db)):
        data = d.dict()
        user.email_alerts = data.pop("email_alerts")
        for k, v in data.items():
            setattr(s, k, v)
        s.internship = 0 if d.internship_type == "none" else 1
        db.commit()
        return {"message": "Profile updated"}

    @app.get("/eligibility")
    def eligibility(s=Depends(my_student), db: Session = Depends(get_db)):
        return ranked_matches(s, db)

    @app.get("/recommendations")
    def recommendations(s=Depends(my_student), db: Session = Depends(get_db)):
        return matching.recommendations(s, resources_by_skill(db))

    @app.get("/quiz/{category}")
    def quiz(category: str, n: int = 5, _=Depends(my_student), db: Session = Depends(get_db)):
        if category not in matching.ADVICE:
            raise HTTPException(404, "Unknown test")
        qs = db.query(models.Question).filter_by(category=category).all()
        random.shuffle(qs)
        return [{"id": q.id, "text": q.text, "options": q.options.split("||")}
                for q in qs[:max(1, min(n, 10))]]

    @app.post("/quiz/submit")
    def submit_quiz(d: QuizIn, s=Depends(my_student), db: Session = Depends(get_db)):
        if d.category not in matching.ADVICE:
            raise HTTPException(400, "Unknown test")
        ids = [int(k) for k in d.answers if k.isdigit()]
        qs = (db.query(models.Question).filter(models.Question.id.in_(ids),
                                               models.Question.category == d.category).all())
        if not qs:
            raise HTTPException(400, "No answers received")
        review, correct = [], 0
        for q in qs:
            opts, mine = q.options.split("||"), d.answers.get(str(q.id), -1)
            ok = mine == q.answer
            correct += ok
            review.append({"question": q.text, "ok": ok, "correct": opts[q.answer],
                           "your": opts[mine] if 0 <= mine < len(opts) else None,
                           "explanation": q.explanation})
        score = round(100 * correct / len(qs), 1)
        db.add(models.Test(student_id=s.id, test_type=d.category, score=score))
        setattr(s, d.category, score)
        db.commit()
        return {"score": score, "correct": correct, "total": len(qs), "review": review}

    @app.get("/report")
    def report(s=Depends(my_student), user=Depends(current_user), db: Session = Depends(get_db)):
        return build_report(s, user, db)

    @app.post("/report/email")
    def email_report(bg: BackgroundTasks, s=Depends(my_student), user=Depends(current_user),
                     db: Session = Depends(get_db)):
        bg.add_task(email_service.report_mail, user.email, user.name,
                    report_sections(build_report(s, user, db)))
        return {"message": f"Report sent to {user.email}"}

    @app.get("/companies")
    def list_companies(_=Depends(current_user), db: Session = Depends(get_db)):
        cols = ["id", "name", "role", "domain", "ctc_lpa", "min_cgpa", "min_tenth", "min_twelfth",
                "max_backlogs", "branches", "min_aptitude", "min_coding", "min_dsa", "min_sql",
                "internship_req"]
        return [{c: getattr(x, c) for c in cols}
                for x in db.query(models.Company).order_by(models.Company.name, models.Company.role).all()]

    @app.post("/admin/companies")
    def add_company(d: CompanyIn, bg: BackgroundTasks, _=Depends(admin_only),
                    db: Session = Depends(get_db)):
        company = models.Company(**d.dict())
        db.add(company)
        db.commit()
        notified = 0
        for s, u in student_rows(db, alerts_only=True):
            if matching.match_company(s, company)["eligible"]:
                bg.add_task(email_service.company_alert, u.email, u.name, f"{company.name} ({company.role})")
                notified += 1
        return {"message": f"{company.name} added. {notified} eligible students emailed."}

    @app.post("/admin/questions")
    def add_question(d: QuestionIn, _=Depends(admin_only), db: Session = Depends(get_db)):
        if d.category not in matching.ADVICE:
            raise HTTPException(400, "Unknown category")
        if d.answer >= len(d.options):
            raise HTTPException(400, "Correct option number is out of range")
        db.add(models.Question(category=d.category, text=d.text.strip(), answer=d.answer,
                               options="||".join(o.strip() for o in d.options),
                               explanation=d.explanation.strip()))
        db.commit()
        return {"message": "Question added to the test bank"}
