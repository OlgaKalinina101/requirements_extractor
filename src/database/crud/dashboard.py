"""Dashboard analytics CRUD - aggregates for manager dashboard."""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from src.database.models import Project, Document, Requirement, User, Comment


def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    """Get aggregated dashboard statistics for manager view.

    Returns:
        - total_requirements, total_documents, total_projects
        - by_status: [{status, count}, ...]
        - by_priority: [{priority, count}, ...]
        - by_type: [{type, count}, ...]
        - assignee_workload: [{assignee_id, assignee_name, total, done, in_progress, pending}, ...]
        - recent_activity: [{type, timestamp, ...}, ...]
    """
    # Totals
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    total_documents = db.query(func.count(Document.id)).scalar() or 0
    total_requirements = db.query(func.count(Requirement.id)).scalar() or 0

    # By status
    status_rows = (
        db.query(Requirement.status, func.count(Requirement.id).label("count"))
        .group_by(Requirement.status)
        .all()
    )
    by_status = [{"status": s or "unknown", "count": c} for s, c in status_rows]

    # By priority
    priority_rows = (
        db.query(Requirement.priority, func.count(Requirement.id).label("count"))
        .group_by(Requirement.priority)
        .all()
    )
    by_priority = [{"priority": p or "unknown", "count": c} for p, c in priority_rows]

    # By type
    type_rows = (
        db.query(Requirement.type, func.count(Requirement.id).label("count"))
        .group_by(Requirement.type)
        .all()
    )
    by_type = [{"type": t or "unknown", "count": c} for t, c in type_rows]

    # Assignee workload: count by status per assignee
    assignee_agg = (
        db.query(
            Requirement.assignee_id,
            Requirement.status,
            func.count(Requirement.id).label("cnt"),
        )
        .filter(Requirement.assignee_id.isnot(None))
        .group_by(Requirement.assignee_id, Requirement.status)
        .all()
    )

    assignee_data: Dict[int, Dict[str, Any]] = {}
    for assignee_id, status, cnt in assignee_agg:
        if assignee_id not in assignee_data:
            assignee_data[assignee_id] = {
                "assignee_id": assignee_id,
                "assignee_name": None,
                "total": 0,
                "done": 0,
                "in_progress": 0,
                "pending": 0,
            }
        assignee_data[assignee_id]["total"] += cnt
        if status in ("accepted", "modified", "rejected", "done"):
            assignee_data[assignee_id]["done"] += cnt
        elif status in ("in_progress", "blocked"):
            assignee_data[assignee_id]["in_progress"] += cnt
        else:
            assignee_data[assignee_id]["pending"] += cnt

    # Fill assignee names
    user_ids = list(assignee_data.keys())
    users = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            users[u.id] = u
    assignee_workload = []
    for aid, data in assignee_data.items():
        u = users.get(aid)
        data["assignee_name"] = (u.full_name or u.email) if u else f"User #{aid}"
        assignee_workload.append(data)

    assignee_workload.sort(key=lambda x: x["total"], reverse=True)

    # Recent activity: last 50 events
    # Events: new requirement (created_at), edit (edited_at), comment (created_at)
    activities: List[Dict[str, Any]] = []

    # Recent requirement creations
    recent_reqs = (
        db.query(Requirement)
        .order_by(desc(Requirement.created_at))
        .limit(20)
        .all()
    )
    for r in recent_reqs:
        activities.append({
            "type": "requirement_created",
            "timestamp": r.created_at.isoformat() if r.created_at else None,
            "requirement_id": r.id,
            "requirement_code": r.requirement_id,
            "document_id": r.document_id,
            "text_preview": (r.text or "")[:80] + ("..." if len(r.text or "") > 80 else ""),
        })

    # Recent edits
    edited_reqs = (
        db.query(Requirement)
        .filter(Requirement.edited_at.isnot(None))
        .order_by(desc(Requirement.edited_at))
        .limit(20)
        .all()
    )
    for r in edited_reqs:
        activities.append({
            "type": "requirement_edited",
            "timestamp": r.edited_at.isoformat() if r.edited_at else None,
            "requirement_id": r.id,
            "requirement_code": r.requirement_id,
            "document_id": r.document_id,
            "edited_by": r.edited_by,
        })

    # Recent comments
    recent_comments = (
        db.query(Comment)
        .order_by(desc(Comment.created_at))
        .limit(20)
        .all()
    )
    for c in recent_comments:
        activities.append({
            "type": "comment_added",
            "timestamp": c.created_at.isoformat() if c.created_at else None,
            "requirement_id": c.requirement_id,
            "comment_id": c.id,
            "text_preview": (c.text or "")[:60] + ("..." if len(c.text or "") > 60 else ""),
        })

    # Sort all by timestamp desc and take top 50
    activities = [a for a in activities if a.get("timestamp")]
    activities.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    recent_activity = activities[:50]

    return {
        "total_requirements": total_requirements,
        "total_documents": total_documents,
        "total_projects": total_projects,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_type": by_type,
        "assignee_workload": assignee_workload,
        "recent_activity": recent_activity,
    }


def get_my_dashboard_stats(db: Session, user_id: int) -> Dict[str, Any]:
    """Get dashboard stats for executor: their assigned requirements only."""
    total = (
        db.query(func.count(Requirement.id))
        .filter(Requirement.assignee_id == user_id)
        .scalar()
        or 0
    )

    status_rows = (
        db.query(Requirement.status, func.count(Requirement.id).label("count"))
        .filter(Requirement.assignee_id == user_id)
        .group_by(Requirement.status)
        .all()
    )
    by_status = [{"status": s or "unknown", "count": c} for s, c in status_rows]

    # Recent assigned requirements (last 20)
    recent = (
        db.query(Requirement)
        .filter(Requirement.assignee_id == user_id)
        .order_by(desc(Requirement.created_at))
        .limit(20)
        .all()
    )

    return {
        "total": total,
        "by_status": by_status,
        "recent_requirements": [
            {
                "id": r.id,
                "requirement_id": r.requirement_id,
                "text": (r.text or "")[:80] + ("..." if len(r.text or "") > 80 else ""),
                "status": r.status,
                "document_id": r.document_id,
            }
            for r in recent
        ],
    }
