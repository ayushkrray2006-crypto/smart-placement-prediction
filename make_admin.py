from database import SessionLocal
import models

email = input("Enter the email to make admin: ")
db = SessionLocal()
u = db.query(models.User).filter_by(email=email).first()
if u:
    u.role = "admin"
    db.commit()
    print("Done:", email, "is now admin")
else:
    print("No user with that email")
