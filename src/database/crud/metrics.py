"""Coverage metrics CRUD operations."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from src.database.models import CoverageMetrics


def get_coverage_metrics(db: Session, document_id: int) -> Optional[CoverageMetrics]:
    """Get coverage metrics for a document."""
    return db.query(CoverageMetrics).filter(
        CoverageMetrics.document_id == document_id
    ).first()


def create_coverage_metrics(
    db: Session,
    document_id: int,
    total_pages: int,
    processed_pages: int,
    skipped_pages: List[int],
    coverage_percent: float,
    requirements_count: int,
) -> CoverageMetrics:
    """Create coverage metrics for a document."""
    metrics = CoverageMetrics(
        document_id=document_id,
        total_pages=total_pages,
        processed_pages=processed_pages,
        skipped_pages=skipped_pages,
        coverage_percent=coverage_percent,
        requirements_count=requirements_count,
        calculated_at=datetime.now(timezone.utc),
    )
    db.add(metrics)
    db.commit()
    db.refresh(metrics)
    return metrics
