"""
Database seeding for TracePilot.
Creates default demo users and initialises tables on first run.
"""

from sqlalchemy.orm import Session

from backend.auth import hash_password
from backend.database import Base, engine, SessionLocal
from backend.models import User


# Demo users to create on first run
DEMO_USERS = [
    {"username": "operator", "password": "operator123", "role": "operator"},
    {"username": "supervisor", "password": "supervisor123", "role": "supervisor"},
    {"username": "admin", "password": "admin123", "role": "admin"},
]


def create_tables() -> None:
    """Create all tables defined in the ORM models."""
    Base.metadata.create_all(bind=engine)


def seed_users(db: Session) -> None:
    """Insert demo users if they don't already exist."""
    for user_data in DEMO_USERS:
        existing = db.query(User).filter(User.username == user_data["username"]).first()
        if existing:
            continue
        user = User(
            username=user_data["username"],
            password_hash=hash_password(user_data["password"]),
            role=user_data["role"],
        )
        db.add(user)
        print(f"  Seeded user: {user_data['username']} ({user_data['role']})")
    db.commit()


def run_seed() -> None:
    """Full seed routine: create tables then seed demo data."""
    print("Creating database tables...")
    create_tables()

    print("Seeding demo users...")
    db = SessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()
    print("Seed complete.")
