# backend/create_superadmin.py
import sys
import os
from getpass import getpass
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models.user import User
from app.models.tenant import Tenant
from app.services.auth import hash_password

def validate_password(password: str) -> bool:
    if len(password) < 8:
        print("Password must be at least 8 characters long")
        return False
    if not any(c.isdigit() for c in password):
        print("Password must contain at least one number")
        return False
    if not any(c.isalpha() for c in password):
        print("Password must contain at least one letter")
        return False
    return True


def create_superadmin():
    db = SessionLocal()
    try:
        email = input("Email: ").strip()
        password = getpass("Password: ").strip()
        if not validate_password(password):
            return
        full_name = input("Full name: ").strip()

        # Check if already exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.is_superadmin:
                print(f"✅ {email} is already a superadmin")
                return
            # Promote existing user
            existing.is_superadmin = True
            db.commit()
            print(f"✅ {email} promoted to superadmin")
            return

        # Create a platform tenant for superadmin
        tenant = db.query(Tenant).filter(Tenant.slug == "platform").first()
        if not tenant:
            tenant = Tenant(
                name="Platform",
                slug="platform",
                bot_name="Platform Bot",
                is_active=True
            )
            db.add(tenant)
            db.flush()

        # Create new superadmin user
        user = User(
            tenant_id=tenant.id,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role="superadmin",
            is_superadmin=True,
            is_active=True
        )
        db.add(user)
        db.commit()
        print(f"✅ Superadmin created: {email}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_superadmin()
