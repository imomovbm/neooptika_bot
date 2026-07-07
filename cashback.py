from models import SessionLocal, User

with SessionLocal() as session:
    # try a telegram_id that definitely does NOT exist yet
    missing = session.query(User).filter_by(telegram_id=999999999).first()
    print("Missing user result:", missing)
    print("Is it falsy?", not missing)