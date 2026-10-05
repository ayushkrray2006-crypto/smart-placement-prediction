import joblib
import pandas as pd
from pathlib import Path

_bundle = joblib.load(Path(__file__).parent.parent / "ml" / "model.pkl")

def predict_readiness(student):
    row = pd.DataFrame([{f: getattr(student, f) for f in _bundle["features"]}])
    p = float(_bundle["model"].predict_proba(row)[0][1])
    band = "High" if p >= 0.7 else "Medium" if p >= 0.4 else "Low"
    return {"readiness_score": round(p * 100, 1), "band": band,
            "note": "This is an estimate, not a guarantee of placement."}
