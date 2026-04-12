"""
Unit tests for audit log creation using an in-memory SQLite database.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.audit import create_audit_log
from backend.models import AuditLog


@pytest.fixture()
def db_session():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_create_audit_log_basic(db_session):
    """A basic audit log entry should be persisted with all fields."""
    entry = create_audit_log(
        db=db_session,
        user_id=1,
        username="operator1",
        action="create_job",
        resource_type="job",
        resource_id="42",
        details="Created job 'Test Job'",
    )

    assert entry.id is not None
    assert entry.user_id == 1
    assert entry.username == "operator1"
    assert entry.action == "create_job"
    assert entry.resource_type == "job"
    assert entry.resource_id == "42"
    assert entry.details == "Created job 'Test Job'"
    assert entry.timestamp is not None


def test_create_audit_log_persisted(db_session):
    """The audit log entry should be queryable from the database."""
    create_audit_log(
        db=db_session,
        user_id=1,
        username="admin",
        action="login",
        resource_type="user",
        resource_id="1",
        details="User logged in",
    )

    logs = db_session.query(AuditLog).all()
    assert len(logs) == 1
    assert logs[0].action == "login"


def test_create_audit_log_system_action(db_session):
    """System actions can have user_id=None."""
    entry = create_audit_log(
        db=db_session,
        user_id=None,
        username="system",
        action="scheduled_cleanup",
        resource_type="system",
        details="Automatic cleanup ran",
    )

    assert entry.user_id is None
    assert entry.username == "system"


def test_create_audit_log_with_ip(db_session):
    """IP address should be stored when provided."""
    entry = create_audit_log(
        db=db_session,
        user_id=5,
        username="inspector",
        action="record_measurement",
        resource_type="measurement",
        resource_id="100",
        ip_address="192.168.1.42",
    )

    assert entry.ip_address == "192.168.1.42"


def test_multiple_audit_logs(db_session):
    """Multiple log entries should all be persisted."""
    for i in range(5):
        create_audit_log(
            db=db_session,
            user_id=i,
            username=f"user{i}",
            action=f"action_{i}",
            resource_type="job",
            resource_id=str(i),
        )

    logs = db_session.query(AuditLog).all()
    assert len(logs) == 5
