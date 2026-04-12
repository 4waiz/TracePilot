"""
Audit logging utility for TracePilot.
Records user actions for traceability and compliance.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models import AuditLog


def create_audit_log(
    db: Session,
    *,
    user_id: Optional[int] = None,
    username: str = "system",
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    # Aliases used by some route files
    entity_type: Optional[str] = None,
    entity_id=None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Write an entry to the audit log table."""
    entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        resource_type=resource_type or entity_type or "unknown",
        resource_id=str(resource_id or entity_id or ""),
        details=details,
        timestamp=datetime.now(timezone.utc),
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
