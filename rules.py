def check_eligibility(s, c):
    reasons = []
    if s.cgpa < c.min_cgpa:
        reasons.append(f"CGPA below {c.min_cgpa}")
    if s.backlogs > c.max_backlogs:
        reasons.append(f"Backlogs above {c.max_backlogs}")
    if s.aptitude < c.min_aptitude:
        reasons.append(f"Aptitude below {c.min_aptitude}")
    if s.coding < c.min_coding:
        reasons.append(f"Coding below {c.min_coding}")
    return {"company": c.name, "eligible": not reasons, "reasons": reasons}

ADVICE = {
    "aptitude": "Practice quantitative, logical and verbal aptitude daily.",
    "coding": "Solve 3 coding problems per week.",
    "dsa": "Revise arrays, strings, linked lists, trees and graphs.",
    "sql_score": "Practice joins, group by and subqueries.",
    "communication": "Do mock interviews and group discussions.",
}

def recommendations(s, threshold=60):
    weak = [(k, getattr(s, k)) for k in ADVICE if getattr(s, k) < threshold]
    weak.sort(key=lambda x: x[1])
    recs = [{"skill": k, "score": v, "priority": i + 1, "advice": ADVICE[k]}
            for i, (k, v) in enumerate(weak)]
    if s.internship == 0:
        recs.append({"skill": "internship", "priority": len(recs) + 1,
                     "advice": "Apply for an internship or a real-world project."})
    return recs
