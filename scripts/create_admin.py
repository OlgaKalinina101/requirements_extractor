"""Create first admin user. Run once after migration 006.

Usage:
    python scripts/create_admin.py
    ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=secret python scripts/create_admin.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.database.database import SessionLocal, init_db
from src.database import crud
from src.auth.password import hash_password


def main():
    init_db()
    db = SessionLocal()
    try:
        email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        password = os.getenv("ADMIN_PASSWORD", "admin123")
        force = "--force" in sys.argv

        existing_user = crud.get_user_by_email(db, email)
        if existing_user and not force:
            print(f"User {email} already exists.")
            return

        if not force:
            any_user = crud.list_users(db, limit=1)
            if any_user:
                print("Users already exist. Use --force to create admin anyway.")
                return

        user = crud.create_user(
            db=db,
            email=email,
            hashed_password=hash_password(password),
            full_name="Administrator",
            role="admin",
        )
        print(f"Admin user created: {user.email} (id={user.id})")
        print("Change the password after first login!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
