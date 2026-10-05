"""Rule-based matching of a student profile against company criteria.

Academic criteria (CGPA, 10th, 12th, backlogs, branch, required internship) decide
whether the student can APPLY. Skill criteria (aptitude, coding, DSA, SQL) decide how
well the student is PREPARED, and feed the match percentage.
"""

SKILL_NAMES = {
    "aptitude": "Aptitude",
    "coding": "Coding",
    "dsa": "Data structures and algorithms",
    "sql_score": "SQL and databases",
    "communication": "Communication",
}
ADVICE = {
    "aptitude": "Practise quantitative, logical and verbal aptitude daily and take timed mock tests.",
    "coding": "Solve at least 3 coding problems every week and review better solutions.",
    "dsa": "Revise arrays, strings, linked lists, stacks, trees and graphs with practice problems.",
    "sql_score": "Practise joins, GROUP BY, subqueries and constraints on real tables.",
    "communication": "Do mock interviews and group discussions, and record yourself answering.",
}


def _n(v):
    return float(v or 0)


def match_company(s, c):
    gaps, good, parts = [], [], []
    state = {"eligible": True}

    def check(label, have, need, hard, weight=1.0):
        need = _n(need)
        if need <= 0:
            return
        have = _n(have)
        ratio = min(have / need, 1.0)
        parts.append((weight, ratio))
        if ratio >= 1:
            good.append(f"{label} {have:g} meets the {need:g} needed")
        else:
            gaps.append(f"{label}: you have {have:g}, about {need:g} needed")
            if hard:
                state["eligible"] = False

    check("CGPA", s.cgpa, c.min_cgpa, True, 2)
    check("10th %", s.tenth_pct, c.min_tenth, True)
    check("12th %", s.twelfth_pct, c.min_twelfth, True)

    active, limit = int(s.backlogs or 0), int(c.max_backlogs or 0)
    parts.append((2, 1.0 if active <= limit else 0.0))
    if active > limit:
        gaps.append(f"Active backlogs: you have {active}, at most {limit} allowed")
        state["eligible"] = False
    elif limit == 0 and s.backlog_history:
        gaps.append("You cleared backlogs earlier. Some companies ask for no backlog history")

    allowed = [b.strip().upper() for b in (c.branches or "ALL").split(",") if b.strip()]
    if allowed != ["ALL"] and (s.branch or "").upper() not in allowed:
        gaps.append(f"Branch: open to {', '.join(allowed)}")
        state["eligible"] = False
        parts.append((2, 0.0))

    has_intern = (s.internship_type or "none") != "none"
    req = int(c.internship_req or 0)
    if req == 2 and not has_intern:
        gaps.append("Internship experience is required")
        state["eligible"] = False
        parts.append((1, 0.0))
    elif req == 1 and not has_intern:
        gaps.append("An internship is preferred and would improve your chances")
        parts.append((0.5, 0.0))

    check("Aptitude", s.aptitude, c.min_aptitude, False, 2)
    check("Coding", s.coding, c.min_coding, False, 2)
    check("DSA", s.dsa, c.min_dsa, False, 2)
    check("SQL", s.sql_score, c.min_sql, False, 2)

    total = sum(w for w, _ in parts)
    pct = round(100 * sum(w * r for w, r in parts) / total) if total else 100
    pref = s.preferred_domain or "Not sure"
    return {"id": c.id, "company": c.name, "role": c.role or "Not specified",
            "domain": c.domain or "", "ctc_lpa": c.ctc_lpa or 0,
            "eligible": state["eligible"], "match": pct, "gaps": gaps, "good": good,
            "domain_fit": pref != "Not sure" and pref == c.domain}


def recommendations(s, res, threshold=60):
    """Ordered improvement plan. res maps a skill key to a list of resource dicts."""
    out = []
    weak = sorted(((k, _n(getattr(s, k))) for k in SKILL_NAMES if _n(getattr(s, k)) < threshold),
                  key=lambda x: x[1])
    for k, v in weak:
        out.append({"skill": SKILL_NAMES[k], "score": v, "advice": ADVICE[k],
                    "resources": res.get(k, [])})
    if (s.internship_type or "none") == "none":
        out.append({"skill": "Internship", "score": None, "resources": res.get("internship", []),
                    "advice": "Do at least one internship or a real project with a company, NGO or open-source team."})
    if (s.cert_type or "none") == "none":
        out.append({"skill": "Certification", "score": None, "resources": res.get("certification", []),
                    "advice": "Earn one recognised certificate in your target domain."})
    if int(s.projects or 0) < 2:
        out.append({"skill": "Projects", "score": None, "resources": [],
                    "advice": "Build two projects that solve a real problem and publish them on GitHub."})
    for i, item in enumerate(out, 1):
        item["priority"] = i
    return out
