import datetime
import re
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from .models import ResearchCorpus


PII_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"),
}


def redact_pii(text: str) -> str:
    redacted = text or ""
    for label, pattern in PII_PATTERNS.items():
        redacted = pattern.sub(f"[REDACTED_{label.upper()}]", redacted)
    return redacted


def register_corpus(
    db: Session,
    *,
    name: str,
    source_type: str,
    file_search_store: Optional[str] = None,
    sample_text: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ResearchCorpus:
    metadata = dict(metadata or {})
    if sample_text is not None:
        metadata["sample_preview_redacted"] = redact_pii(sample_text)[:1000]

    corpus = ResearchCorpus(
        corpus_id=str(uuid.uuid4()),
        name=name,
        source_type=source_type,
        file_search_store=file_search_store,
        redaction_status="redacted" if sample_text else "configured",
        pii_redaction_rules={"patterns": list(PII_PATTERNS.keys())},
        metadata_json=metadata,
        last_synced_at=datetime.datetime.utcnow() if file_search_store else None,
    )
    db.add(corpus)
    db.commit()
    db.refresh(corpus)
    return corpus
