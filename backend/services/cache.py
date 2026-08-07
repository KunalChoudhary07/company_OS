"""
SQLite-backed cache with SHA-256 hashing on normalized objectives.
Same request (case/whitespace insensitive) never hits the LLM twice.
"""

import hashlib
import json
import logging
import re
import uuid
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models.db import Initiative

logger = logging.getLogger("companyos.cache")


def _normalize(objective: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation from edges."""
    text = objective.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _hash(normalized: str) -> str:
    return hashlib.sha256(normalized.encode()).hexdigest()


def get_cached(db: Session, objective: str) -> Optional[dict]:
    """Return parsed JSON dict if a cached result exists, else None."""
    key = _hash(_normalize(objective))
    row = db.query(Initiative).filter(Initiative.objective_hash == key).first()
    if row:
        logger.info(f"Cache HIT for objective hash {key[:12]}...")
        return json.loads(row.result_json), row.id
    logger.info(f"Cache MISS for objective hash {key[:12]}...")
    return None, None


def store_result(db: Session, objective: str, result_dict: dict) -> str:
    """
    Store result in SQLite. Returns initiative ID.

    Idempotent: `objective_hash` carries a UNIQUE constraint, and the cache
    check in the route is a check-then-act, so two runs of the same objective
    can both see a MISS and then both try to insert. The loser of that race
    used to raise IntegrityError *after* all the LLM and search work had
    already completed, failing the whole request at the last step.
    On conflict we now refresh the existing row and return its id instead.
    """
    key = _hash(_normalize(objective))
    initiative_id = str(uuid.uuid4())
    row = Initiative(
        id=initiative_id,
        objective_hash=key,
        objective=objective,
        result_json=json.dumps(result_dict),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(Initiative).filter(Initiative.objective_hash == key).first()
        if existing is None:
            # Constraint fired but the row isn't there — nothing sane to do but surface it.
            logger.error(f"IntegrityError on {key[:12]} but no existing row found")
            raise
        # Keep the freshest result under the id that already exists.
        existing.result_json = json.dumps(result_dict)
        db.commit()
        logger.info(f"Duplicate objective — reused existing id={existing.id}")
        return existing.id

    logger.info(f"Result stored with id={initiative_id}")
    return initiative_id


def get_by_id(db: Session, initiative_id: str) -> Optional[dict]:
    """Fetch a stored initiative by UUID."""
    row = db.query(Initiative).filter(Initiative.id == initiative_id).first()
    if row:
        return json.loads(row.result_json)
    return None


def list_all(db: Session) -> list:
    """Return summary list of all stored initiatives."""
    rows = db.query(
        Initiative.id, Initiative.objective, Initiative.created_at
    ).order_by(Initiative.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "objective": r.objective,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
