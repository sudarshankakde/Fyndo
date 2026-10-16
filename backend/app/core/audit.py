"""Audit trail helper.

Every state-changing operation calls :func:`audit_log` so that there is a
single, greppable, structured trail of *who* changed *what* and *when*.
Records are emitted through the ``fyndo.audit`` logger, which inherits the
application formatter (JSON in production) and is written to both the console
and the rotating audit file.
"""
import logging
from typing import Any, Optional

audit_logger = logging.getLogger("fyndo.audit")


def audit_log(
    action: str,
    *,
    actor_id: Optional[object] = None,
    actor_role: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[object] = None,
    outcome: str = "success",
    **details: Any,
) -> None:
    """Emits one structured audit record.

    ``action`` is a stable, dotted identifier (e.g. ``reel.moderate``).
    Free-form ``details`` are namespaced under ``detail_`` so they can never
    shadow core log-record fields.
    """
    audit_logger.info(
        "%s %s",
        outcome.upper(),
        action,
        extra={
            "event": "audit",
            "action": action,
            "outcome": outcome,
            "actor_id": str(actor_id) if actor_id else None,
            "actor_role": actor_role,
            "target_type": target_type,
            "target_id": str(target_id) if target_id else None,
            **{f"detail_{key}": value for key, value in details.items()},
        },
    )
